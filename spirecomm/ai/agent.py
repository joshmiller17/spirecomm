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

	def __init__(self, logfile_name, chosen_class=PlayerClass.IRONCLAD):
		self.chosen_class = chosen_class
		self.change_class(chosen_class)
		self.action_delay = 0.5 # seconds delay per action, useful for actually seeing what's going on.
		self.debug_level = 6
		self.ascension = 0
		self.auto_pause = True # pause after warnings and errors
		self.debug_queue = ["AI initialized.", "Delay timer set to " + str(self.action_delay), "Debug level set to " + str(self.debug_level), "Auto pause is " + "ON" if self.auto_pause else "OFF"]
		self.cmd_queue = []
		self.last_action = None
		self.logfile_name = logfile_name
		self.logfile = open(self.logfile_name, 'a+')
		self.skipping_card = False
		self.paused = False
		self.step = False
		self.combat_round = 1
		self.state_id = 0 # debugging guide for tracking state
		self.root = SelectorBehaviour("Root Context Selector")
		self.init_behaviour_tree(self.root) # Warning: uses British spelling
		self.behaviour_tree = py_trees.trees.BehaviourTree(self.root)
		self.blackboard = py_trees.blackboard.Blackboard()
		self.blackboard.game = Game()
		self.blackboard.tracked_state = {} # game state info that the agent chooses to track
		self.blackboard.game.player = spirecomm.spire.character.Player(0)
		self.last_game_state = None
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
		self.log(filename + " loaded successfully")
		self.log(py_trees.display.ascii_tree(self.root), debug=6)
		
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
		if ("WARN" in msg or "ERR" in msg) and self.auto_pause:
			self.paused = True
			
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
		
	# equivalent to self.log(msg, debug=-1)
	def think(self, msg):
		self.debug_queue.append(msg)
			
	def get_next_cmd(self):
		try:
			return self.cmd_queue.pop()
		except:
			return StateAction()
			
	def decide(self, action):
		if action.command.startswith("end"):
			self.combat_round += 1
		if action.command.startswith("proceed"):
			self.combat_round = 1
		if self.step:
			self.log("> " + str(action), debug=3)
		else:
			self.log("> " + str(action), debug=5)
		return action
		
	# Check that the simulator predicted this outcome was possible
	def simulation_sanity_check(self, original_state, action):
		original_state.debug_file = self.logfile_name
		simulated_state = original_state.takeAction(action, from_real=True)
		while len(simulated_state.debug_log):
			self.log(simulated_state.debug_log.pop(0))
		real_diff = self.state_diff(original_state, self.blackboard.game, ignore_randomness=True)
		if real_diff == {}:
			self.log("WARN: real diff is null", debug=3)
			self.note(str(original_state))
			self.note(str(self.blackboard.game))
		sim_diff = self.state_diff(original_state, simulated_state, ignore_randomness=True)
		diff_diff = {}
		skip_warn = False
		for key, value in real_diff.items():
			if key not in sim_diff:
				diff_diff["sim_missing_" + key] = value
			else:
				val_diff = value != sim_diff[key]
				if type(value) is list: # compare lists in unordered way
					val_diff = set(value) != set(sim_diff[key])
				if val_diff:
					diff_diff["sims_val_" + key] = sim_diff[key]
					diff_diff["real_val_" + key] = value
		for key, value in sim_diff.items():
			if key not in real_diff:
				diff_diff["sim_added_" + key] = value
		#diff = self.state_diff(self.blackboard.game, simulated_state)
		if diff_diff != {}:
			# check for just drawing different cards
			# if simulated_state.just_reshuffled:
				# if len(simulated_state.hand) == len(self.blackboard.game.hand) and len(simulated_state.discard_pile) == len(self.blackboard.game.discard_pile) and original_state.known_top_cards == []:
					# self.log("minor warning: reshuffled different cards in simulation")
					# skip_warn = True
			# elif "sims_val_drawn" in diff_diff and "real_val_drawn" in diff_diff:
				# if len(simulated_state.hand) == len(self.blackboard.game.hand) and original_state.known_top_cards == []:
					# self.log("minor warning: drew different cards in simulation")
					# if len(diff_diff) == 2:
						# skip_warn = True
					
			if not skip_warn:
				self.log("WARN: simulation discrepency, see log for details", debug=3)
			self.log("actual/sim diff: " + str(diff_diff), debug=3)
			self.log("sim diff: " + str(sim_diff), debug=3)
			self.log("real diff: " + str(real_diff), debug=3)
			# self.note("Simulated:")
			# self.note(str(simulated_state))
			# self.note("Actual:")
			# self.note(str(self.blackboard.game))
		else:
			self.log("Simulation sanity check success!", debug=5)
		return simulated_state
		
	# Returns a dict of what changed between game states
	# ignore_randomness is used by simulation_sanity_check and ignores poor simulations due to chance
	def state_diff(self, state1, state2, ignore_randomness=False):	
	
		if state1.player is None or state2.player is None:
			self.log("ERR: Null player")
			if state1.player is None:
				self.log("in state 1")
				self.log(str(state1))
			else:
				self.log("in state 2")
				self.log(str(state2))
			raise Exception("Null player")
	
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
		if state1.player.current_hp != state2.player.current_hp:
			diff["current_hp"] = state2.player.current_hp - state1.player.current_hp
		if state1.player.max_hp != state2.player.max_hp:
			diff["max_hp"] = state2.player.max_hp - state1.player.max_hp
		if state1.floor != state2.floor:
			diff["floor"] = state2.floor
		if state1.act != state2.act:
			diff["act"] = state2.act
		if state1.gold != state2.gold:
			diff["gold"] = state2.gold - state1.gold
		#if state1.state_id != state2.state_id:
		#	diff["state_id"] = state2.state_id - state1.state_id
		if state1.combat_round != state2.combat_round:
			diff["combat_round"] = state2.combat_round - state1.combat_round
			
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
		

		if state1.in_combat and state2.in_combat:
		
			monster_changes = {}
			
			monsters1 = [monster for monster in state1.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			monsters2 = [monster for monster in state2.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]

			checked_monsters = []
			for monster1 in monsters1:
				for monster2 in monsters2:
					if monster1 == monster2 and monster1 not in checked_monsters:
						checked_monsters.append(monster1) # avoid checking twice
						m_id = monster1.monster_id + str(monster1.monster_index)
						if monster1.current_hp != monster2.current_hp:
							monster_changes[m_id + "_hp"] = monster2.current_hp - monster1.current_hp
						if monster1.block != monster2.block:
								monster_changes[m_id + "_block"] = monster2.block - monster1.block
							
						if monster1.powers != monster2.powers:
							powers_changed = self.get_power_changes(monster1.powers, monster2.powers)
							for name, amount in powers_changed.items():
								diff[m_id + "_power_change_" + name] = amount
								self.log("DEBUG: m1 powers are " + str([str(power) for power in monster1.powers]))
								self.log("DEBUG: m2 powers are " + str([str(power) for power in monster2.powers]))
								self.log("DEBUG: m1 is " + str(monster1))
								self.log("DEBUG: m2 is " + str(monster2))
						break
						
					elif monster1 not in monsters2:
						try:
							unavailable_monster = [monster for monster in state2.monsters if monster1 == monster][0]
							cause = "unknown"
							if unavailable_monster.half_dead:
								cause = "half dead"
							elif unavailable_monster.is_gone or unavailable_monster.current_hp <= 0:
								cause = "is gone / dead"
						except:
							cause = "no longer exists"
						
						monster_changes[monster1.monster_id + str(monster1.monster_index) + "_not_available"] = cause
					elif monster2 not in monsters1:
						monster_changes[monster1.monster_id + str(monster1.monster_index) + "_returned_with_hp"] = monster2.current_hp
								
						
			
			if monster_changes != {}:
				for key, value in monster_changes.items():
					diff[key] = value
			
			# general fixme?: better record linking between state1 and state2? right now most record linking is by name or ID (which might not be the same necessarily)
			
			delta_hand = len(state2.hand) - len(state1.hand)
			delta_draw_pile = len(state2.draw_pile) - len(state1.draw_pile)
			delta_discard = len(state2.discard_pile) - len(state1.discard_pile)
			delta_exhaust = len(state2.exhaust_pile) - len(state1.exhaust_pile)
			if delta_hand != 0:
				diff["delta_hand"] = delta_hand
			if delta_draw_pile != 0:
				diff["delta_draw_pile"] = delta_draw_pile
			if delta_discard != 0:
				diff["delta_discard"] = delta_discard
			if delta_exhaust != 0:
				diff["delta_exhaust"] = delta_exhaust
			
			if not ignore_randomness:
		
				cards_changed_from_hand = set(state2.hand).symmetric_difference(set(state1.hand))
				cards_changed_from_draw = set(state2.draw_pile).symmetric_difference(set(state1.draw_pile))
				cards_changed_from_discard = set(state2.discard_pile).symmetric_difference(set(state1.discard_pile))
				cards_changed_from_exhaust = set(state2.exhaust_pile).symmetric_difference(set(state1.exhaust_pile))
				cards_changed = cards_changed_from_hand | cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
				cards_changed_outside_hand = cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
				
				choice_then_discard = ["Headbutt", "Armaments", "True Grit", "Dual Wield"]
				choice_then_exhaust = ["Warcry", "Infernal Blade"] # FIXME exhaust is possibly atomic with the card effect? more data collection needed, might need to make the card effect composite so that exhausting can happen atomically with effect
				
				card_actions = ["drawn", "hand_to_deck", "discovered", "exhausted", "exhumed", "discarded",
								"discard_to_hand", "deck_to_discard", "discard_to_deck",
								"discovered_to_deck", "discovered_to_discard", # "playability_changed", <- deprecated
								 "power_played", "upgraded", "exhausted_from_deck", "unknown_change", "err_pc"]
				
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
					elif card in state1.draw_pile and card in state2.exhaust_pile:
						# havoc etc
						diff["exhausted_from_deck"].append(card.get_id_str())
						continue
						
					elif card in cards_changed_from_discard and card in cards_changed_from_draw:
						#deck to discard
						if card in state2.discard_pile:
							diff["deck_to_discard"].append(card.get_id_str())
							continue
						# discard to draw_pile
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
					elif card in state2.draw_pile and card not in state1.draw_pile and card not in state1.hand and card not in state1.discard_pile and card not in state1.exhaust_pile:
						# discovered to draw pile, e.g. status effect
						diff["discovered_to_deck"].append(card.get_id_str())
						continue
					elif card in state2.discard_pile and card not in state1.discard_pile and card not in state1.hand and card not in state1.draw_pile and card not in state1.exhaust_pile:
						# discovered to discard, e.g. status effect
						diff["discovered_to_discard"].append(card.get_id_str())
						continue
					elif card.get_base_name() in choice_then_discard and card in state2.discard_pile: # these cards are weird since they get played and there's a state of change before it's discarded
						diff["made_choice_then_discarded"].append(card.get_id_str())
					elif card.get_base_name() in choice_then_exhaust and card in state2.exhaust:  # these cards are weird since they get played and there's a state of change before it's exhausted
						diff["made_choice_then_exhausted"].append(card.get_id_str())
					else:
						self.log("WARN: unknown card change " + card.get_id_str(), debug=3)
						diff["unknown_change"].append(card.get_id_str())
						if card in state1.draw_pile:
							self.log("card was in state1 draw pile")
						if card in state2.draw_pile:
							self.log("card is in state2 draw pile")
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
				powers_changed = self.get_power_changes(state1.player.powers, state2.player.powers)
				for name, amount in powers_changed.items():
					diff["player_power_change_" + name] = amount
					

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
		
	# return a dict of powers and amount difference, assume 0 for non existent
	def get_power_changes(self, powers1, powers2):
		# convert tuples to dicts
		p1 = {}
		p2 = {}
		for p in powers1:
			p1[p.power_name] = p.amount
		for p in powers2:
			p2[p.power_name] = p.amount
			

		diff = {}
		powers = set(())
		for p in p1.keys():
			powers.add(p)
		for p in p2.keys():
			powers.add(p)
		for power in powers:
			amt1 = 0
			if power in p1:
				amt1 = p1[power]
			amt2 = 0
			if power in p2:
				amt2 = p2[power]
			if amt2 != amt1:
				diff[power] = amt2 - amt1
		
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
		self.log("WARN: Agent received error " + str(error), debug=2)
		#self.state_diff(self.last_game_state, self.blackboard.game) == {}
		if "Invalid command" in str(error):
			if "error" in str(error):
				self.log(traceback.format_exc(), debug=2)
				self.log(str(sys.exc_info()), debug=2)
				print(traceback.format_exc(), file=self.logfile, flush=True)
			# Assume this just means we're paused
			self.log("Invalid command error", debug=3)
			self.last_action = StateAction()
			return StateAction()
		else:
			# FIXME I think this is related to unpausing from in-game pause menu, we accidentally input an un-initialized play
			# For now, just try again
			self.log(str(error), debug=3)
			self.log(traceback.format_exc(), debug=2)
			self.log(str(sys.exc_info()), debug=2)
			print(traceback.format_exc(), file=self.logfile, flush=True)
			self.last_action = StateAction()
			return StateAction()
			
		"""
		Some errors we might receive:
		Index X out of bounds in command ...
		Selected card requires an enemy target
		Selected card cannot be played with the selected target
		"""
		
	def default_logic(self, game_state):
	
		if self.blackboard.game.choice_available:
			return self.decide(self.handle_screen())
		if self.blackboard.game.proceed_available:
			return self.decide(ProceedAction())
		if self.blackboard.game.play_available or self.blackboard.game.end_available:
			return self.handle_combat()
		if self.blackboard.game.cancel_available:
			return self.decide(CancelAction())
		self.log("ERR: no choices available. Game paused?", debug=2)
		self.last_action = StateAction()
		return StateAction()
		

	def get_next_action_in_game(self, game_state):
		self.last_game_state = self.blackboard.game
		self.blackboard.game = game_state
		
		if self.blackboard.game.player is None:
			if self.last_game_state.player is not None:
				self.blackboard.game.player = self.last_game_state.player # persist the player
			else:
				raise Exception("Previous game state did not have a Player")
		self.state_id += 1
		self.blackboard.game.state_id = self.state_id
		self.blackboard.game.combat_round = self.combat_round
				
		# Check difference from last state
		self.log("True Diff: " + str(self.state_diff(self.last_game_state, self.blackboard.game)), debug=6)
		if self.blackboard.game.in_combat and self.last_game_state.in_combat and self.last_action is not None:
			simulated_state = self.simulation_sanity_check(self.last_game_state, self.last_action) # check if we predicted this
			self.blackboard.tracked_state = simulated_state.tracked_state # FIXME this assumes we always simulate well, we'll need a fallback option for a way to figure out the correct tracked state when our simulation is wrong due to random chance
			self.blackboard.game.tracked_state = self.blackboard.tracked_state
		
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
		if len(self.cmd_queue) > 0:
			self.log("WARN: command queue is non-empty: " + str(self.cmd_queue), debug=3)
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
					if self.debug_level >= 5:
						if monster.move_hits > 1:
							self.think("{}{} is hitting me for {}x{} damage".format(monster.monster_id, index_str, monster.move_adjusted_damage, monster.move_hits))
						else:
							self.think("{}{} is hitting me for {} damage".format(monster.monster_id, index_str, monster.move_adjusted_damage))
						#self.think("    adjusted: {}, base: {}".format(monster.move_adjusted_damage, monster.move_base_damage))
		
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
		# Drink potions whenever we get one to see what they do lulz
		if self.blackboard.game.room_type == "MonsterRoomBoss" or self.blackboard.game.room_type == "MonsterRoom" and len(self.blackboard.game.get_real_potions()) > 0:
			potion_action = self.use_next_potion()
			if potion_action is not None:
				return self.decide(potion_action)
		if self.blackboard.game.play_available:
			return self.decide(self.get_play_card_action())
		return EndTurnAction()

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
			return EndTurnAction()
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
			return EndTurnAction()
		if card_to_play.has_target:
			available_monsters = [monster for monster in self.blackboard.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			if len(available_monsters) == 0:
				return EndTurnAction()
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
		self.log("Encountered event: " + str(self.blackboard.game.screen.event_id))
		
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
		self.blackboard.game.tracked_state["visited_shop"] = True
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
		self.skipping_card = False;
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
			if RestOption.REST in rest_options and self.blackboard.game.player.current_hp < self.blackboard.game.player.max_hp / 2:
				return RestAction(RestOption.REST)
			elif RestOption.REST in rest_options and self.blackboard.game.act != 1 and self.blackboard.game.floor % 17 == 15 and self.blackboard.game.current_hp < self.blackboard.game.max_hp * 0.9:
				return RestAction(RestOption.REST)
			elif RestOption.SMITH in rest_options:
				return RestAction(RestOption.SMITH)
			elif RestOption.LIFT in rest_options:
				return RestAction(RestOption.LIFT)
			elif RestOption.DIG in rest_options:
				return RestAction(RestOption.DIG)
			elif RestOption.REST in rest_options and self.blackboard.game.player.current_hp < self.blackboard.game.player.max_hp:
				return RestAction(RestOption.REST)
		else:
			return ProceedAction()

	def count_copies_in_deck(self, card):
		count = 0
		for deck_card in self.blackboard.game.deck:
			if deck_card.card_id == card.card_id:
				count += 1
		return count

	def choose_card_reward(self):
		# always take a card lulz
		reward_cards = self.blackboard.game.screen.cards
		potential_pick = self.priorities.get_best_card(reward_cards)
		return CardRewardAction(card=potential_pick)
		
			
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

