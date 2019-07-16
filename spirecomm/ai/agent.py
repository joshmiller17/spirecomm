from __future__ import division
import time
import random
import collections
import traceback
import sys

from spirecomm.spire.game import Game
from spirecomm.spire.character import Intent, PlayerClass
import spirecomm.spire.card
from spirecomm.spire.screen import RestOption
from spirecomm.communication.action import *
from spirecomm.ai.behaviours import *
from spirecomm.ai.priorities import *

import py_trees



class SimpleAgent:

	def __init__(self, logfile, chosen_class=PlayerClass.IRONCLAD):
		self.chosen_class = chosen_class
		self.change_class(chosen_class)
		self.action_delay = 2.0 # seconds delay per action, useful for actually seeing what's going on.
		self.debug_level = 5
		# high delay will steal mouse focus??
		self.ascension = 0
		self.debug_queue = ["AI initialized.", "Delay timer set to " + str(self.action_delay), "Debug level set to " + str(self.debug_level)]
		self.cmd_queue = []
		self.last_action = None
		self.logfile = logfile
		self.skipping_card = False
		self.paused = False
		self.step = False
		self.combat_round = 1
		self.root = SelectorBehaviour("Root Context Selector")
		self.init_behaviour_tree(self.root) # Warning: uses British spelling
		self.behaviour_tree = py_trees.trees.BehaviourTree(self.root)
		self.blackboard = py_trees.blackboard.Blackboard()
		self.blackboard.game = Game()
		self.last_game_state = Game()
		# call behaviour_tree.tick() for one tick
		# can use behaviour.tick_once() to tick a specific behaviour
		
		# SIMPLE TRAITS
		self.errors = 0
		self.choose_good_card = False
		self.map_route = []
		self.upcoming_rooms = []
		self.priorities = Priority()
		
	def pause(self):
		self.paused = True
		self.log("Paused")
		
	def resume(self):
		self.paused = False
		self.log("Resuming")
		
	# do one action
	def take_step(self):
		self.paused = False
		self.step = True
		self.log("Taking a step")
		
	def tree_to_json(self,filename):
		f = open(filename,"w")
		f.write(json.dumps(self.root.to_json(),indent="\t"))
		f.close()

	def json_to_tree(self,filename):
		f = open(filename,"r")
		jsonTree = json.load(f)
		f.close()
		
		self.root = SelectorBehaviour.fromDict(jsonTree,self)
		self.log(filename + " loaded successfully:")
		self.log(py_trees.display.ascii_tree(self.root))
		
	def print_tree(self):
		self.log(py_trees.display.ascii_tree(self.root))
		
	# only show to screen if self.debug_level >= debug
	"""
	DEBUG LEVELS
	-1 Don't even save to logfile
	0 Off
	1 Fatal
	2 Error
	3 Warn
	4 Info
	5 Debug
	6 Trace
	7 All
	"""
	def log(self, msg, debug=4):
		if self.debug_level >= 0 and debug >= 0:
			print(str(time.time()) + ": " + msg, file=self.logfile, flush=True)
		if self.debug_level >= debug:
			self.debug_queue.append(msg)
			
	# a note is a log that isn't shown to the Kivy window
	def note(self, msg):
		print(str(time.time()) + ": " + msg, file=self.logfile, flush=True)
		
	def init_behaviour_tree(self, root):
		choiceContext = SequenceBehaviour("Choice Context")
		proceedContext = SequenceBehaviour("Proceed Context")
		combatContext = SequenceBehaviour("Combat Context")
		cancelContext = SequenceBehaviour("Cancel Context")
		choiceAvail = BoolCheckBehaviour("Choice Available", agent=self, boolean="choice_available")
		proceedAvail = BoolCheckBehaviour("Proceed Available", agent=self, boolean="proceed_available")
		combatAvail = SelectorBehaviour("Combat Choice Available")
		playAvail = BoolCheckBehaviour("Play Available", agent=self, boolean="play_available")
		endAvail = BoolCheckBehaviour("End Available", agent=self, boolean="end_available")
		combatAvail.add_children([playAvail, endAvail])
		cancelAvail = BoolCheckBehaviour("Cancel Available", agent=self, boolean="cancel_available")
		testBehaviour = TestBehaviour("Test", agent=self)
		
		choiceSelector = SelectorBehaviour("Type of Choice Selector")
		eventContext = SequenceBehaviour("Event Context")
		eventAvail = CompareToConstBehaviour("Event Available", agent=self, attr="screen_type", static=ScreenType.EVENT)
		eventDecision = ActionBehaviour("Default Choose", agent=self, action="ChooseAction",params=[0])
		eventContext.add_children([eventAvail, eventDecision])
		
		chestContext = SequenceBehaviour("Chest Context")
		chestAvail = CompareToConstBehaviour("Chest Available", agent=self, attr="screen_type", static=ScreenType.CHEST)
		chestDecision = ActionBehaviour("Default Chest Open", agent=self, action="OpenChestAction")
		chestContext.add_children([chestAvail, chestDecision])
		
		shopContext = SequenceBehaviour("Shop Context")
		shopAvail = CompareToConstBehaviour("Shop Available", agent=self, attr="screen_type", static=ScreenType.SHOP_ROOM)
		doShop = SelectorBehaviour("Check Shop")
		tryVisitingShop = SequenceBehaviour("Try Visiting Shop")
		visitedShop = BoolCheckBehaviour("Is Shop Visited", agent=self, boolean="visited_shop")
		visitShop = ActionBehaviour("Visit Shop", agent=self, action="ChooseShopkeeperAction")
		tryVisitingShop.add_children([visitedShop, visitShop])
		dontVisitShop = ActionBehaviour("Leave Shop", agent=self, action="ProceedAction")
		doShop.add_children([tryVisitingShop, dontVisitShop])
		shopContext.add_children([shopAvail, doShop])
		
		restContext = SequenceBehaviour("Rest Context")
		restAvail = CompareToConstBehaviour("Rest Available", agent=self, attr="screen_type", static=ScreenType.REST)
		doRest = CustomBehaviour("Choose Rest Option", agent=self, function="choose_rest_option")
		restContext.add_children([restAvail, doRest])

		cardRewardContext = SequenceBehaviour("Card Reward Context")
		cardRewardAvail = CompareToConstBehaviour("Card Reward Available", agent=self, attr="screen_type", static=ScreenType.CARD_REWARD)
		chooseCard = CustomBehaviour("Choose a Card", agent=self, function="choose_card_reward")
		cardRewardContext.add_children([cardRewardAvail, chooseCard])
		
		
		combatRewardContext = SequenceBehaviour("Combat Reward Context")
		combatRewardAvail = CompareToConstBehaviour("Combat Reward Available", agent=self, attr="screen_type", static=ScreenType.COMBAT_REWARD)
		handleRewards = CustomBehaviour("Handle Rewards", agent=self, function="handle_rewards")
		combatRewardContext.add_children([combatRewardAvail, handleRewards])
		
		mapContext = SequenceBehaviour("Map Context")
		mapAvail = CompareToConstBehaviour("Map Available", agent=self, attr="screen_type", static=ScreenType.MAP)
		mapChoice = CustomBehaviour("Handle Map", agent=self, function="make_map_choice")
		mapContext.add_children([mapAvail, mapChoice])
		
		bossRewardContext = SequenceBehaviour("Boss Reward Context")
		bossAvail = CompareToConstBehaviour("Boss Reward Available", agent=self, attr="screen_type", static=ScreenType.BOSS_REWARD)
		bossChoice = CustomBehaviour("Handle Boss Reward", agent=self, function="handle_boss_reward")
		bossRewardContext.add_children([bossAvail, bossChoice])
		
		shopScreenContext = SequenceBehaviour("Shop Screen Context")
		shopScreenAvail = CompareToConstBehaviour("Shop Screen Available", agent=self, attr="screen_type", static=ScreenType.SHOP_SCREEN)
		shopScreenChoice = CustomBehaviour("Handle Shop Screen", agent=self, function="handle_shop_screen")
		shopScreenContext.add_children([shopScreenAvail, shopScreenChoice])
		
		
		gridContext = SequenceBehaviour("Grid Context")
		gridAvail = CompareToConstBehaviour("Grid Available", agent=self, attr="screen_type", static=ScreenType.GRID)
		gridChoice = CustomBehaviour("Handle Grid", agent=self, function="handle_grid")
		gridContext.add_children([gridAvail, gridChoice])
		
		selectFromHandContext = SequenceBehaviour("Select From Hand Context")
		selectFromHandAvail = CompareToConstBehaviour("Hand Select Available", agent=self, attr="screen_type", static=ScreenType.HAND_SELECT)
		selectFromHandChoice = CustomBehaviour("Handle Hand Select", agent=self, function="handle_hand_select")
		selectFromHandContext.add_children([selectFromHandAvail, selectFromHandChoice])		
		
		choiceSelector.add_children([eventContext, chestContext, shopContext, restContext, cardRewardContext, combatRewardContext,
		mapContext, bossRewardContext, shopScreenContext, gridContext, selectFromHandContext])

		choiceContext.add_children([choiceAvail, choiceSelector])
		proceedContext.add_children([proceedAvail, ActionBehaviour("Proceed", agent=self, action="ProceedAction")])
		combatContext.add_children([combatAvail, testBehaviour])
		cancelContext.add_children([cancelAvail, ActionBehaviour("Cancel", agent=self, action="CancelAction")])
		
		root.add_children([choiceContext, proceedContext, combatContext, cancelContext])
		self.log("Behaviour tree initialized.")
		self.note(py_trees.display.ascii_tree(root))
		#py_trees.display.render_dot_tree(root) # FIXME can't render dot tree: FileNotFoundError: [WinError 2] "dot" not found in path.
		
	# For this to get plugged in, need to set pre_tick_handler = this func at some point
	# Can also set a post tick handler
	#def pre_tick_handler(self.behaviour_tree):
	#	pass
		
	def get_next_msg(self):
		try:
			return self.debug_queue.pop(0)
		except:
			return ""
		
	# equivalent to self.log(msg, debug=-1)
	def think(self, msg):
		self.debug_queue.append(msg)
			
	def get_next_cmd(self):
		try:
			return self.cmd_queue.pop()
		except:
			return Action()
			
	def decide(self, action):
		if action.command.startswith("end"):
			self.combat_round += 1
			self.blackboard.game.combat_round = self.combat_round
		if action.command.startswith("proceed"):
			self.combat_round = 1
		self.log("> " + str(action), debug=5)
		return action
		
	# Check that the simulator predicted this outcome was possible
	def simulation_sanity_check(self, original_state, action):
		simulated_state = original_state.takeAction(action)
		diff = self.state_diff(self.blackboard.game, simulated_state)
		if diff != {}:
			if len(diff) == 2 and "drawn" in diff and "hand_to_deck" in diff and len(diff["drawn"]) == len(diff["hand_to_deck"]):
				self.log("minor warning: hand drawn different than simulated, see log for details", debug=4)
			else:
				self.log("WARN: simulation discrepency, see log for details", debug=3)
			self.log("actual/sim diff: " + str(diff), debug=4)
			self.note("Simulated:")
			self.note(str(simulated_state))
			self.note("Actual:")
			self.note(str(self.blackboard.game))
		else:
			self.log("Sanity check success!")
		
	# Returns a dict of what changed between game states
	def state_diff(self, state1, state2):	
		diff = {}
		if state1.room_phase != state2.room_phase:
			diff["room_phase"] = str(state2.room_phase)
		if state1.room_type != state2.room_type:
			diff["room_type"] = str(state2.room_type)
		choices_added = set(state2.choice_list) - (set(state1.choice_list))
		choices_added = list(choices_added)
		if choices_added != []:
			diff["choices_added"] = choices_added
		choices_removed = set(state1.choice_list) - (set(state2.choice_list))
		choices_removed = list(choices_removed)
		if choices_removed != []:
			diff["choices_removed"] = choices_removed
		if state1.current_action != state2.current_action:
			diff["current_action"] = str(state2.current_action)
		if state1.act_boss != state2.act_boss:
			diff["act_boss"] = state2.act_boss
		if state1.current_hp != state2.current_hp:
			diff["current_hp"] = state2.current_hp - state1.current_hp
		if state1.max_hp != state2.max_hp:
			diff["max_hp"] = state2.max_hp - state1.max_hp
		if state1.floor != state2.floor:
			diff["floor"] = state2.floor
		if state1.act != state2.act:
			diff["act"] = state2.act
		if state1.gold != state2.gold:
			diff["gold"] = state2.gold - state1.gold
			
		# relics
		if state1.relics != state2.relics:
			diff["relics"] = []
			for relic2 in state2.relics:
				found = False
				for relic1 in state1.relics:
					if relic1.name == relic2.name:
						found = True
						if relic1.counter != relic2.counter:
							diff["relics"].append((relic2.name, relic2.counter - relic1.counter))
				if not found:
					diff["relics"].append(relic2.name)
			if diff["relics"] == []:
				diff.pop("relics", None)
				
		# deck
		if state1.deck != state2.deck:
			diff["cards_added"] = []
			diff["cards_removed"] = []
			diff["cards_upgraded"] = []
			cards_changed = set(state2.deck).symmetric_difference(set(state1.deck))
			for card in cards_changed:
				if card not in state2.deck:
					diff["cards_removed"].append(str(card))
				elif card not in state1.deck:
					diff["cards_added"].append(str(card))
				else: # assume upgraded or changed in some way
					diff["cards_upgraded"].append(str(card))
			if diff["cards_added"] == []:
				diff.pop("cards_added", None)
			if diff["cards_removed"] == []:
				diff.pop("cards_removed", None)
			if diff["cards_upgraded"] == []:
				diff.pop("cards_upgraded", None)
			#diff["deck_added"] = [c.name for c in list(set(state2.deck) - set(state1.deck))]
			#diff["deck_removed"] = [c.name for c in list(set(state1.deck) - set(state2.deck))]
			
			
		if state1.potions != state2.potions:
			diff["potions_added"] = [str(p) for p in list(set(state2.potions) - set(state1.potions))]
			diff["potions_removed"] = [str(p) for p in list(set(state1.potions) - set(state2.potions))]	
		if state1.in_combat != state2.in_combat:
			diff["in_combat"] = state2.in_combat
		

		# Combat for both states
		if state1.player is not None and state2.player is not None:
		
			monster_changes = {}
			
			monsters1 = [monster for monster in state1.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			monsters2 = [monster for monster in state2.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]

			for monster1 in monsters1:
				for monster2 in monsters2:
					if monster1 == monster2:
						m_id = monster1.name + str(monster1.monster_index)
						if monster1.current_hp != monster2.current_hp:
							monster_changes[m_id + "_hp"] = monster2.current_hp - monster1.current_hp
						if monster1.block != monster2.block:
								monster_changes[m_id + "_block"] = monster2.block - monster1.block
							
						if monster1.powers != monster2.powers:
							monster_changes[m_id + "_powers_changed"] = []
							monster_changes[m_id + "_powers_added"] = []
							monster_changes[m_id + "_powers_removed"] = []
							powers_changed = set(monster2.powers).symmetric_difference(set(monster1.powers))
							for power in powers_changed:
								if power in monster1.powers and power in monster2.powers:
										monster_changes[m_id + "_powers_changed"].append((power.power_name, power2.amount - power1.amount))
								elif power in monster2.powers:
									for p2 in monster2.powers:
										if p2.power_name == power.power_name:
											monster_changes[m_id + "_powers_added"].append((p2.power_name, p2.amount))
											continue
								elif power in monster1.powers:
									for p1 in monster1.powers:
										if p1.power_name == power.power_name:
											monster_changes[m_id + "_powers_removed"].append((p1.power_name, p1.amount))
											continue
												
							if monster_changes[m_id + "_powers_added"] == []:
								monster_changes.pop(m_id + "_powers_added", None)
							if monster_changes[m_id + "_powers_removed"] == []:
								monster_changes.pop(m_id + "_powers_removed", None)
							if monster_changes[m_id + "_powers_changed"] == []:
								monster_changes.pop(m_id + "_powers_changed", None)
			
			if monster_changes != {}:
				diff["monsters"] = monster_changes
			
			# general fixme?: better record linking between state1 and state2? right now most record linking is by name or ID (which might not be the same necessarily)
		
			cards_changed_from_hand = set(state2.hand).symmetric_difference(set(state1.hand))
			cards_changed_from_draw = set(state2.draw_pile).symmetric_difference(set(state1.draw_pile))
			cards_changed_from_discard = set(state2.discard_pile).symmetric_difference(set(state1.discard_pile))
			cards_changed_from_exhaust = set(state2.exhaust_pile).symmetric_difference(set(state1.exhaust_pile))
			cards_changed = cards_changed_from_hand | cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
			cards_changed_outside_hand = cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
			
			card_actions = ["drawn", "hand_to_deck", "discovered", "exhausted", "exhumed", "discarded",
							"discard_to_hand", "deck_to_discard", "discard_to_deck",
							"discovered_to_deck", "discovered_to_discard", # "playability_changed", <- deprecated
							 "power_played", "upgraded", "unknown_change", "err_pc"]
			
			for a in card_actions:
				diff[a] = []
				
			# TODO some checks if none of these cases are true
			for card in cards_changed:
				if card in cards_changed_from_draw and card in cards_changed_from_hand:
					# draw
					if card in state2.hand:
						diff["drawn"].append(card.get_id_str())
						continue
					# hand to deck
					elif card in state1.hand:
						diff["hand_to_deck"].append(card.get_id_str())
						continue	
				elif card in cards_changed_from_hand and card in cards_changed_from_discard:
					# discard
					if card in state1.hand:
						diff["discarded"].append(card.get_id_str())
						continue
					# discard to hand
					elif card in state2.hand:
						diff["discard_to_hand"].append(card.get_id_str())
						continue	
				elif card in cards_changed_from_exhaust and card in cards_changed_from_hand:
					#exhaust
					if card in state1.hand:
						diff["exhausted"].append(card.get_id_str())
						continue
					#exhume
					elif card in state2.hand:
						diff["exhumed"].append(card.get_id_str())
						continue
				elif card in cards_changed_from_discard and card in cards_changed_from_draw:
					#deck to discard
					if card in state2.discard_pile:
						diff["deck_to_discard"].append(card.get_id_str())
						continue
					# discard to deck
					elif card in state1.discard_pile:
						diff["discard_to_deck"].append(card.get_id_str())
						continue
				elif card in cards_changed_from_hand and card in state2.hand and card not in cards_changed_outside_hand:
					#discovered
					if card not in state1.hand and card not in state1.draw_pile and card not in state1.discard_pile and card not in state1.exhaust_pile:
						diff["discovered"].append(card.get_id_str())
						continue
				elif card in cards_changed_from_hand and card in state1.hand and card not in cards_changed_outside_hand:
					if card.type is spirecomm.spire.card.CardType.POWER and card not in state2.hand:
						# power played
						diff["power_played"].append(card.get_id_str())
						continue
					elif card.upgrades > 0: # assume upgrading it was the different thing
						diff["upgraded"].append(card.get_id_str()) # FIXME check this more strongly
						continue	
				elif card in state2.deck and card not in state1.deck and card not in state1.hand and card not in state1.discard_pile and card not in state1.exhaust_pile:
					# discovered to deck, e.g. status effect
					diff["discovered_to_deck"].append(card.get_id_str())
					continue
				elif card in state2.discard_pile and card not in state1.discard_pile and card not in state1.hand and card not in state1.deck and card not in state1.exhaust_pile:
					# discovered to discard, e.g. status effect
					diff["discovered_to_discard"].append(card.get_id_str())
					continue
				else:
					self.log("WARN: unknown card change " + card.get_id_str(), debug=3)
					diff["unknown_change"].append(card.get_id_str())
					if card in state1.deck:
						self.log("card was in state1 deck")
					if card in state2.deck:
						self.log("card is in state2 deck")
					if card in state1.discard_pile:
						self.log("card was in state1 discard")
					if card in state2.discard_pile:
						self.log("card is in state2 discard")
					if card in state1.hand:
						self.log("card was in state1 hand")
					if card in state2.hand:
						self.log("card is in state2 hand")
					if card in state1.exhaust_pile:
						self.log("card was in state1 exhaust")
					if card in state2.exhaust_pile:
						self.log("card is in state2 exhaust")
			
			for a in card_actions:
				if diff[a] == []:
					diff.pop(a, None)
		
			if state1.player.block != state2.player.block:
				diff["block"] = state2.player.block - state1.player.block
				
			if state1.player.powers != state2.player.powers:
				diff["powers_changed"] = []
				diff["powers_added"] = []
				diff["powers_removed"] = []
				powers_changed = set(state2.player.powers).symmetric_difference(set(state1.player.powers))
				for power in powers_changed:
					#power1 = next(p for p in state1.player.powers if p.name == power.name)
					#power2 = next(p for p in state2.player.powers if p.name == power.name)
					if power in state1.player.powers and power in state2.player.powers:
							diff["powers_changed"].append((power.power_name, power2.amount - power1.amount))
					elif power in state2.player.powers:
						for p2 in state2.player.powers:
							if p2.power_name == power.power_name:
								diff["powers_added"].append((p2.power_name, p2.amount))
								continue
					elif power in state1.player.powers:
						for p1 in state1.player.powers:
							if p1.power_name == power.power_name:
								diff["powers_added"].append((p1.power_name, p1.amount))
								continue
									
				if diff["powers_added"] == []:
					diff.pop("powers_added", None)
				if diff["powers_removed"] == []:
					diff.pop("powers_removed", None)
				if diff["powers_changed"] == []:
					diff.pop("powers_changed", None)
					

		# if diff != {}:
			# # TEST ONLY
			# self.log("Our deck (state1):")
			# for card in state1.deck:
				# self.log(card.get_id_str())
			# self.log("Our hand (state1):")
			# for card in state1.hand:
				# self.log(card.get_id_str())
			# self.log("Our draw pile (state1):")
			# for card in state1.draw_pile:
				# self.log(card.get_id_str())
			# self.log("Our discard pile (state1):")
			# for card in state1.discard_pile:
				# self.log(card.get_id_str())
			
			# self.log("Our deck (state2):")
			# for card in state2.deck:
				# self.log(card.get_id_str())
			# self.log("Our hand (state2):")
			# for card in state2.hand:
				# self.log(card.get_id_str())
			# self.log("Our draw pile (state2):")
			# for card in state2.draw_pile:
				# self.log(card.get_id_str())
			# self.log("Our discard pile (state2):")
			# for card in state2.discard_pile:
				# self.log(card.get_id_str())
		
			
			
		return diff
		
		
	def change_class(self, new_class):
		self.chosen_class = new_class
		if self.chosen_class == PlayerClass.THE_SILENT:
			self.priorities = SilentPriority() # Simple FIXME
		elif self.chosen_class == PlayerClass.IRONCLAD:
			self.priorities = IroncladPriority()  # Simple FIXME
		elif self.chosen_class == PlayerClass.DEFECT:
			self.priorities = DefectPowerPriority()  # Simple FIXME
		else:
			self.priorities = random.choice(list(PlayerClass))  # Simple FIXME

	# This error handler is called whenever CommMod throws an error
	# For example, if we open pause menu, the last action we send will be Invalid
	# Coordinator still needs an action input, so this function needs to return a valid action
	def handle_error(self, error):
		return Action() # TODO remove
		self.log("Error: " + str(error), debug=2)
		if "Invalid command" in str(error):
			if "error" in str(error):
				self.log(traceback.format_exc(), debug=2)
				self.log(str(sys.exc_info()), debug=2)
				print(traceback.format_exc(), file=self.logfile, flush=True)
			# Assume this just means we're paused
			self.log("Invalid command error", debug=3)
			time.sleep(1)
			return Action()
		elif "Selected card requires an enemy target" in str(error):
			# FIXME I think this is related to unpausing from in-game pause menu, we accidentally input an un-initialized play
			# For now, just try again
			self.log("Selected card requires target error", debug=3)
			time.sleep(1)
			return Action()
		else:
			raise Exception(error)
		
	def default_logic(self, game_state):
	
		if self.blackboard.game.choice_available:
			return self.decide(self.handle_screen())
		if self.blackboard.game.proceed_available:
			return self.decide(ProceedAction())
		if self.blackboard.game.play_available or self.blackboard.game.end_available:
			return self.handle_combat()
		if self.blackboard.game.cancel_available:
			return self.decide(CancelAction())
		self.log("Error: no choices available. Game paused?", debug=2)
		time.sleep(1)
		return Action()

	def get_next_action_in_game(self, game_state):
		self.last_game_state = self.blackboard.game
		self.blackboard.game = game_state
		
		# Check difference from last state
		self.log("Diff: " + str(self.state_diff(self.last_game_state, self.blackboard.game)), debug=7)
		if self.blackboard.game.in_combat and self.last_game_state.in_combat and self.last_action is not None:
			self.simulation_sanity_check(self.last_game_state, self.last_action) # check if we predicted this
		
		# Sleep if needed
		time.sleep(self.action_delay)
		while (self.paused):
			time.sleep(1)
			self.think('z')
		
	
		try:
			self.compute_smart_state()
			self.log(str(self.blackboard.game), debug=5)
			self.behaviour_tree.tick() # should add an action to the self.cmd_queue
			
		except Exception as e:
			self.log("Agent encountered error", debug=2)
			self.log(str(e), debug=2)
			self.log(traceback.format_exc(), debug=2)
			print(traceback.format_exc(), file=self.logfile, flush=True)
		
		if self.step: # finish taking one step
			self.paused = True
			self.step = False
		
		cmd = self.get_next_cmd()
		self.last_action = cmd
		return self.decide(cmd) # FIXME, after phasing out the default logic, should only get one decide - right now, decide is called twice
		

	def get_next_action_out_of_game(self):
		self.log("Starting new game")
		return StartGameAction(self.chosen_class, ascension_level=self.ascension)
		
	def compute_smart_state(self):
		pass
		#g = self.blackboard.game
		#hp_percent = (g.current_hp * 100.0) / g.max_hp
		#self.think("I'm at {0:.0f}% HP".format(hp_percent))
		
		for monster in self.blackboard.game.monsters:
			if monster.half_dead:
				self.think("{} ({}) is half-dead!".format(monster.name, monster.monster_index))
			#if monster.is_gone:
			#	self.think("{} ({}) is gone!".format(monster.name, monster.monster_index))
			if monster.intent.is_attack():
				if len(self.blackboard.game.monsters) > 1:
					index_str = " [" + str(monster.monster_index + 1) + "]"
				else:
					index_str = ""
				if monster.move_adjusted_damage is not None:
					self.think("{}{} is hitting me for {}x{} damage".format(monster.name, index_str, monster.move_adjusted_damage, monster.move_hits))
				else: 
					self.think("{}{} is hitting me for {} damage".format(monster.name, index_str, monster.incoming_damage))
		
		# FIXME map_route isn't actually nodes, but a set of X coords
		#upcoming_rooms = collections.defaultdict(int)
		#self.generate_map_route()
		#for node in self.map_route:
		#	upcoming_rooms[node.symbol] += 1
		#self.think("My chosen map route has these rooms:")
		#for key,value in upcoming_rooms.items():
		#	self.think("{}.{}".format(key,value))	
		
		
		
# ---------------------------------------------

	def handle_combat(self):
		if self.blackboard.game.room_type == "MonsterRoomBoss" and len(self.blackboard.game.get_real_potions()) > 0:
			potion_action = self.use_next_potion()
			if potion_action is not None:
				return self.decide(potion_action)
		if self.blackboard.game.play_available:
			return self.decide(self.get_play_card_action())
		return self.decide(EndTurnAction())

	def is_monster_attacking(self):
		for monster in self.blackboard.game.monsters:
			if monster.intent.is_attack() or monster.intent == Intent.NONE:
				return True
		return False

	def get_incoming_damage(self):
		incoming_damage = 0
		for monster in self.blackboard.game.monsters:
			if not monster.is_gone and not monster.half_dead:
				if monster.move_adjusted_damage is not None:
					incoming_damage += monster.move_adjusted_damage * monster.move_hits
				elif monster.intent == Intent.NONE:
					incoming_damage += 5 * self.blackboard.game.act
		return incoming_damage

	def get_low_hp_target(self):
		available_monsters = [monster for monster in self.blackboard.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		best_monster = min(available_monsters, key=lambda x: x.current_hp)
		return best_monster

	def get_high_hp_target(self):
		available_monsters = [monster for monster in self.blackboard.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		best_monster = max(available_monsters, key=lambda x: x.current_hp)
		return best_monster

	def many_monsters_alive(self):
		available_monsters = [monster for monster in self.blackboard.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		return len(available_monsters) > 1

	def get_play_card_action(self):
		playable_cards = [card for card in self.blackboard.game.hand if card.is_playable]
		zero_cost_cards = [card for card in playable_cards if card.cost == 0]
		zero_cost_attacks = [card for card in zero_cost_cards if card.type == spirecomm.spire.card.CardType.ATTACK]
		zero_cost_non_attacks = [card for card in zero_cost_cards if card.type != spirecomm.spire.card.CardType.ATTACK]
		nonzero_cost_cards = [card for card in playable_cards if card.cost != 0]
		aoe_cards = [card for card in playable_cards if self.priorities.is_card_aoe(card)]
		if self.blackboard.game.player.block > self.get_incoming_damage() - (self.blackboard.game.act + 4):
			offensive_cards = [card for card in nonzero_cost_cards if not self.priorities.is_card_defensive(card)]
			if len(offensive_cards) > 0:
				nonzero_cost_cards = offensive_cards
			else:
				nonzero_cost_cards = [card for card in nonzero_cost_cards if not card.exhausts]
		if len(playable_cards) == 0:
			return self.decide(EndTurnAction())
		if len(zero_cost_non_attacks) > 0:
			card_to_play = self.priorities.get_best_card_to_play(zero_cost_non_attacks)
		elif len(nonzero_cost_cards) > 0:
			card_to_play = self.priorities.get_best_card_to_play(nonzero_cost_cards)
			if len(aoe_cards) > 0 and self.many_monsters_alive() and card_to_play.type == spirecomm.spire.card.CardType.ATTACK:
				card_to_play = self.priorities.get_best_card_to_play(aoe_cards)
		elif len(zero_cost_attacks) > 0:
			card_to_play = self.priorities.get_best_card_to_play(zero_cost_attacks)
		else:
			# This shouldn't happen!
			return self.decide(EndTurnAction())
		if card_to_play.has_target:
			available_monsters = [monster for monster in self.blackboard.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			if len(available_monsters) == 0:
				return self.decide(EndTurnAction())
			if card_to_play.type == spirecomm.spire.card.CardType.ATTACK:
				target = self.get_low_hp_target()
			else:
				target = self.get_high_hp_target()
			return PlayCardAction(card=card_to_play, target_monster=target)
		else:
			return PlayCardAction(card=card_to_play)

	def use_next_potion(self):
		for potion in self.blackboard.game.get_real_potions():
			if potion.can_use:
				if potion.requires_target:
					return PotionAction(True, potion=potion, target_monster=self.get_low_hp_target())
				else:
					return PotionAction(True, potion=potion)

	# TODO
	def handle_event(self):
		#if self.blackboard.game.screen.event_id in ["Vampires", "Masked Bandits", "Knowing Skull", "Ghosts", "Liars Game", "Golden Idol", "Drug Dealer", "The Library"]:
		#		return ChooseAction(len(self.blackboard.game.screen.options) - 1)
		return ChooseAction(0)
		
	# TODO
	def handle_chest(self):
		return OpenChestAction()
		
	# TODO
	def handle_shop(self):
		return ProceedAction()
		#return ChooseShopkeeperAction()
		
	# TODO
	def handle_shop_screen(self):
		self.game.visited_shop = True
		if self.blackboard.game.screen.purge_available and self.blackboard.game.gold >= self.blackboard.game.screen.purge_cost:
			return ChooseAction(name="purge")
		for card in self.blackboard.game.screen.cards:
			if self.blackboard.game.gold >= card.price and not self.priorities.should_skip(card):
				return BuyCardAction(card)
		for relic in self.blackboard.game.screen.relics:
			if self.blackboard.game.gold >= relic.price:
				return BuyRelicAction(relic)
		return CancelAction()
		
		
	# TODO
	def handle_rewards(self):
		for reward_item in self.blackboard.game.screen.rewards:
			if reward_item.reward_type == RewardType.POTION and self.blackboard.game.are_potions_full():
				continue
			elif reward_item.reward_type == RewardType.CARD and self.skipping_card:
				continue
			else:
				return CombatRewardAction(reward_item)
		return ProceedAction()
		
	# TODO
	def handle_boss_reward(self):
		relics = self.blackboard.game.screen.relics
		best_boss_relic = self.priorities.get_best_boss_relic(relics)
		return BossRewardAction(best_boss_relic)
		
	def handle_grid(self):
		if not self.blackboard.game.choice_available:
			return ProceedAction()
		if self.blackboard.game.screen.for_upgrade or self.choose_good_card:
			available_cards = self.priorities.get_sorted_cards(self.blackboard.game.screen.cards)
		else:
			available_cards = self.priorities.get_sorted_cards(self.blackboard.game.screen.cards, reverse=True)
		num_cards = self.blackboard.game.screen.num_cards
		return CardSelectAction(available_cards[:num_cards])
		
	def handle_hand_select(self):
		if not self.blackboard.game.choice_available:
			return ProceedAction()
		# Usually, we don't want to choose the whole hand for a hand select. 3 seems like a good compromise.
		num_cards = min(self.blackboard.game.screen.num_cards, 3)
		return CardSelectAction(self.priorities.get_cards_for_action(self.blackboard.game.current_action, self.blackboard.game.screen.cards, num_cards))
		
		
	def handle_screen(self):
		if self.blackboard.game.screen_type == ScreenType.EVENT:
			return self.handle_event()
		elif self.blackboard.game.screen_type == ScreenType.CHEST:
			return self.handle_chest()
		elif self.blackboard.game.screen_type == ScreenType.SHOP_ROOM:
			return self.handle_shop()
		elif self.blackboard.game.screen_type == ScreenType.REST:
			return self.choose_rest_option()
		elif self.blackboard.game.screen_type == ScreenType.CARD_REWARD:
			return self.choose_card_reward()
		elif self.blackboard.game.screen_type == ScreenType.COMBAT_REWARD:
			return self.handle_rewards()
		elif self.blackboard.game.screen_type == ScreenType.MAP:
			return self.make_map_choice()
		elif self.blackboard.game.screen_type == ScreenType.BOSS_REWARD:
			return self.handle_boss_reward()
		elif self.blackboard.game.screen_type == ScreenType.SHOP_SCREEN:
			return self.handle_shop_screen();
		elif self.blackboard.game.screen_type == ScreenType.GRID:
			if not self.blackboard.game.choice_available:
				return ProceedAction()
			if self.blackboard.game.screen.for_upgrade or self.choose_good_card:
				available_cards = self.priorities.get_sorted_cards(self.blackboard.game.screen.cards)
			else:
				available_cards = self.priorities.get_sorted_cards(self.blackboard.game.screen.cards, reverse=True)
			num_cards = self.blackboard.game.screen.num_cards
			return CardSelectAction(available_cards[:num_cards])
		elif self.blackboard.game.screen_type == ScreenType.HAND_SELECT:
			if not self.blackboard.game.choice_available:
				return ProceedAction()
			# Usually, we don't want to choose the whole hand for a hand select. 3 seems like a good compromise.
			num_cards = min(self.blackboard.game.screen.num_cards, 3)
			return CardSelectAction(self.priorities.get_cards_for_action(self.blackboard.game.current_action, self.blackboard.game.screen.cards, num_cards))
		else:
			return ProceedAction()

	def choose_rest_option(self):
		rest_options = self.blackboard.game.screen.rest_options
		if len(rest_options) > 0 and not self.blackboard.game.screen.has_rested:
			if RestOption.REST in rest_options and self.blackboard.game.current_hp < self.blackboard.game.max_hp / 2:
				return RestAction(RestOption.REST)
			elif RestOption.REST in rest_options and self.blackboard.game.act != 1 and self.blackboard.game.floor % 17 == 15 and self.blackboard.game.current_hp < self.blackboard.game.max_hp * 0.9:
				return RestAction(RestOption.REST)
			elif RestOption.SMITH in rest_options:
				return RestAction(RestOption.SMITH)
			elif RestOption.LIFT in rest_options:
				return RestAction(RestOption.LIFT)
			elif RestOption.DIG in rest_options:
				return RestAction(RestOption.DIG)
			elif RestOption.REST in rest_options and self.blackboard.game.current_hp < self.blackboard.game.max_hp:
				return RestAction(RestOption.REST)
			else:
				return ChooseAction(0)
		else:
			return ProceedAction()

	def count_copies_in_deck(self, card):
		count = 0
		for deck_card in self.blackboard.game.deck:
			if deck_card.card_id == card.card_id:
				count += 1
		return count

	def choose_card_reward(self):
		reward_cards = self.blackboard.game.screen.cards
		if self.blackboard.game.screen.can_skip and not self.blackboard.game.in_combat:
			pickable_cards = [card for card in reward_cards if self.priorities.needs_more_copies(card, self.count_copies_in_deck(card))]
		else:
			pickable_cards = reward_cards
		if len(pickable_cards) > 0:
			potential_pick = self.priorities.get_best_card(pickable_cards)
			return CardRewardAction(potential_pick)
		elif self.blackboard.game.screen.can_bowl:
			return CardRewardAction(bowl=True)
		else:
			self.skipping_card = True
			return CancelAction()
			
	# TODO generate_map_route, then get the actual symbols in order that we'll encounter them
	def get_informative_path(self):
		pass

	# TODO How many possible paths are there? Should I just iterate through all possibilities and pick the one that best fits a set of heuristics?
	def generate_map_route(self):
		node_rewards = self.priorities.MAP_NODE_PRIORITIES.get(self.blackboard.game.act)
		best_rewards = {0: {node.x: node_rewards[node.symbol] for node in self.blackboard.game.map.nodes[0].values()}}
		best_parents = {0: {node.x: 0 for node in self.blackboard.game.map.nodes[0].values()}}
		min_reward = min(node_rewards.values())
		map_height = max(self.blackboard.game.map.nodes.keys())
		for y in range(0, map_height):
			best_rewards[y+1] = {node.x: min_reward * 20 for node in self.blackboard.game.map.nodes[y+1].values()}
			best_parents[y+1] = {node.x: -1 for node in self.blackboard.game.map.nodes[y+1].values()}
			for x in best_rewards[y]:
				node = self.blackboard.game.map.get_node(x, y)
				best_node_reward = best_rewards[y][x]
				for child in node.children:
					test_child_reward = best_node_reward + node_rewards[child.symbol]
					if test_child_reward > best_rewards[y+1][child.x]:
						best_rewards[y+1][child.x] = test_child_reward
						best_parents[y+1][child.x] = node.x
		best_path = [0] * (map_height + 1)
		best_rooms = [0] * (map_height + 1)
		best_path[map_height] = max(best_rewards[map_height].keys(), key=lambda x: best_rewards[map_height][x])
		for y in range(map_height, 0, -1):
			best_path[y - 1] = best_parents[y][best_path[y]]
			#best_rooms[y - 1] =  # TODO get symbol of best_path[y-1]
		self.map_route = best_path
		self.upcoming_rooms = best_rooms

	def make_map_choice(self):
		if len(self.blackboard.game.screen.next_nodes) > 0 and self.blackboard.game.screen.next_nodes[0].y == 0:
			self.generate_map_route()
			self.blackboard.game.screen.current_node.y = -1
		if self.blackboard.game.screen.boss_available:
			return ChooseMapBossAction()
		chosen_x = self.map_route[self.blackboard.game.screen.current_node.y + 1]
		for choice in self.blackboard.game.screen.next_nodes:
			if choice.x == chosen_x:
				return ChooseMapNodeAction(choice)
		# This should never happen
		return ChooseAction(0)

