from enum import Enum
import copy
import random
import math
import os


import spirecomm.spire.relic
import spirecomm.spire.card
import spirecomm.spire.character
import spirecomm.spire.map
import spirecomm.spire.potion
import spirecomm.spire.screen
import spirecomm.spire.power

from spirecomm.communication.action import *


# MCTS values for changes to game state
MCTS_MAX_HP_VALUE = 7
MCTS_HP_VALUE = 1
MCTS_POTION_VALUE = 7 # TODO change by potion type, evolved by behaviour tree
MCTS_ROUND_COST = 0.5 # penalize long fights
# TODO add cost for losing gold (e.g. to thieves) -- note, somehow count how much gold was stolen and report that it will return if we kill the thief
# TODO eventually add: value for deck changes (e.g. cost for gaining parasite)
# TODO eventually add: value for card misc changes (e.g., genetic algorithm, ritual dagger)

BUFFS = ["Ritual", "Strength", "Dexterity", "Incantation", "Enrage", "Metallicize", "SadisticNature", "Juggernaut", "DoubleTap", "DemonForm", "DarkEmbrace", "Brutality", "Berserk", "Rage", "Feel No Pain", "Flame Barrier", "Corruption", "Combust", "Fire Breathing", "Mayhem"]
DEBUFFS = ["Frail", "Vulnerable", "Weakened", "Entangled", "Shackles", "NoBlock", "No Draw", "Strength Down", "Dexterity Down", "Focus Down"]
PASSIVE_EFFECTS = ["Strike Damage", "Ethereal"] # these don't do anything by themselves
VALID_CLASSES = ["COLORLESS", "IRONCLAD", "THE_SILENT", "DEFECT"]

class Reward:
	
	def __init__(self, reward={}):
		self.totalItemized = reward
		
	def __str__(self):
		ret = ", ".join([key + ": " + str(value) for key, value in self.totalItemized.items()])
		return ret
		
	def addReward(self, reward):
		if reward is None:
			return self
		for key, value in reward.totalItemized.items():
			if key in self.totalItemized:
				self.totalItemized[key] += value
			else:
				self.totalItemized[key] = value
		return self
		
	def getTotalReward(self):
		ret = 0
		for key, value in self.totalItemized.items():
			ret += value
		return ret
		
	def getTotalItemized(self):
		return self.totalItemized
		
# TODO add simulator.log to README
class Simulator:

	def __init__(self):
		self.game = None
		self.debug_file = "simulator.log"
		self.debug_log = []
		
		# from JSON for discovery: ignores cards that are from an event or healing, sort by class
		self.cards = {"ATTACK": {}, "SKILL": {}, "POWER": {}}
		for player_class in VALID_CLASSES:
			self.cards[player_class] = {"RARE":[], "UNCOMMON": [], "COMMON": [], "BASIC": []}
			
		self.load_cards_from_json()
		
		
	def load_cards_from_json(self):
		CARDS_PATH = os.path.join(config.SPIRECOMM_PATH, "spirecomm", "ai", "cards")
		d = open(self.debug_file, 'a+')
		for root, dirs, files in os.walk(CARDS_PATH):
			for f in files:
				err=False
				try:
					card = spirecomm.spire.card.Card(f[:-5], f[:-5], -1, -1, compare_to_real=False)
					if card.is_discoverable:
						self.cards[card.metadata["type"]][card.metadata["class"]][card.metadata["rarity"]].append(card)
						
				except Exception as e:
					err=True
					print("Error loading card: " + f, file=d, flush=True)
					print("    --" + str(e), file=d, flush=True)
					
				if not err:
					print("Success: " + f, file=d, flush=True)
		d.close()
		
		
		
	# TODO change instances of self to self.game
		

	# related to agent.state_diff(), this function takes a key, value pair from state_diff and creates that change to the state
	def changeState(self, key, value):
		set_attrs = ["room_phase", "room_type", "current_action", "act_boss", "floor", "act", "in_combat"]
		if key in set_attrs:
			setattr(self, key, value)
		if key == "choices_added":
			for v in value:
				self.choice_list.append(v)
		if key == "choices_removed":
			for v in value:
				self.choice_list.remove(v)
		change_attrs = ["gold", "state_id", "combat_round"]
		if key in change_attrs:
			setattr(self, key, self.key + value)
		if key == "relics":
			for v in value:
				if type(v) is tuple and len(v) == 2:
					self.set_relic_counter(v[0], self.get_relic(v[0].counter) + v[1])
				else:
					if self.has_relic(v):
						self.relics.remove(v)
					else:
						self.relics.append(v)
			

		# FIXME state_diff gives string, not the actual card object we would need to do this
		# if key == "cards_added":
			# for v in value:
				# self.deck.append(v)
		# if key == "cards_removed":
			# for v in value:
				# self.deck.remove(v)
		# if key == "cards_upgraded":
			# pass
			

		if key == "potions_added":
			for v in value:
				for p in self.potions:
					if p.name == "Potion Slot":
						p.name = v
						break
		
		if key == "potions_removed":
			for v in value:
				for p in self.potions:
					if p.name == v:
						p.name = "Potion Slot"
						break

		
	
			
			# monsters1 = [monster for monster in state1.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			# monsters2 = [monster for monster in state2.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]

			# checked_monsters = []
			# for monster1 in monsters1:
				# for monster2 in monsters2:
					# if monster1 == monster2 and monster1 not in checked_monsters:
						# checked_monsters.append(monster1) # avoid checking twice
						# m_id = monster1.monster_id + str(monster1.monster_index)
						# if monster1.current_hp != monster2.current_hp:
							# monster_changes[m_id + "_hp"] = monster2.current_hp - monster1.current_hp
						# if monster1.block != monster2.block:
								# monster_changes[m_id + "_block"] = monster2.block - monster1.block
							
						# if monster1.powers != monster2.powers:
							# monster_changes[m_id + "_powers_changed"] = []
							# monster_changes[m_id + "_powers_added"] = []
							# monster_changes[m_id + "_powers_removed"] = []
							# powers_changed = set([p.power_name for p in set(monster2.powers).symmetric_difference(set(monster1.powers))])
							# for name in powers_changed:
								# powers1 = [p.power_name for p in monster1.powers]
								# powers2 = [p.power_name for p in monster2.powers]
								# if name in powers1 and name in powers2:
									# monster_changes[m_id + "_powers_changed"].append((name, monster2.get_power(name).amount - monster1.get_power(name).amount))
									# continue
								# elif name in powers2:
									# monster_changes[m_id + "_powers_added"].append((name, monster2.get_power(name).amount))
									# continue
								# elif name in powers1:
									# monster_changes[m_id + "_powers_removed"].append((name, monster1.get_power(name).amount))
									# continue
								
							# if monster_changes[m_id + "_powers_added"] == []:
								# monster_changes.pop(m_id + "_powers_added", None)
							# if monster_changes[m_id + "_powers_removed"] == []:
								# monster_changes.pop(m_id + "_powers_removed", None)
							# if monster_changes[m_id + "_powers_changed"] == []:
								# monster_changes.pop(m_id + "_powers_changed", None)
						# break
						
					# elif monster1 not in monsters2:
						# try:
							# unavailable_monster = [monster for monster in state2.monsters if monster1 == monster][0]
							# cause = "unknown"
							# if unavailable_monster.half_dead:
								# cause = "half dead"
							# elif unavailable_monster.is_gone or unavailable_monster.current_hp <= 0:
								# cause = "is gone / dead"
						# except:
							# cause = "no longer exists"
						
						# monster_changes[monster1.monster_id + str(monster1.monster_index) + "_not_available"] = cause
					# elif monster2 not in monsters1:
						# monster_changes[monster1.monster_id + str(monster1.monster_index) + "_returned_with_hp"] = monster2.current_hp
								
						
			
			# if monster_changes != {}:
				# for key, value in monster_changes.items():
					# diff[key] = value
			
			# # general fixme?: better record linking between state1 and state2? right now most record linking is by name or ID (which might not be the same necessarily)
			
			# delta_hand = len(state2.hand) - len(state1.hand)
			# delta_draw_pile = len(state2.draw_pile) - len(state1.draw_pile)
			# delta_discard = len(state2.discard_pile) - len(state1.discard_pile)
			# delta_exhaust = len(state2.exhaust_pile) - len(state1.exhaust_pile)
			# if delta_hand != 0:
				# diff["delta_hand"] = delta_hand
			# if delta_draw_pile != 0:
				# diff["delta_draw_pile"] = delta_draw_pile
			# if delta_discard != 0:
				# diff["delta_discard"] = delta_discard
			# if delta_exhaust != 0:
				# diff["delta_exhaust"] = delta_exhaust
			
			# if not ignore_randomness:
		
				# cards_changed_from_hand = set(state2.hand).symmetric_difference(set(state1.hand))
				# cards_changed_from_draw = set(state2.draw_pile).symmetric_difference(set(state1.draw_pile))
				# cards_changed_from_discard = set(state2.discard_pile).symmetric_difference(set(state1.discard_pile))
				# cards_changed_from_exhaust = set(state2.exhaust_pile).symmetric_difference(set(state1.exhaust_pile))
				# cards_changed = cards_changed_from_hand | cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
				# cards_changed_outside_hand = cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
				
				# card_actions = ["drawn", "hand_to_deck", "discovered", "exhausted", "exhumed", "discarded",
								# "discard_to_hand", "deck_to_discard", "discard_to_deck",
								# "discovered_to_deck", "discovered_to_discard", # "playability_changed", <- deprecated
								 # "power_played", "upgraded", "unknown_change", "err_pc"]
				
				# for a in card_actions:
					# diff[a] = []
					
				# # TODO some checks if none of these cases are true
				# for card in cards_changed:
					# if card in cards_changed_from_draw and card in cards_changed_from_hand:
						# # draw
						# if card in state2.hand:
							# diff["drawn"].append(card.get_id_str())
							# continue
						# # hand to deck
						# elif card in state1.hand:
							# diff["hand_to_deck"].append(card.get_id_str())
							# continue	
					# elif card in cards_changed_from_hand and card in cards_changed_from_discard:
						# # discard
						# if card in state1.hand:
							# diff["discarded"].append(card.get_id_str())
							# continue
						# # discard to hand
						# elif card in state2.hand:
							# diff["discard_to_hand"].append(card.get_id_str())
							# continue	
					# elif card in cards_changed_from_exhaust and card in cards_changed_from_hand:
						# #exhaust
						# if card in state1.hand:
							# diff["exhausted"].append(card.get_id_str())
							# continue
						# #exhume
						# elif card in state2.hand:
							# diff["exhumed"].append(card.get_id_str())
							# continue
					# elif card in cards_changed_from_discard and card in cards_changed_from_draw:
						# #deck to discard
						# if card in state2.discard_pile:
							# diff["deck_to_discard"].append(card.get_id_str())
							# continue
						# # discard to draw_pile
						# elif card in state1.discard_pile:
							# diff["discard_to_deck"].append(card.get_id_str())
							# continue
					# elif card in cards_changed_from_hand and card in state2.hand and card not in cards_changed_outside_hand:
						# #discovered
						# if card not in state1.hand and card not in state1.draw_pile and card not in state1.discard_pile and card not in state1.exhaust_pile:
							# diff["discovered"].append(card.get_id_str())
							# continue
					# elif card in cards_changed_from_hand and card in state1.hand and card not in cards_changed_outside_hand:
						# if card.type is spirecomm.spire.card.CardType.POWER and card not in state2.hand:
							# # power played
							# diff["power_played"].append(card.get_id_str())
							# continue
						# elif card.upgrades > 0: # assume upgrading it was the different thing
							# diff["upgraded"].append(card.get_id_str()) # FIXME check this more strongly
							# continue	
					# elif card in state2.draw_pile and card not in state1.draw_pile and card not in state1.hand and card not in state1.discard_pile and card not in state1.exhaust_pile:
						# # discovered to draw pile, e.g. status effect
						# diff["discovered_to_deck"].append(card.get_id_str())
						# continue
					# elif card in state2.discard_pile and card not in state1.discard_pile and card not in state1.hand and card not in state1.draw_pile and card not in state1.exhaust_pile:
						# # discovered to discard, e.g. status effect
						# diff["discovered_to_discard"].append(card.get_id_str())
						# continue
					# else:
						# self.log("WARN: unknown card change " + card.get_id_str(), debug=3)
						# diff["unknown_change"].append(card.get_id_str())
						# if card in state1.draw_pile:
							# self.log("card was in state1 draw pile")
						# if card in state2.draw_pile:
							# self.log("card is in state2 draw pile")
						# if card in state1.discard_pile:
							# self.log("card was in state1 discard")
						# if card in state2.discard_pile:
							# self.log("card is in state2 discard")
						# if card in state1.hand:
							# self.log("card was in state1 hand")
						# if card in state2.hand:
							# self.log("card is in state2 hand")
						# if card in state1.exhaust_pile:
							# self.log("card was in state1 exhaust")
						# if card in state2.exhaust_pile:
							# self.log("card is in state2 exhaust")
				
				# for a in card_actions:
					# if diff[a] == []:
						# diff.pop(a, None)
		
			# if state1.player.block != state2.player.block:
				# diff["block"] = state2.player.block - state1.player.block
				
			# if state1.player.powers != state2.player.powers:
				# diff["powers_changed"] = []
				# diff["powers_added"] = []
				# diff["powers_removed"] = []
				# powers_changed = set(state2.player.powers).symmetric_difference(set(state1.player.powers))
				# for power in powers_changed:
					# #power1 = next(p for p in state1.player.powers if p.power_name == power.power_name)
					# #power2 = next(p for p in state2.player.powers if p.power_name == power.power_name)
					# if power in state1.player.powers and power in state2.player.powers:
							# diff["powers_changed"].append((power.power_name, power2.amount - power1.amount))
					# elif power in state2.player.powers:
						# for p2 in state2.player.powers:
							# if p2.power_name == power.power_name:
								# diff["powers_added"].append((p2.power_name, p2.amount))
								# continue
					# elif power in state1.player.powers:
						# for p1 in state1.player.powers:
							# if p1.power_name == power.power_name:
								# diff["powers_added"].append((p1.power_name, p1.amount))
								# continue
									
				# if diff["powers_added"] == []:
					# diff.pop("powers_added", None)
				# if diff["powers_removed"] == []:
					# diff.pop("powers_removed", None)
				# if diff["powers_changed"] == []:
					# diff.pop("powers_changed", None)

	# True iff either we're dead or the monsters are (or we smoke bomb)
	def isTerminal(self):
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		return self.player.current_hp <= 0 or len(available_monsters) < 1 or not self.in_combat
		
	# return value of terminal state
	def getReward(self):
		
		# Trace back to where we started
		original_game_state = self
		while original_game_state.original_state is not None:
			original_game_state = original_game_state.original_state
			
		delta_hp = self.player.current_hp - original_game_state.player.current_hp
		delta_max_hp = self.player.max_hp - original_game_state.player.max_hp
		orig_potions = 0
		for p in original_game_state.potions:
			if p.name != "Potion Slot":
				orig_potions += 1
		delta_potions = -1 * orig_potions
		for p in original_game_state.potions:
			if p.name != "Potion Slot":
				delta_potions += 1
		
		r = {}
		r["HP"] = delta_hp * MCTS_HP_VALUE
		r["max HP"] = delta_max_hp * MCTS_MAX_HP_VALUE
		#r["potions"] = delta_potions * MCTS_POTION_VALUE
		#r -= self.combat_round * MCTS_ROUND_COST
		reward = Reward(r)
		
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				d.write("\n~~~~~~~~~~~~~~\n")
				d.write("\nTerminal state reached, reward: " + str(reward.getTotalItemized()) + "\n")
				d.write(str(self))
				d.write("\n~~~~~~~~~~~~~~\n")
		
		return reward


	def getPossibleActions(self):
		if self.tracked_state["possible_actions"] == None:
		
			possible_actions = [EndTurnAction()]
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				pass
				#monster.recognize_intents() # FIXME
			
			for potion in self.get_real_potions():
				if potion.requires_target:
					for monster in available_monsters:
						possible_actions.append(PotionAction(True, potion=potion, target_monster=monster))
				else:
					possible_actions.append(PotionAction(True, potion=potion))
					
			for card in self.hand:
				if len(available_monsters) == 0 and card.type != spirecomm.spire.card.CardType.POWER:
					continue
				if card.cost > self.player.energy:
					continue
				if card.has_target:
					for monster in available_monsters:
						possible_actions.append(PlayCardAction(card=card, target_monster=monster))
				else:
					possible_actions.append(PlayCardAction(card=card))
			
			if self.debug_file:
				with open(self.debug_file, 'a+') as d:
					d.write(str(self))
					d.write("\n-----------------------------\n")
					d.write("Possible Actions:\n")
					d.write("\n".join([str(a) for a in possible_actions]))
					d.write('\n')

			self.tracked_state["possible_actions"] = possible_actions
				
		return self.tracked_state["possible_actions"]
		
	def get_upgradable_cards(self, cards):
		upgradable = []
		for card in cards:
			if card.upgrades == 0 or card.get_base_name() == "Searing Blow":
				upgradable.append(card)
		return upgradable
		
	# a test bed for checking our surroundings
	def debug_game_state(self):
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for monster in available_monsters:
			if monster.monster_id == "Lagavulin":
				self.debug_log.append("Lagavulin's powers: " + str([str(power) for power in monster.powers]))
	
	
	# Returns a new state
	def takeAction(self, action, from_real=False):
	
		if self.in_combat and not self.tracked_state["registered_start_of_combat"]:
			self.apply_start_of_combat_effects()
			self.tracked_state["registered_start_of_combat"] = True
	
		if from_real:
			self.tracked_state["is_simulation"] = False
	
		self.debug_game_state()
	
		self.debug_log.append("Simulating taking action: " + str(action))
		#self.debug_log.append("Combat round: " + str(self.combat_round))
	
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				d.write("\nSimulating taking action: " + str(action) + "\n")
		
		new_state = copy.deepcopy(self)
		new_state.tracked_state["possible_actions"] = None
		new_state.original_state = self
		new_state.state_id += 1
		
		new_state.tracked_state["just_reshuffled"] = False
		
		if action.command.startswith("end") and not self.screen_up:
			return new_state.simulate_end_turn(action)
		elif action.command.startswith("potion") and not self.screen_up:
			# assumes we have this potion, will throw an error if we don't I think
			return new_state.simulate_potion(action)
		elif action.command.startswith("play") and not self.screen_up:
			return new_state.simulate_play(action)
		elif action.command.startswith("state"):
			return new_state
		elif action.command.startswith("choose") and self.screen_up and new_state.current_action == "DiscoveryAction":
			return new_state.simulate_discovery(action)
		elif action.command.startswith("choose") and self.screen_up and new_state.current_action == "ExhaustAction":
			return new_state.simulate_exhaust(action)
		elif action.command.startswith("choose") and self.screen_up and new_state.current_action == "DiscardPileToTopOfDeckAction":
			return new_state.simulate_headbutt(action)
		elif action.command.startswith("choose") and self.screen_up and new_state.current_action == "PutOnDeckAction":
			return new_state.simulate_hand_to_topdeck(action)
		elif action.command.startswith("choose") and self.screen_up and new_state.current_action == "ArmamentsAction":
			return new_state.simulate_upgrade(action)
		elif action.command.startswith("choose") and self.screen_up and new_state.current_action == "DualWieldAction": # FIXME?
			return new_state.simulate_dual_wield(action)
		elif action.command.startswith("choose") and self.screen_up and new_state.current_action == "ExhumeAction": # FIXME?
			return new_state.simulate_exhume(action)
		elif action.command.startswith("choose") and self.screen_up and new_state.current_action == "ForethoughtAction": # FIXME?
			return new_state.simulate_forethought(action)
		else:
			raise Exception("Chosen simulated action is not a valid combat action in the current state: " + str(action) + ", " + str(self.screen) + " (" + str(self.screen_type) + ") " + ("[UP]" if self.screen_up else ""))
		
	def choose_move(self, monster):
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		if self.combat_round == 1 and "startswith" in monster.intents:
			selected_move = monster.intents["startswith"]
		elif monster.monster_id == "GremlinTsundere" and len(available_monsters) > 1:
			selected_move == "Protect"
		else:
			# make sure the attack we pick is not limited
			while True: # do-while
				move_weights = []
				moves = []
				moveset = monster.intents["moveset"]
				
				# change moveset to next move if exists
				if str(monster) in self.tracked_state["monsters_last_attacks"]:
					last_move = self.tracked_state["monsters_last_attacks"][str(monster)][0]
					self.debug_log.append("Last move was " + str(last_move) + "[" + str(self.tracked_state["monsters_last_attacks"][str(monster)][1]) + "]")
					if "next_move" in moveset[last_move]:
						list_of_next_moves = moveset[last_move]["next_move"]
						moveset = {}
						for movedict in list_of_next_moves:
							moveset[movedict["name"]] = monster.intents["moveset"][movedict["name"]]
							moveset[movedict["name"]]["probability"] = movedict["probability"]
						self.debug_log.append("Found next moves to be: " + str(moveset))
				
				# pick from our moveset
				if len(moveset) < 1:
					self.debug_log.append("ERR: no moves to pick from") # TODO remove after figuring out this bug
				for move, details in moveset.items():
					moves.append(move)
					move_weights.append(details["probability"])
				selected_move = random.choices(population=moves, weights=move_weights)[0] # choices returns as a list of size 1
				
				if selected_move is None:
					self.debug_log.append("ERR: selected move is none") # TODO remove after figuring out this bug
				
				# check limits
				if "limits" not in monster.intents or str(monster) not in self.tracked_state["monsters_last_attacks"]:
					# don't worry about limits, choose a random attack
					break
				else:
					exceeds_limit = False
					for limited_move, limited_times in monster.intents["limits"].items():
						if selected_move == limited_move and selected_move == self.tracked_state["monsters_last_attacks"][str(monster)][0]:
							if self.tracked_state["monsters_last_attacks"][str(monster)][1] + 1 >= limited_times: # selecting this would exceed limit:
								exceeds_limit = True
								self.debug_log.append("Tried to use " + selected_move + " but that would exceed a move limit")
					if not exceeds_limit:
						break
		
		# Check if Lagavulin should still be sleeping
		moveset = monster.intents["moveset"]
		if monster.monster_id == "Lagavulin":
			if monster.current_hp != monster.max_hp and self.tracked_state["lagavulin_is_asleep"]:
				# wake up
				selected_move = "Stunned"
				monster.add_power("Metallicize", -8)
				#monster.remove_power("Asleep") # I think this doesn't actually exist in the code
				self.tracked_state["lagavulin_is_asleep"] = False
		
		return selected_move
		
	def apply_end_of_player_turn_effects(self):
	
		# reset relics
		self.set_relic_counter("Kunai", 0)
		self.set_relic_counter("Shuriken", 0)
		self.set_relic_counter("Ornamental Fan", 0)
		self.set_relic_counter("Velvet Choker", 0)
		self.set_relic_counter("Letter Opener", 0)
		self.tracked_state["attacks_played_last_turn"] = self.tracked_state["attacks_played_this_turn"]
		self.tracked_state["attacks_played_this_turn"] = 0
		self.tracked_state["cards_played_last_turn"] = self.tracked_state["cards_played_this_turn"]
		self.tracked_state["cards_played_this_turn"] = 0
		self.tracked_state["skills_played_this_turn"] = 0
		self.tracked_state["powers_played_this_turn"] = 0
		self.tracked_state["necronomicon_triggered"] = False
		
		self.decrement_duration_powers(self.player)
		
		self.increment_relic("Stone Calendar")
		
		if self.player.has_power("Fire Breathing"):
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			amt = self.player.get_power_amount("Fire Breathing") * self.tracked_state["attacks_played_this_turn"]
			if amt > 0:
				for monster in available_monsters:
					self.apply_damage(amt, None, monster)
		
		if self.combat_round == 7 and self.has_relic("Stone Calendar"):
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				self.apply_damage(52, None, monster)
				
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for monster in available_monsters:
			if monster.has_power("Poison"):
				self.apply_damage(monster.get_power_amount("Poison"), None, monster, ignores_block=True)
				monster.decrement_power("Poison")
			
		
		if self.player.block == 0 and self.has_relic("Orichalcum"):
			self.player.block += 6 # note, this happens before all other end of turn block gaining effects like frost orbs, metallicize, etc
			
		if not self.has_relic("Ice Cream"):
			self.player.energy = 0
			
		# Hand discarded
		for card in self.hand:
			for effect in card.effects:
				if effect["effect"] == "Regret":
					self.lose_hp(self.player, len(self.hand), from_card=True)
				if effect["effect"] == "Ethereal":
					self.hand.remove(card)
					self.exhaust_card(card)
					continue
				elif effect["effect"] == "SelfWeakened":
					self.apply_debuff(self.player, "Weakened", effect["amount"])
				elif effect["effect"] == "SelfFrail":
					self.apply_debuff(self.player, "Frail", effect["amount"])
				elif effect["effect"] == "SelfDamage":
					self.apply_damage(effect["amount"], None, self.player)
					
		if not self.has_relic("Runic Pyramid"):
			self.discard_pile += self.hand
			self.hand = []
			
		if self.has_relic("Nilry's Codex"):
			pass # TODO discovery
		
		for power in self.player.powers:
			if power.power_name == "Strength Down":
				self.apply_debuff(self.player, "Strength", -1 * power.amount)
				self.player.remove_power("Strength Down")
			elif power.power_name == "Dexterity Down":
				self.apply_debuff(self.player, "Dexterity", -1 * power.amount)
				self.player.remove_power("Dexterity Down")
			elif power.power_name == "Focus Down":
				self.apply_debuff(self.player, "Focus", -1 * power.amount)
				self.player.remove_power("Focus Down")
			elif power.power_name == "Plated Armor":
				self.add_block(self.player, power.amount)
			elif power.power_name == "Metallicize":
				self.add_block(self.player, power.amount)
			elif power.power_name == "Combust":
				self.lose_hp(self.player, 1, from_card=True)
				available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
				for monster in available_monsters:
					monster.current_hp = max(monster.current_hp - power.amount, 0)
			elif power.power_name == "Regen":
				self.player.current_hp = min(self.player.current_hp + power.amount, self.player.max_hp)
				self.player.decrement_power(power.power_name)
			elif power.power_name == "DemonForm":
				character.add_power("Strength", power.amount)
				
	# orange pellets
	def remove_all_debuffs(self):
		for power in self.player.powers:
			if power.power_name in DEBUFFS:
				self.remove_power(power.power_name)
			if (power.power_name is "Strength" or power.power_name is "Dexterity" or power.power_name is "Focus") and power.amount < 0:
				self.remove_power(power.power_name)
			
				
	def decrement_duration_powers(self, character):
		turn_based_powers = ["Vulnerable", "Frail", "Weakened", "No Block", "No Draw"]
		for power in character.powers:
			if power.power_name in turn_based_powers:
				character.decrement_power(power.power_name)	
		
	def apply_end_of_turn_effects(self, monster): # (not for player use)
	
		for power in monster.powers:
			if power.power_name == "Shackles":
				monster.remove_power("Shackles")
			elif power.power_name == "Ritual":
				monster.add_power("Strength", power.amount)
			elif power.power_name == "Incantation":
				monster.add_power("Ritual", 3) # eventually adjust for ascensions
				monster.remove_power("Incantation")
			elif power.power_name == "Metallicize":
				monster.block += power.amount
			elif power.power_name == "Regen":
				monster.current_hp = min(monster.current_hp + power.amount, monster.max_hp)
				monster.decrement_power(power.power_name)

		self.decrement_duration_powers(monster)
				
				
	# DEPRECATED - we already get this information when we see the first state of combat
	# tracking it again here creates duplicates
	def apply_start_of_combat_effects(self):
	
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		
		for monster in available_monsters:
			if monster.monster_id == "Lagavulin" and monster.move_base_damage == 0:
				self.tracked_state["lagavulin_is_asleep"] = True
				
			# if "powers" in monster.intents:
				# for power in monster.intents["powers"]:
					# monster.add_power(power["name"], power["amount"])
					# self.debug_log.append("DEBUG: " + str(monster) + " has power " + str(power))
				

		# FIXME relics technically activate in order of acquisition (?)

		# if self.player.current_hp / self.player.max_hp < 0.50:
			# self.tracked_state["below_half_health"] = True
			# if self.has_relic("Red Skull") and self.tracked_state["below_half_health"]:
				# self.player.add_power("Strength", 3)
		# if self.has_relic("Thread and Needle"):
			# self.player.add_power("Plated Armor", 4)
		# if self.has_relic("Anchor"):
			# self.add_block(self.player, 10)
		# if self.has_relic("Fossilized Helix"):
			# self.player.add_power("Buffer", 1)
		# if self.has_relic("Vajra"):
			# self.player.add_power("Strength", 1)
		# if self.has_relic("Oddly Smooth Stone"):
			# self.player.add_power("Dexterity", 1)
		# if self.has_relic("Bronze Scales"):
			# self.player.add_power("Thorns", 3)
		# if self.has_relic("Mark of Pain"):
			# self.draw_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
			# self.draw_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
			# random.shuffle(draw_pile)
		# if self.has_relic("Philosopher's Stone"):
			# available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			# for monster in available_monsters:
				# monster.add_power("Strength", 1)
		# if self.has_relic("Bag of Preparation"):
			# random.shuffle(self.draw_pile)
			# self.hand += self.draw_pile.pop(0)
			# self.hand += self.draw_pile.pop(0)
		# if self.has_relic("Bag of Marbles"):
			# for monster in available_monsters:
				# monster.add_power("Vulnerable", 1)
		# if self.has_relic("Red Mask"):
			# for monster in available_monsters:
				# monster.add_power("Weakened", 1)
		# if self.has_relic("Snecko Eye"):
			# self.player.add_power("Confused", 1)
		# if self.has_relic("Gambling Chip"):
			# self.current_action = "GamblingChipAction"
			# self.screen = HandSelectScreen(self.hand, selected=[], num_cards=99, can_pick_zero=True)
			# self.screen_type = spirecomm.spire.screen.ScreenType.HAND_SELECT
			# self.screen_up = True
			
			
		# # TODO bottled cards are waiting on patch to CommMod
						
		# draw = self.draw_pile
		# for card in draw:
			# for effect in card.effects:
				# if effect["effect"] == "Innate":
					# self.hand += card
					# if self.has_power("Confused"):
						# card.cost = random.choice(range(4))
					# self.draw_pile.remove(card)
					# continue
			
	def check_effects_on_kill(self, target):
		# Note: Ritual Dagger and Feed tracked by the card effects
		
		if target.current_hp > 0:
			return
		
		self.debug_log.append("Killed " + str(target))
		
		if self.has_relic("Gremlin Horn"):
			self.draw_card()
			self.player.energy += 1
	
		if target.has_power("Spore Cloud"):
			self.player.add_power("Vulnerable", target.get_power_amount("Spore Cloud"))
			target.remove_power("Spore Cloud")
		if target.has_power("Thievery") and not self.has_relic("Ectoplasm"):
			self.tracked_state["incoming_gold"] += target.misc
		
			
			
		# TODO corpse explosion, that relic that shifts poison (specimen?)
		
		

				
	def check_intents(self):
	
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		
		for monster in available_monsters:
		
			if monster.monster_id == "GremlinTsundere" and len(available_monsters) < 2:
				monster.current_move = None # reset to attacking
									
			# Check if Lagavulin should still be sleeping
			if monster.monster_id == "Lagavulin":
				if monster.current_hp != monster.max_hp and self.tracked_state["lagavulin_is_asleep"]:
					# wake up
					selected_move = "Stunned"
					monster.add_power("Metallicize", -8)
					monster.remove_power("Asleep") # I think this doesn't actually exist in the code
					self.tracked_state["lagavulin_is_asleep"] = False
		
			if "half_health" in monster.intents and not monster.used_half_health_ability:
				monster.used_half_health_ability = True
				monster.current_move = monster.intents["half_health"]
			

	def apply_start_of_turn_effects(self, character):
	
		if character.has_power("Barricade"):
			pass
		elif character is self.player and self.has_relic("Calipers"):
			character.block = max(character.block - 15, 0)
		else:
			character.block = 0
	
		if character is self.player:
		
			self.player.block += self.tracked_state["next_turn_block"]
			self.tracked_state["next_turn_block"] = 0
			
			if self.has_relic("Brimstone"):
				self.player.add_power("Strength", 2)
				available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
				for monster in available_monsters:
					monster.add_power("Strength", 1)
			
			if self.has_relic("Pocketwatch") and self.tracked_state["cards_played_last_turn"] <= 3:
				self.draw_card(3)
		
			if self.has_relic("Mercury Hourglass"):
				available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
				for monster in available_monsters:
					self.apply_damage(3, None, monster)
		
			if self.has_relic("Runic Dodecahedron") and character.current_hp == character.max_hp:
				character.energy += 1
			if self.has_relic("Art of War") and self.tracked_state["attacks_played_last_turn"] == 0:
				character.energy += 1
				
			flower = self.get_relic("Happy Flower")
			if flower:
				flower.counter += 1
				if flower.counter >= 3:
					self.set_relic_counter("Happy Flower", 0)
					self.player.energy += 1
					
			burner = self.get_relic("Incense Burner")
			if burner:
				burner.counter += 1
				if burner.counter >= 6:
					self.set_relic_counter("Incense Burner", 0)
					self.player.add_power("Intangible", 1)
				
			if character.has_power("Brutality"):
				self.lose_hp(character, 1, from_card=True)
				self.draw_card()
				
			if self.has_relic("Warped Tongs"):
				selected_card = random.choice(self.hand)
				while selected_card.type == spirecomm.spire.card.CardType.CURSE or selected_card.type == spirecomm.spire.card.CardType.SPECIAL or (selected_card.upgrades > 0 and not selected_card.name.startswith("Searing Blow")):
					selected_card = random.choice(self.hand)
				selected_card.upgrade()
				
			if character.has_power("Mayhem"):
				for _ in range(character.get_power_amount("Mayhem")):
					card = self.draw_top_card()
					play_action = self.get_random_play(card)
					self.simulate_play(play_action)
					
				
	
	def apply_debuff(self, target, debuff, amount):
		if debuff == "Weakened" and target is self.player and self.has_relic("Ginger"):
			return
		if debuff == "Frail" and target is self.player and self.has_relic("Turnip"):
			return	
		if debuff in spirecomm.spire.power.DEBUFFS and target.has_power("Artifact"):
			target.decrement_power("Artifact")
		else:
			target.add_power(debuff, amount)
			if debuff == "Vulnerable" and self.has_relic("Champion Belt"):
				self.apply_debuff(target, "Weakened", 1)
			if target is not self.player and self.player.has_power("SadisticNature"):
				target.current_hp = max(target.current_hp - self.player.get_power_amount("SadisticNature"), 0)
			
	# helper function to calculate damage
	# note: attacker may be None (e.g. Burn)
	def calculate_real_damage(self, base_damage, attacker, target):
		damage = base_damage
		if attacker is not None:
			damage += attacker.get_power_amount("Strength")
			damage -= attacker.get_power_amount("Shackles")
			if attacker.has_power("Weakened"):
				if attacker is not self.player and self.has_relic("Paper Krane"):
					damage = damage - (0.40 * damage)
				else:
					damage = damage - (0.25 * damage)
		if target.has_power("Vulnerable"):
			if target is not self.player and self.has_relic("Paper Phrog"):
				damage = damage + (0.75 * damage)
			elif target is self.player and self.has_relic("Odd Mushroom"):
				damage = damage + (0.25 * damage)
			else:
				damage = damage + (0.50 * damage)
		return int(math.floor(damage))
		
	# Note attacker may be None, e.g. from Burn card
	def apply_damage(self, damage, attacker, target, from_attack=False, ignores_block=False):
		if target.has_power("Intangible") and not from_attack: # already adjusted for this in use_attack
			damage = 1
		if not ignores_block and target.block > 0:
			unblocked_damage = max(damage - target.block, 0)
			target.block = max(target.block - damage, 0)
			if target.block == 0 and target is not self.player and self.has_relic("Hand Drill"):
				self.apply_debuff(target, "Vulnerable", 2)
		else:
			unblocked_damage = damage
		capped_damage = min(target.current_hp, unblocked_damage)
		if unblocked_damage > 0 and unblocked_damage <= 5 and target is self.player and self.has_relic("Torii"):
			unblocked_damage = 1
		
		if unblocked_damage > 0:
			
			if target.has_power("Buffer"):
				target.decrement_power("Buffer")
			else:
				target.current_hp -= unblocked_damage
				self.check_effects_on_kill(target) # see if we killed them and if we do something about that
		
			# Guardian Mode Shift
			if target is not self.player and target.monster_id == "TheGuardian" and target.has_power("Mode Shift"):
				shift_amt = min(target.get_power_amount("Mode Shift", unblocked_damage))
				target.add_power("Mode Shift", -1 * shift_amt)
				if target.get_power_amount("Mode Shift") == 0: # Shift to Defensive
					target.current_move = "Defensive Mode"
		
		if unblocked_damage > 0 and target is self.player:
				
			if self.has_relic("Runic Cube"):
				self.draw_card()
		
			if self.has_relic("Self-Forming Clay"):
				self.tracked_state["next_turn_block"] += 3
		
			if target.current_hp / target.max_hp < 0.50:
				if self.has_relic("Red Skull") and not self.tracked_state["below_half_health"]:
					self.player.add_power("Strength", 3)
				self.tracked_state["below_half_health"] = True
		
			if self.tracked_state["times_lost_hp_this_combat"] == 0 and self.has_relic("Centennial Puzzle"):
				self.draw_card(3)
			self.tracked_state["times_lost_hp_this_combat"] += 1
			# TODO reduce the cost of blood for blood wherever it is in our deck
		
		
		self.check_intents()
		
		
		
	# applies Damage attack and returns unblocked damage
	# Note: this should only be used for ATTACK damage
	# Note attacker may be None, e.g. from Burn card
	def use_attack(self, base_damage, attacker, target):
		adjusted_damage = self.calculate_real_damage(base_damage, attacker, target)
		adjusted_damage = max(adjusted_damage, 0)
		pen_nib = self.get_relic("Pen Nib")
		if pen_nib is not None and pen_nib.counter >= 10:
			adjusted_damage *= 2 
			self.set_relic_counter("Pen Nib", 0)
		if attacker is not None:
			if attacker.has_power("Thievery"):
				gold_stolen = min(self.gold, attacker.get_power_amount("Thievery"))
				self.gold = self.gold - gold_stolen
				attacker.misc += gold_stolen
		if target.has_power("Angry"):
			target.add_power("Strength", target.get_power_amount("Angry"))
		if target.has_power("Intangible"):
			adjusted_damage = 1
		unblocked_damage = adjusted_damage - target.block
		unblocked_damage = max(unblocked_damage, 0)
		if unblocked_damage > 0:
			if unblocked_damage <= 5 and attacker is self.player and self.has_relic("The Boot"):
				unblocked_damage = 5
			if target is not self.player and target.block > 0 and self.has_relic("Hand Drill"):
				self.apply_debuff(target, "Vulnerable", 2)
			target.block = 0
			self.apply_damage(unblocked_damage, attacker, target, from_attack=True)
			if target.has_power("Plated Armor"):
				target.decrement_power("Plated Armor")
		else:
			target.block -= adjusted_damage
		if attacker is not None:
			if target.has_power("Flame Barrier"):
				self.use_attack(target.get_power_amount("Flame Barrier"), None, attacker)
			if target.has_power("Thorns"):
				self.use_attack(target.get_power_amount("Thorns"), None, attacker)
		if target.has_power("Curl Up"):
			curl = target.get_power_amount("Curl Up")
			self.add_block(target, curl)
			target.remove_power("Curl Up")
		return unblocked_damage
		
	def add_block(self, target, amount):
		if not target.has_power("NoBlock"):
			if amount == "Entrench":
				target.block *= 2
			else:
				target.block += amount
			if target.has_power("Juggernaut"):
				available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
				selected_monster = random.choice(available_monsters)
				self.use_attack(target.get_power_amount("Juggernaut"), None, selected_monster)
			
	# HP lost from cards / relics
	def lose_hp(self, target, amount, from_card=False):
		self.apply_damage(amount, None, target, ignores_block=True)
		if target is self.player and from_card and target.has_power("Rupture"):
			target.add_power("Strength", target.get_power_amount("Rupture"))
			
	def gain_gold(self, gold):
		if not self.has_relic("Ectoplasm"):
			self.gold += gold
		
	def gain_hp(self, target, amount): # assumes we're in combat
		if target is self.player:
			if self.has_relic("Magic Flower"):
				amount = math.ceil(amount * 1.5)
			if target.current_hp / target.max_hp > 0.50:
				if self.has_relic("Red Skull") and self.tracked_state["below_half_health"]:
					self.player.add_power("Strength", -3)
				self.tracked_state["below_half_health"] = False
				
		target.current_hp += amount
		
	def exhaust_card(self, card):
		if card.name != "Necronomicurse":
			if self.has_relic("Strange Spoon") and random.random() > 0.50:
				self.discard_pile.append(card)
				return
			self.exhaust_pile.append(card)
		if self.player.has_power("DarkEmbrace"):
			self.draw_card()
		if self.player.has_power("Feel No Pain"):
			self.add_block(self.player, self.player.get_power_amount("Feel No Pain"))
		if card.name.startswith("Sentinel"):
			for effect in card.effects:
				if effect["effect"] == "Sentinel":
					self.player.energy += effect["amount"]
		if self.has_relic("Charon's Ashes"):
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				monster.current_hp = max(monster.current_hp - 3, 0)
				
	def reshuffle_deck(self):		
		self.draw_pile = self.discard_pile
		random.shuffle(self.draw_pile)
		self.discard_pile = []
		self.tracked_state["just_reshuffled"] = True
				
		sundial = self.get_relic("Sundial")
		if sundial:
			sundial.counter += 1
			if sundial.counter >= 3:
				self.set_relic_counter("Sundial", 0)
				self.player.energy += 2
				
		if self.has_relic("The Abacus"):
			self.player.block += 6
			
	def draw_top_card(self):
		if len(self.draw_pile) == 0:
			self.reshuffle_deck()
		card = self.draw_pile.pop(0)
		return card
	
	def draw_card(self, draw=1):
		if self.player.has_power("No Draw"):
			return
		card = self.draw_top_card()
		if len(self.hand) >= 10:
			self.discard_pile.append(card)
		else:
			self.hand.append(card)
		if card.type == spirecomm.spire.card.CardType.STATUS and self.player.has_power("Evolve"):
			for _ in range(self.player.get_power_amount("Evolve")):
				self.draw_card()
		if self.player.has_power("Confused"):
			card.cost = random.choice(range(4))
		if card.type == spirecomm.spire.card.CardType.SKILL and self.player.has_power("Corruption"):
			card.cost = 0
		
		for effect in card.effects:
			if effect["effect"] == "Void":
				self.player.energy = max(self.player.energy - 1, 0)
		
		if draw > 1:
			self.draw_card(draw - 1)
			
	# used to simulate entropic brew
	def generate_random_potion(self, player_class=spirecomm.spire.character.PlayerClass.IRONCLAD):
		# fixme not sure if entropic brew can generate fruit juice
		possible_potions = [ 
		spirecomm.spire.potion.Potion("Ancient Potion", "Ancient Potion", True, True, False),
		spirecomm.spire.potion.Potion("Attack Potion", "Attack Potion", True, True, False),
		spirecomm.spire.potion.Potion("Block Potion", "Block Potion", True, True, False),
		spirecomm.spire.potion.Potion("Dexterity Potion", "Dexterity Potion", True, True, False),
		spirecomm.spire.potion.Potion("Essence of Steel", "Essence of Steel", True, True, False),
		spirecomm.spire.potion.Potion("Explosive Potion", "Explosive Potion", True, True, False),
		spirecomm.spire.potion.Potion("Fairy in a Bottle", "Fairy in a Bottle", False, True, False),
		spirecomm.spire.potion.Potion("Fear Potion", "Fear Potion", True, True, True),
		spirecomm.spire.potion.Potion("Fire Potion", "Fire Potion", True, True, True),
		spirecomm.spire.potion.Potion("Gambler's Brew", "Gambler's Brew", True, True, False),
		spirecomm.spire.potion.Potion("Liquid Bronze", "Liquid Bronze", True, True, False),
		spirecomm.spire.potion.Potion("Power Potion", "Power Potion", True, True, False),
		spirecomm.spire.potion.Potion("Regen Potion", "Regen Potion", True, True, False),
		spirecomm.spire.potion.Potion("Skill Potion", "Skill Potion", True, True, False),
		spirecomm.spire.potion.Potion("Smoke Bomb", "Smoke Bomb", True, True, False),
		spirecomm.spire.potion.Potion("Snecko Oil", "Snecko Oil", True, True, False),
		spirecomm.spire.potion.Potion("Speed Potion", "Speed Potion", True, True, False),
		spirecomm.spire.potion.Potion("Flex Potion", "Flex Potion", True, True, False),
		spirecomm.spire.potion.Potion("Strength Potion", "Strength Potion", True, True, False),
		spirecomm.spire.potion.Potion("Swift Potion", "Swift Potion", True, True, False),
		spirecomm.spire.potion.Potion("Weak Potion", "Weak Potion", True, True, True),
		]
	
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			possible_potions.append(spirecomm.spire.potion.Potion("Blood Potion", "Blood Potion", True, True, False))
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			possible_potions.append(spirecomm.spire.potion.Potion("Ghost In A Jar", "Ghost In A Jar", True, True, False))
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			possible_potions.append(spirecomm.spire.potion.Potion("Focus Potion", "Focus Potion", True, True, False))
		
		return random.choice(possible_potions)
		
	# quick function for setting a discover action
	def discover(self, player_class, card_type="ALL", rarity="ALL", action="DiscoverAction", skip_available=False):
		self.screen_up = True
		self.screen_type = spirecomm.spire.screen.ScreenType.CardRewardScreen
		self.current_action = action
		
		generated_cards = []
		for _ in range(3):
			generated_cards.append(self.generate_card(player_class, card_type, rarity))
		
		self.screen = spirecomm.spire.screen.CardRewardScreen(cards=generated_cards,can_bowl=False, can_skip=skip_available)
		self.choice_list = [card.get_choice_str() for card in generated_cards]
		return self
		
		
	def generate_card(self, player_class, card_type="ALL", rarity="ALL"):
		# card_id, name, card_type, rarity, upgrades=0, has_target=False, cost=0, misc=0, is_playable=False, exhausts=False
	
		return card

		
	def generate_random_colorless_card(self, rare_only=False):
		cards = []
		
		
	
		return cards
		
	def generate_random_attack_card(self, player_class, rare_only=False):
		cards = []
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			pass # TODO
	
		return cards
	
	def generate_random_skill_card(self, player_class, rare_only=False):
		cards = []
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			pass # TODO
	
		return cards
	
	def generate_random_power_card(self, player_class, rare_only=False):
		cards = []
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			pass # TODO
	
		return cards
		
	# parses damage in the form of amount or amount x hits, returns amounts and hits
	def read_damage(self, string):
		if 'x' in str(string):
			list = string.split('x')
			return list[0], list[1]
		else:
			return string, 1
		
	
	# Returns a new state
	def simulate_end_turn(self, action):
		
		self.check_intents()
		
		# TODO consider retaining cards (well-laid plans) or runic pyramid
		
		# end player's turn
		self.apply_end_of_player_turn_effects()
		
		# MONSTER TURN / MONSTERS ATTACK
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for monster in available_monsters:
			if monster is None:
				self.debug_log.append("WARN: Monster is None")
				continue
							
			self.apply_start_of_turn_effects(monster)
				
			if monster.intents != {}: # we have correctly loaded intents JSON
			
				if monster.current_move is None:		
					if self.combat_round == 1 and "startswith" in monster.intents:
						monster.current_move = monster.intents["startswith"]
						if monster.monster_id == "Sentry" and monster.monster_index == 1:
							# The second Sentry starts with an attack rather than debuff
							monster.current_move = "Beam"
						self.debug_log.append("Known initial intent for " + str(monster) + " is " + str(monster.current_move))

					elif self.tracked_state["is_simulation"]: # generate random move
						monster.current_move = self.choose_move(monster)
						self.debug_log.append("Simulated intent for " + str(monster) + " is " + str(monster.current_move))
					else: # figure out move from what we know about it
					
						timeout = 100 # assume trying 100 times will be enough unless there's a problem
						while timeout > 0:
							# continue to randomly sample moves until we find one that fits
							move = self.choose_move(monster)
							details = monster.intents["moveset"][move]
							intent_str = details["intent_type"]
							if spirecomm.spire.character.Intent[intent_str] == monster.intent or self.has_relic("Runic Dome"):
								# if it's an attack, check the number of hits also
								if monster.intent.is_attack():
									hits = 0
									effects = details["effects"]
									for effect in effects:
										if effect["name"] == "Damage":
											amt, h = self.read_damage(effect["amount"])
											hits += h
									if hits == monster.move_hits:
										monster.current_move = move
										self.debug_log.append("DEBUG: counted hits " + str(hits) + " is " + str(hits)) # TODO remove
									else: 
										self.debug_log.append("DEBUG: counted hits " + str(hits) + " is not " + str(hits)) # TODO remove
								else:
									monster.current_move = move
									
							if monster.current_move is not None:
								if self.has_relic("Runic Dome"):
									self.debug_log.append("Guessed intent for " + str(monster) + " is " + str(monster.current_move))
								else:
									self.debug_log.append("Recognized intent for " + str(monster) + " is " + str(monster.current_move))
								break
							timeout -= 1
							
								
				if monster.current_move is None:
					self.debug_log.append("ERROR: Could not determine " + monster.name + "\'s intent of " + str(monster.intent))
				else:
					if monster.intent == spirecomm.spire.character.Intent.ATTACK and (monster.monster_id == "FuzzyLouseNormal" or monster.monster_id == "FuzzyLouseDefensive"):
						# louses have a variable base attack
						effs = monster.intents["moveset"][monster.current_move]["effects"]
						json_base = None
						for eff in effs:
							if eff["name"] == "Damage":
								json_base = eff["amount"]
						if not json_base:
							raise Exception("Malformed Louse JSON when calculating base damage for " + str(monster.current_move))
						attack_adjustment = monster.move_base_damage - json_base
						monster.misc = attack_adjustment
						self.debug_log.append("Adjusted damage for louse: " + str(monster.misc))
								
					# Finally, apply the intended move
					effects = monster.intents["moveset"][monster.current_move]["effects"]
					for effect in effects:
						
						if effect["name"] == "Damage":
							amount, hits = self.read_damage(effect["amount"])
							base_damage = amount
							if monster.monster_id == "FuzzyLouseNormal" or monster.monster_id == "FuzzyLouseDefensive":
								base_damage += monster.misc # adjustment because louses are variable
								self.debug_log.append("Adjusted damage for louse: " + str(monster.misc))
							for _ in range(hits):
								unblocked_damage = self.use_attack(base_damage, monster, self.player)
								self.debug_log.append("Taking " + str(unblocked_damage) + " damage from " + str(monster))
								
						elif effect["name"] == "Block":
							self.add_block(monster, effect["amount"])
							
						elif effect["name"] == "BlockOtherRandom":
							selected_ally = None
							while selected_ally is None or selected_ally is monster:
								selected_ally = random.choice(available_monsters)
							self.add_block(selected_ally, effect["amount"])
							
						elif effect["name"] in BUFFS:
							monster.add_power(effect["name"], effect["amount"])
							
						elif effect["name"] in DEBUFFS:
							self.apply_debuff(self.player, effect["name"], effect["amount"])
														
						elif effect["name"] == "AddSlimedToDiscard":
							for __ in range(effect["amount"]):
								slimed = spirecomm.spire.card.Card("Slimed", "Slimed", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL)
								self.discard_pile.append(slimed)
								
						elif effect["name"] == "AddDazedToDiscard":
							for __ in range(effect["amount"]):
								slimed = spirecomm.spire.card.Card("Dazed", "Dazed", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL)
								self.discard_pile.append(slimed)
								
						elif effect["name"] == "GainBurnToDiscard" or effect["name"] == "AddBurnToDiscard":
							for _ in range(effect["amount"]):
								self.discard_pile.append(spirecomm.spire.card.Card("Burn", "Burn", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
							1	
						elif effect["name"] == "GainBurn+ToDiscard" or effect["name"] == "AddBurn+ToDiscard":
							for _ in range(effect["amount"]):
								self.discard_pile.append(spirecomm.spire.card.Card("Burn+", "Burn+", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL, upgrades=1))
								
						elif effect["name"] == "GainBurnToDeck" or effect["name"] == "AddBurnToDeck":
							for _ in range(effect["amount"]):
								self.draw_pile.append(spirecomm.spire.card.Card("Burn", "Burn", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))	
						
						elif effect["name"] == "Sleep":
							pass # take one (1) snoozle
							
						elif effect["name"] == "Charge":
							pass # i'ma chargin' mah fireball!
							
						elif effect["name"] == "Split":
							for new_monster in effect["amount"]:
								m = spirecomm.spire.character.Monster(new_monster, new_monster, monster.current_hp,  monster.current_hp, 0, None, False, False)
								self.monsters.append(m)
								self.monsters.remove(monster)
						
						elif effect["name"] == "Escape":
							monster.is_gone = True
							
						elif effect["name"] == "Offensive Mode":
							monster.add_power("Mode Shift", 30 + monster.misc) # TODO account for ascension_level
							monster.misc += 10
						
						elif effect["name"] not in PASSIVE_EFFECTS:
							self.debug_log.append("WARN: Unknown effect " + effect["name"])
						
					# increment count of moves in a row
					if str(monster) in self.tracked_state["monsters_last_attacks"] and self.tracked_state["monsters_last_attacks"][str(monster)][0] == monster.current_move:
						self.tracked_state["monsters_last_attacks"][str(monster)][1] += 1
					else:
						self.tracked_state["monsters_last_attacks"][str(monster)] = [monster.current_move, 1]

			
			if monster.intents == {} or monster.current_move is None:
				self.debug_log.append("WARN: unable to get intent for " + str(monster))
				# default behaviour: just assume the same move as the first turn of simulation
				if monster.intent.is_attack():
					if monster.move_adjusted_damage is not None:
						# are weak and vulnerable accounted for in default logic?
						for _ in range(monster.move_hits):
							unblocked_damage = self.use_attack(monster.move_base_damage, monster, self.player)
							self.debug_log.append("Taking " + str(unblocked_damage) + " damage from " + str(monster))
							
			monster.current_move = None # now that we used the move, clear it
							
		for monster in available_monsters:
			self.apply_end_of_turn_effects(monster)

		
		self.player.energy += 3
		for relic in ["Coffee Dripper", "Mark of Pain", "Sozu", "Ectoplasm", "Cursed Key", "Runic Dome", "Philosopher's Stone", "Fusion Hammer"]:
			if self.has_relic(relic):
				self.player.energy += 1
		if self.player.has_power("Berserk"):
			self.player.energy += 1
			
		self.combat_round += 1
		self.apply_start_of_turn_effects(self.player)

		# Draw new hand - TODO consider relic modifiers and known information
		hand_size = 5
		if self.has_relic("Snecko Eye"):
			hand_size += 2
		while len(self.hand) < hand_size:
			self.draw_card()
			
		if self.debug_file and self.debug_log != []:
			with open(self.debug_file, 'a+') as d:
				d.write('\n')
				d.write('\n'.join(self.debug_log))
				d.write('\n')
				#d.write("\nNew State:\n")
				#d.write(str(self))
			
		self.tracked_state["is_simulation"] = True
		
		return self
				
		
	def simulate_discovery(self, action):
		self.choice_list = []
		self.current_action = None
		
		# TODO actually discover the card
	
		return self
		
	def simulate_exhaust(self, action):
		self.hand.remove(action.card)
		self.exhaust_card(action.card)
		return self
		
	def simulate_headbutt(self, action):
		card = action.cards[0]
		self.discard_pile.remove(card)
		self.draw_pile.insert(0, card)
		return self
		
	def simulate_hand_to_topdeck(self, action):
		self.hand.remove(action.card)
		self.draw_pile.insert(0, action.card)
		return self
		
	def simulate_upgrade(self, action):
		action.card.upgrade()
		return self

	def simulate_exhume(self, action):
		card = action.cards[0]
		self.exhaust_pile.remove(card)
		self.hand.append(card)
		return self
		
	def simulate_dual_wield(self, action):
		# TODO how to know whether it's dualwield+?
		
	
		return self
		
	def simulate_forethought(self, action):
		# TODO
		
	
		return self
		
		
	# Returns a new state
	def simulate_potion(self, action):
	
		self.potions.remove(action.potion) # fixme? might need to match on name rather than ID
		self.potions.append(spirecomm.spire.potion.Potion("Potion Slot", "Potion Slot", False, False, False))
		
		if action.potion.name == "Ancient Potion":
			self.player.add_power("Artifact", 1)
		
		elif action.potion.name == "Attack Potion":
			# TODO
			pass
		
		elif action.potion.name == "Block Potion":
			self.add_block(self.player, 12)
		
		elif action.potion.name == "Blood Potion":
			hp_gained = int(math.ceil(self.player.max_hp * 0.25))
			new_hp = min(self.player.max_hp, self.player.current_hp + hp_gained)
			self.player.current_hp = new_hp
		
		elif action.potion.name == "Dexterity Potion":
			self.player.add_power("Dexterity", 2)
		
		elif action.potion.name == "Energy Potion":
			self.player.energy += 2
		
		elif action.potion.name == "Entropic Brew":
			for i in range(len(self.potions)):
				if self.potions[i].potion_id == "Potion Slot":
					self.potions[i] = self.generate_random_potion()
		
		elif action.potion.name == "Essence of Steel":
			self.player.add_power("Plated Armor", 4)
		
		elif action.potion.name == "Explosive Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				self.apply_damage(10, None, monster)
		
		# TODO Fairy in a Bottle is not usable but should be considered in game state
		
		elif action.potion.name == "Fear Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				if monster == action.target_monster:
					monster.add_power("Vulnerable", 3)
		
		elif action.potion.name == "Fire Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				if monster == action.target_monster:
					self.apply_damage(20, None, monster)
		
		elif action.potion.name == "Focus Potion":
			self.player.add_power("Focus", 2)
		
		elif action.potion.name == "Fruit Juice":
			self.player.max_hp += 5
			self.player.current_hp += 5
		
		elif action.potion.name == "Gambler's Brew":
			# TODO
			pass
			
		elif action.potion.name == "Ghost In A Jar":
			self.player.add_power("Intangible", 1)
		
		elif action.potion.name == "Liquid Bronze":
			self.player.add_power("Thorns", 3)
		
		elif action.potion.name == "Poison Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				if monster == action.target_monster:
					monster.add_power("Poison", 6)
		
		elif action.potion.name == "Power Potion":
			# TODO
			pass
			
		elif action.potion.name == "Regen Potion":
			self.player.add_power("Regen", 5)
		
		elif action.potion.name == "Skill Potion":
			# TODO
			pass
		
		elif action.potion.name == "Smoke Bomb":
			if self.blackboard.game.room_type != "MonsterRoomBoss":
				self.in_combat = False
		
		elif action.potion.name == "Snecko Oil":
			self.player.add_power("Confused")
			self.draw_card(3)
		
		elif action.potion.name == "Speed Potion":
			self.player.add_power("Dexterity", 5)
			self.player.add_power("Dexterity Down", 5)
		
		elif action.potion.name == "Flex Potion":
			self.player.add_power("Strength", 5)
			self.player.add_power("Strength Down", 5)
		
		elif action.potion.name == "Strength Potion":
			self.player.add_power("Strength", 2)
		
		elif action.potion.name == "Swift Potion":
			self.draw_card(3)
		
		elif action.potion.name == "Weak Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				if monster == action.target_monster:
					monster.add_power("Weakened", 3)
		
		else:
			self.debug_log.append("ERROR: No handler for potion: " + str(action.potion))
			
			
		if self.debug_file and self.debug_log != []:
			with open(self.debug_file, 'a+') as d:
				d.write('\n')
				d.write('\n'.join(self.debug_log))
				d.write('\n')
				#d.write("\nNew State:\n")
				#d.write(str(self))
		
		self.tracked_state["is_simulation"] = True
		
		return self
		
	
	def get_random_play(self, card):
		# randomly play the card
		play_action = PlayCardAction(card)
		if card.has_target:
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			selected_monster = random.choice(available_monsters)
			play_action.target_index = selected_monster.monster_index
			play_action.target_monster = selected_monster
		return play_action
		
		
		
	# Returns a new state
	def simulate_play(self, action, free_play=False, from_deck=False):
	
		if not action.card.loadedFromJSON:
			raise Exception("Card not loaded from JSON: " + str(action.card.name))
			
		if action.card.type != spirecomm.spire.card.CardType.CURSE:
			# Velvet Choker does count copies of free_play cards, but allows them to go off past 6
			self.increment_relic("Velvet Choker") # doesn't count Blue Candle
			
		self.tracked_state["cards_played_this_turn"] += 1
		
		# Fix for IDs not matching
		found = False # test
		possible_cards = self.hand
		if from_deck:
			possible_cards = self.draw_pile
		for c in possible_cards:
			if action.card == c:
				action.card = c
				found = True 
		if not found:
			raise Exception("Could not find action card " + action.card.get_id_str() + " in hand " + str([card.get_id_str() for card in possible_cards]))
		
		if not free_play:
			# move card to discard
			self.player.energy -= action.card.cost
			self.hand.remove(action.card)
			if action.card.type != spirecomm.spire.card.CardType.POWER: # powers just get removed from play
				self.discard_pile.append(action.card)
		
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]

			
		X_cost = -1
		if "X" in [effect["effect"] for effect in action.card.effects]:
			X_cost = self.player.energy
			if self.has_relic("Chemical X"):
				X_cost += 2
			self.player.energy = 0
			
			
		effect_targets = []
		for effect in action.card.effects:
			
			# Pick target(s)
			if effect["target"] == "self":
				effect_targets = [self.player]
			elif effect["target"] == "one":
				for monster in available_monsters:
					if action.target_monster is None:
						raise Exception("Action expects a target; check " + str(action.card.get_clean_name()) + ".json for potential error.")
					if action.target_monster == monster:
						effect_targets = [monster]
						break
			elif effect["target"] == "all":
				effect_targets = available_monsters
			elif effect["target"] == "random":
				effect_targets = [random.choice(available_monsters)]
				
			
			# Do effect
			for target in effect_targets:
			
				effects_that_can_target_unavailable = ["Feed", "RitualDagger", "Greed"]
			
				available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
				if target is not self.player and target not in available_monsters and effect["effect"] not in effects_that_can_target_unavailable:
					continue # we probably killed it, just ignore remaining effects
			
				if effect["effect"] == "Block":
					real_amount = effect["amount"]
					real_amount += target.get_power_amount("Dexterity")
					if target.has_power("Frail"):
						real_amount = int(math.floor(real_amount - (0.25 * real_amount)))
					self.add_block(target, real_amount)
					
				elif effect["effect"] == "Entrench":
					self.add_block(target, "Entrench")
					
				elif effect["effect"] == "Damage":
					base_damage = effect["amount"]
					if action.card.name.startswith("Searing Blow"):
						upgrades = action.card.upgrades
						base_damage = math.ceil((upgrades * ((upgrades + 7) / 2)) + 12)
					if action.card.name == "Ritual Dagger" or action.card.name == "Rampage":
						base_damage += action.card.misc
					
					for effect in action.card.effects:
						if effect["effect"] == "Strike Damage":
							cards = self.draw_pile + self.discard_pile + self.hand
							for card in cards:
								if "Strike" in card.name:
									base_damage += effect["amount"]
						if effect["effect"] == "Bonus Strength Damage":
							base_damage += effect["amount"] * self.player.get_power_amount("Strength")
					
					self.use_attack(base_damage, self.player, target)
					
				elif effect["effect"] == "XDamage":
					if X_cost < 0:
						raise Exception("Non X-cost card using an X-cost ability")
					for _ in range(X_cost):
						base_damage = effect["amount"]
						self.use_attack(base_damage, self.player, target)
					
				elif effect["effect"] == "Corruption":
					cards = self.draw_pile + self.discard_pile + self.hand
					for card in cards:
						if card.type == spirecomm.spire.card.CardType.SKILL:
							card.cost = 0
					self.player.add_power(effect["effect"], effect["amount"])
					
				elif effect["effect"] == "Armaments":
					upgradable_cards = self.get_upgradable_cards(self.hand)
					if len(upgradable_cards) == 0:
						pass
					elif len(upgradable_cards) == 1:
						action = CardSelectAction(cards=upgradable_cards)
						self.simulate_upgrade(action)
					else:
						self.screen = spirecomm.spire.screen.HandSelectScreen(cards=upgradable_cards, selected=[], num_cards=1, can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.HAND_SELECT
						self.current_action = "ArmamentsAction"
						self.choice_list = [card.get_choice_str() for card in upgradable_cards]
					
				elif effect["effect"] == "Armaments+":
					for card in self.hand:
						card.upgrade()
						
				elif effect["effect"] == "HandToDeck":
					if len(self.hand) == 0:
						pass
					elif len(self.hand) == 1:
						action = CardSelectAction(cards=self.hand)
						self.simulate_hand_to_topdeck(action)
					else:
						self.screen = spirecomm.spire.screen.HandSelectScreen(cards=self.hand, selected=[], num_cards=effect["amount"], can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.HAND_SELECT
						self.current_action = "PutOnDeckAction"
						self.choice_list = [card.get_choice_str() for card in self.hand]
						
				elif effect["effect"] == "Headbutt":
					if len(self.discard_pile) == 0:
						pass
					elif len(self.discard_pile) == 1:
						action = CardSelectAction(cards=self.discard_pile)
						self.simulate_headbutt(action)
					else:
						self.screen = spirecomm.spire.screen.GridSelectScreen(cards=self.discard_pile, selected_cards=[], num_cards=1, can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.GRID_SELECT
						self.current_action = "PutOnDeckAction"
						self.choice_list = [card.get_choice_str() for card in self.discard_pile]
						
				elif effect["effect"] == "Exhume":
					if len(self.exhaust_pile) == 0:
						pass
					elif len(self.exhaust_pile) == 1:
						action = CardSelectAction(cards=self.exhaust_pile)
						self.simulate_exhume(action)
					else:
						self.screen = spirecomm.spire.screen.GridSelectScreen(cards=self.hand, selected_cards=[], num_cards=1, can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.GRID_SELECT
						self.current_action = "ExhumeAction"
					
					
				elif effect["effect"] in BUFFS:
					self.player.add_power(effect["effect"], effect["amount"])
						
				elif effect["effect"] in DEBUFFS:
					self.apply_debuff(target, effect["effect"], effect["amount"])
					
				elif effect["effect"] == "Block as Damage":
					base_damage = self.player.block
					self.use_attack(base_damage, self.player, target)
					
				elif effect["effect"] == "MindBlast":
					base_damage = len(self.draw_pile)
					self.use_attack(base_damage, self.player, target)
					
				elif effect["effect"] ==  "Violence":
					available_attacks = [c for c in self.draw_pile if c.type == spirecomm.spire.card.CardType.ATTACK]
					for _ in range(min(effect["amount"], len(available_attacks))):
						selected_card = random.choice(available_attacks)
						self.hand.append(selected_card)
						self.draw_pile.remove(selected_card)
						available_attacks.remove(selected_card)
						
				elif effect["effect"] == "Heal":
					self.gain_hp(target, effect["amount"])
					
				elif effect["effect"] == "Energy":
					self.player.energy += effect["amount"]
					
				elif effect["effect"] == "Dropkick":
					if target.has_power("Vulnerable"):
						self.player.energy += 1 
						self.draw_card()
					
				elif effect["effect"] == "Anger":
					new_card = copy.deepcopy(action.card)
					new_card.uuid = ""
					self.discard_pile.append(new_card)
					
				elif effect["effect"] == "Rampage":
					action.card.misc += effect["amount"]				
					
				
				elif effect["effect"] == "SpotWeakness":
					if target.intent.is_attack():
						self.player.add_power("Strength", effect["amount"])
						
				elif effect["effect"] == "SecondWind":
					hand = self.hand
					for card in hand:
						if card.type != spirecomm.spire.card.CardType.ATTACK:
							self.exhaust_card(card)
							self.add_block(self.player, effect["amount"])
						
						
				elif effect["effect"] == "ExhaustAllNonAttacks":
					hand = self.hand
					for card in hand:
						if card.type != spirecomm.spire.card.CardType.ATTACK:
							self.exhaust_card(card)
					
				elif effect["effect"] == "FiendFire":
					hand = self.hand
					for card in hand:
						self.hand.remove(card)
						self.exhaust_card(card)
						self.use_attack(effect["amount"], self.player, target)
						
				elif effect["effect"] == "GainBurnToDiscard":
					for _ in range(effect["amount"]):
						self.discard_pile.append(spirecomm.spire.card.Card("Burn", "Burn", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
						
				elif effect["effect"] == "DazedToDraw":
					for _ in range(effect["amount"]):
						self.draw_pile.append(spirecomm.spire.card.Card("Dazed", "Dazed", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
						
				elif effect["effect"] == "WoundToHand":
					for _ in range(effect["amount"]):
						if len(self.hand) >= 10:
							self.discard_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
						else:
							self.hand.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
							
				elif effect["effect"] == "WoundToDeck":
					for _ in range(effect["amount"]):
						self.draw_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
					
				elif effect["effect"] == "Reaper":
					base_damage = effect["amount"]
					unblocked_damage = self.use_attack(base_damage, self.player, target)
					self.gain_hp(unblocked_damage)
					
				elif effect["effect"] == "LimitBreak":
					target.add_power("Strength", target.get_power_amount("Strength"))
					
				elif effect["effect"] == "Feed":
					if monster.current_hp <= 0 and not monster.half_dead and not monster.has_power("Minion"):
						self.player.max_hp += effect["amount"]
						self.player.current_hp += effect["amount"]
						
				elif effect["effect"] == "Impatience":
					no_attacks = True
					for card in self.hand:
						if card.type == spirecomm.spire.card.CardType.ATTACK:
							no_attacks = False
							break
					if no_attacks:
						self.draw_card(2)
						
				elif effect["effect"] == "Greed":
					if monster.current_hp <= 0 and not monster.half_dead and not monster.has_power("Minion"):
						self.player.gain_gold(20)
					
				elif effect["effect"] == "RitualDagger":
					if monster.current_hp <= 0 and not monster.half_dead:
						action.card.misc += effect["amount"]
						
				elif effect["effect"] == "Havoc":
					havoc_card = self.draw_pile.pop(0)
					play_action = self.get_random_play(havoc_card)
					self.simulate_play(play_action, from_deck=True)
					self.discard_pile.remove(havoc_card)
					self.exhaust_card(havoc_card)
					
				elif effect["effect"] == "Apotheosis":
					cards = self.draw_pile + self.discard_pile + self.hand
					for card in cards:
						if card is not action.card:
							card.upgrade()
							
				elif effect["effect"] == "Lose HP":
					self.lose_hp(self.player, effect["amount"], from_card=True)
					
				elif effect["effect"] == "DiscardToDraw":
					self.reshuffle_deck()
					
				elif effect["effect"] == "Exhaust":
					self.discard_pile.remove(action.card)
					self.exhaust_card(action.card)
				elif effect["effect"] == "ExhaustRandom":
					exhausted_card = random.choice(self.hand)
					self.hand.remove(exhausted_card)
					self.exhaust_card(exhausted_card)
					
				elif effect["effect"] == "ExhaustSelect":
					if len(self.hand) == 0:
						pass
					elif len(self.hand) == 1:
						action = CardSelectAction(cards=self.hand)
						self.simulate_exhaust(action)
					else:
						self.screen = spirecomm.spire.screen.HandSelectScreen(cards=self.hand, selected=[], num_cards=effect["amount"], can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.HAND_SELECT
						self.current_action = "ExhaustAction"
					
				elif effect["effect"] == "Draw":
					self.draw_card(draw=effect["amount"])
						
				elif effect["effect"] == "Madness":
					selected_card = random.choice([c for c in self.hand if c.cost > 0])
					selected_card.cost = 0
					
				elif effect["effect"] not in PASSIVE_EFFECTS:
					self.debug_log.append("WARN: Unknown effect " + effect["effect"])
					
					
					
					
		if action.card.type == spirecomm.spire.card.CardType.ATTACK:
	
			self.tracked_state["attacks_played_this_turn"] += 1
			if self.tracked_state["attacks_played_this_turn"] == 1 and self.tracked_state["skills_played_this_turn"] > 0 and self.tracked_state["powers_played_this_turn"] > 0 and self.has_relic("Orange Pellets"):
				self.remove_all_debuffs()
		
			if self.player.has_power("Rage"):
				self.add_block(self.player, self.player.get_power_amount("Rage"))
		
			fan = self.get_relic("Ornamental Fan")
			if fan:
				fan.counter += 1
				if fan.counter >= 3:
					self.set_relic_counter("Ornamental Fan", 0)
					self.add_block(self.player, 4)
					
			kunai = self.get_relic("Kunai")
			if kunai:
				kunai.counter += 1
				if kunai.counter >= 3:
					self.set_relic_counter("Kunai", 0)
					self.player.add_power("Dexterity", 1)
			
			shuriken = self.get_relic("Shuriken")
			if shuriken:
				shuriken.counter += 1
				if shuriken.counter >= 3:
					self.set_relic_counter("Shuriken", 0)
					self.player.add_power("Strength", 1)
			
			self.increment_relic("Pen Nib")
			
			nunchaku = self.get_relic("Nunchaku")
			if nunchaku:
				nunchaku.counter += 1
				if nunchaku.counter >= 10:
					self.set_relic_counter("Nunchaku", 0)
					self.player.energy += 1
			
			if self.player.has_power("DoubleTap"):
				self.player.decrement_power("DoubleTap")
				self.simulate_play(action, free_play=True)
			
		if action.card.cost >= 2 and self.has_relic("Necronomicon") and not self.tracked_state["necronomicon_triggered"]:
			self.tracked_state["necronomicon_triggered"] = True
			self.simulate_play(action, free_play=True)
				
				
				
		if action.card.type == spirecomm.spire.card.CardType.SKILL:
		
			self.tracked_state["skills_played_this_turn"] += 1
			if self.tracked_state["skills_played_this_turn"] == 1 and self.tracked_state["attacks_played_this_turn"] > 0 and self.tracked_state["powers_played_this_turn"] > 0 and self.has_relic("Orange Pellets"):
				self.remove_all_debuffs()
	
			letter = self.get_relic("Letter Opener")
			if letter:
				letter.counter += 1
				if letter.counter >= 3:
					self.set_relic_counter("Letter Opener", 0)
					for monster in available_monsters:
						self.apply_damage(5, None, monster)
		
			for monster in available_monsters:
				if monster.has_power("Enrage"):
					monster.add_power("Strength", monster.get_power_amount("Enrage"))

			if self.player.has_power("Corruption"):
				self.discard_pile.remove(exhausted_card) # FIXME if might not have gone to discard
				self.exhaust_card(action.card)
			
		if action.card.type == spirecomm.spire.card.CardType.POWER:
		
			self.tracked_state["powers_played_this_turn"] += 1
			if self.tracked_state["powers_played_this_turn"] == 1 and self.tracked_state["attacks_played_this_turn"] > 0 and self.tracked_state["skills_played_this_turn"] > 0 and self.has_relic("Orange Pellets"):
				self.remove_all_debuffs()
		
			if self.has_relic("Mummified Hand"):
				selected_card = random.choice(self.hand)
				while selected_card.cost == 0: #or selected_card.type == spirecomm.spire.card.CardType.CURSE (should be covered by cost)
					selected_card = random.choice(self.hand)
				selected_card.cost = 0
			
			
		for card in self.hand:
			for effect in card.effects:
				if effect["effect"] == "Pain":
					self.lose_hp(self.player, 1, from_card=True)
						
		if self.hand == [] and self.has_relic("Unceasing Top"):
			self.draw_card()
						
		
		self.check_intents()
					
			
		if self.debug_file and self.debug_log != []:
			with open(self.debug_file, 'a+') as d:
				d.write('\n')
				d.write('\n'.join(self.debug_log))
				d.write('\n')
				#d.write("\nNew State:\n")
				#d.write(str(self))
			
		self.tracked_state["is_simulation"] = True
			
		return self