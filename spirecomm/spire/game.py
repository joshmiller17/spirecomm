from enum import Enum
import copy
import random
import math


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

BUFFS = ["Ritual", "Strength", "Dexterity", "Incantation", "Enrage", "Metallicize", "SadisticNature", "Juggernaut", "DoubleTap", "DemonForm", "DarkEmbrace", "Brutality", "Berserk", "Rage", "Feel No Pain", "Flame Barrier", "Corruption", "Combust"]
DEBUFFS = ["Frail", "Vulnerable", "Weakened", "Entangled", "Shackles", "NoBlock", "No Draw"]

class RoomPhase(Enum):
	COMBAT = 1,
	EVENT = 2,
	COMPLETE = 3,
	INCOMPLETE = 4


class Game:

	def __init__(self):

		# General state

		self.current_action = None # "The class name of the action in the action manager queue, if not empty"
		self.act_boss = None
		# For HP, see game.player
		self.floor = 0
		self.act = 0
		self.gold = 0
		self.seed = 0
		self.character = None
		self.ascension_level = None
		self.relics = []
		self.deck = []
		self.potions = []
		self.map = []

		# Combat state

		self.in_combat = False
		self.combat_round = 1
		self.player = None
		self.monsters = []
		self.draw_pile = []
		self.discard_pile = []
		self.exhaust_pile = []
		self.hand = []

		# Current Screen

		self.screen = None
		self.screen_up = False
		self.screen_type = None
		self.room_phase = None
		self.room_type = None
		self.choice_list = []
		self.choice_available = False

		# Available Commands

		self.end_available = False
		self.potion_available = False
		self.play_available = False
		self.proceed_available = False
		self.cancel_available = False
		
		# Added state info
		self.debug_file = "game.log"
		self.state_id = -1
		self.debug_log = []
		self.original_state = None # For MCTS simulations; FIXME might be a huge memory storage for in-depth simulations? Consider only storing values important for reward func
		
		
		# Tracked state info - TODO this block needs to be stored more permanently
		self.tracked_state = {
		"visited_shop" : False,
		"previous_floor" : 0,  # used to recognize floor changes, i.e. when floor != previous_floor
		"possible_actions": None,
		"monsters_last_attacks" : {}, # monster : [move name, times in a row]
		"is_simulation" : False,
		"known_top_cards" : [], # cards which we know we will be drawing first go here
		"just_reshuffled" : False,
		"incoming_gold" : 0, # gold we get back from thieves if we kill them
		"attacks_played_this_turn" : 0,
		"attacks_played_last_turn" : 0,
		"cards_played_this_turn": 0,
		"cards_played_last_turn" : 0,
		"times_lost_hp_this_combat" : 0,
		"next_turn_block" : 0,
		"below_half_health" : False,
		"necronomicon_triggered" : False,
		"skills_played_this_turn" : 0,
		"powers_played_this_turn" : 0
		}
	
	# for some reason, pausing the game invalidates the state
	def is_valid(self):
		return self.end_available or self.potion_available or self.play_available or self.proceed_available or self.cancel_available
		
	# do any internal state updates we need to do if we change floors
	def on_floor_change(self):
		self.combat_round = 1
		self.original_state = None
		
		self.tracked_state["visited_shop"] = False
		self.tracked_state["is_simulation"] = False
		self.tracked_state["just_reshuffled"] = False
		self.tracked_state["incoming_gold"] = 0
		self.tracked_state["attacks_played_this_turn"] = 0
		self.tracked_state["attacks_played_last_turn"] = 0
		self.tracked_state["cards_played_this_turn"] = 0
		self.tracked_state["cards_played_last_turn"] = 0
		self.tracked_state["times_lost_hp_this_combat"] = 0
		self.tracked_state["next_turn_block"] = 0
		self.tracked_state["necronomicon_triggered"] = False
		self.tracked_state["skills_played_this_turn"] = 0
		self.tracked_state["powers_played_this_turn"] = 0

		
	# returns relic or None
	def get_relic(self, name):
		for relic in self.relics:
			if relic.name == name:
				return relic
		return None
		
	def increment_relic(self, name):
		for relic in self.relics:
			if relic.name == name:
				relic.counter += 1
	
	def set_relic_counter(self, name, amount):
		for relic in self.relics:
			if relic.name == name:
				relic.counter = amount
		
		
	def has_relic(self, name):
		return self.get_relic(name) is not None
	
	def __str__(self):
		string = "\n\n<---- Game State " + str(self.state_id) + " ----"
		string += "\nScreen: " + str(self.screen) + " (" + str(self.screen_type) + ") " + ("[UP]" if self.screen_up else "")
		#string += "\nRoom: " + str(self.room_type)
		string += "\nCurrent action: " + str(self.current_action)
		string += "\nSimulation?: " + str(self.tracked_state["is_simulation"])
		if self.in_combat:
			string += "\nHP: " + str(self.player.current_hp) + "/" + str(self.player.max_hp)
			string += "\nBlock: " + str(self.player.block)
			string += "\nRound: " + str(self.combat_round)
			string += "\nEnergy: " + str(self.player.energy)
			string += "\nMonsters:\n    "
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			if self.tracked_state["is_simulation"]:
				# FIXME when this gets called, we haven't simulated the attack yet, and we also don't calculate adjusted dmg
				string += "\n    ".join([str(monster.monster_id) + " (" + str(monster.current_hp) + \
						"/" + str(monster.max_hp) + ") using {}".format(str(monster.current_move)) for monster in available_monsters])
			else:
				string += "\n    ".join([str(monster.monster_id) + " (" + str(monster.current_hp) + \
							"/" + str(monster.max_hp) + ") using {} {}".format(str(monster.intent), 
							"" if not monster.intent.is_attack() else "for {}x{}".format(monster.move_adjusted_damage, monster.move_hits)) for monster in available_monsters])
			string += "\nHand: " + ", ".join([str(card) for card in self.hand])
		if self.choice_list != []:
			string += "\nChoices: " + str(self.choice_list) + " \n"
		available_commands = []
		if self.end_available:
			available_commands.append("end")
		if self.potion_available:
			available_commands.append("potion")
		if self.play_available:
			available_commands.append("play")
		if self.proceed_available:
			available_commands.append("proceed")
		if self.cancel_available:
			available_commands.append("cancel")
		string += "\n\nAvailable commands: " + ", ".join(available_commands) + "\n"
		string += "---- Game State " + str(self.state_id) + " ---->\n\n"
		return string


	@classmethod
	def from_json(cls, json_state, available_commands):
		game = cls()
		game.current_action = json_state.get("current_action", None)
		if not game.player:
			game.player = spirecomm.spire.character.Player(json_state.get("max_hp"), json_state.get("current_hp"))
		else:
			game.player.current_hp = json_state.get("current_hp")
			game.player.max_hp = json_state.get("max_hp")
		game.floor = json_state.get("floor")
		game.act = json_state.get("act")
		game.gold = json_state.get("gold")
		game.seed = json_state.get("seed")
		game.character = spirecomm.spire.character.PlayerClass[json_state.get("class")]
		game.ascension_level = json_state.get("ascension_level")
		game.relics = [spirecomm.spire.relic.Relic.from_json(json_relic) for json_relic in json_state.get("relics")]
		game.deck = [spirecomm.spire.card.Card.from_json(json_card) for json_card in json_state.get("deck")]
		game.map = spirecomm.spire.map.Map.from_json(json_state.get("map"))
		game.potions = [spirecomm.spire.potion.Potion.from_json(potion) for potion in json_state.get("potions")]
		game.act_boss = json_state.get("act_boss", None)

		# Screen State

		game.screen_up = json_state.get("is_screen_up", False)
		game.screen_type = spirecomm.spire.screen.ScreenType[json_state.get("screen_type")]
		game.screen = spirecomm.spire.screen.screen_from_json(game.screen_type, json_state.get("screen_state"))
		game.room_phase = RoomPhase[json_state.get("room_phase")]
		game.room_type = json_state.get("room_type")
		game.choice_available = "choice_list" in json_state
		if game.choice_available:
			game.choice_list = json_state.get("choice_list")

		# Combat state

		game.in_combat = game.room_phase == RoomPhase.COMBAT
		if game.in_combat:
			combat_state = json_state.get("combat_state")
			game.player = spirecomm.spire.character.Player.from_json(combat_state.get("player"))
			game.monsters = [spirecomm.spire.character.Monster.from_json(json_monster) for json_monster in combat_state.get("monsters")]
			for i, monster in enumerate(game.monsters):
				monster.monster_index = i
			game.draw_pile = [spirecomm.spire.card.Card.from_json(json_card) for json_card in combat_state.get("draw_pile")]
			game.discard_pile = [spirecomm.spire.card.Card.from_json(json_card) for json_card in combat_state.get("discard_pile")]
			game.exhaust_pile = [spirecomm.spire.card.Card.from_json(json_card) for json_card in combat_state.get("exhaust_pile")]
			game.hand = [spirecomm.spire.card.Card.from_json(json_card) for json_card in combat_state.get("hand")]

		# Available Commands

		game.end_available = "end" in available_commands
		game.potion_available = "potion" in available_commands
		game.play_available = "play" in available_commands
		game.proceed_available = "proceed" in available_commands or "confirm" in available_commands
		game.cancel_available = "cancel" in available_commands or "leave" in available_commands \
								or "return" in available_commands or "skip" in available_commands

		# Added state info
		if game.floor != game.tracked_state["previous_floor"]:
			game.on_floor_change()
			game.tracked_state["previous_floor"] = game.floor
		
		return game

	def are_potions_full(self):
		for potion in self.potions:
			if potion.potion_id == "Potion Slot":
				return False
		return True

	def get_real_potions(self):
		potions = []
		for potion in self.potions:
			if potion.potion_id != "Potion Slot":
				potions.append(potion)
		return potions
		

# ---------- MCTS SIMULATIONS -----------		

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
		delta_potions = len(self.potions) - len(original_game_state.potions)
		
		reward = 0
		reward += delta_hp * MCTS_HP_VALUE
		reward += delta_max_hp * MCTS_MAX_HP_VALUE
		reward += delta_potions * MCTS_POTION_VALUE
		reward -= self.combat_round * MCTS_ROUND_COST
		
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				d.write("\n~~~~~~~~~~~~~~\n")
				d.write("\nTerminal state reached, reward: " + str(reward) + "\n")
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
	
	
	# Returns a new state
	def takeAction(self, action):
	
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
		
		if action.command.startswith("end"):
			return new_state.simulate_end_turn(action)
		elif action.command.startswith("potion"):
			# assumes we have this potion, will throw an error if we don't I think
			return new_state.simulate_potion(action)
		elif action.command.startswith("play"):
			return new_state.simulate_play(action)
		elif action.command.startswith("state"):
			return new_state
		elif action.command.startswith("choose") and new_state.current_action == "DiscoveryAction":
			return new_state.simulate_discovery(action)
		else:
			raise Exception("Chosen simulated action is not a valid combat action: " + str(action))
		
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
					self.debug_log.append("Last move was " + str(last_move))
					if "next_move" in moveset[last_move]:
						list_of_next_moves = moveset[last_move]["next_move"]
						moveset = {}
						for movedict in list_of_next_moves:
							moveset[movedict["name"]] = monster.intents["moveset"][movedict["name"]]
							moveset[movedict["name"]]["probability"] = movedict["probability"]
						self.debug_log.append("Found next moves to be: " + str(moveset))
				
				# pick from our moveset
				for move, details in moveset.items():
					moves.append(move)
					move_weights.append(details["probability"])
				selected_move = random.choices(population=moves, weights=move_weights)[0] # choices returns as a list of size 1
				
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
					if not exceeds_limit:
						break
		
		# Check if Lagavulin should still be sleeping
		moveset = monster.intents["moveset"]
		if monster.monster_id == "Lagavulin":
			if monster.current_hp != monster.max_hp and monster.has_power("Asleep"):
				# wake up
				selected_move = "Stunned"
				monster.add_power("Metallicize", -8)
				monster.remove_power("Asleep")
		
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
		
		for power in self.player.powers:
			if power.power_name == "Strength Down":
				self.apply_debuff(self.player, "Strength Down", -1 * power.amount)
				self.player.remove_power("Strength Down")
			elif power.power_name == "Dexterity Down":
				self.apply_debuff(self.player, "Dexterity Down", -1 * power.amount)
				self.player.remove_power("Dexterity Down")
			elif power.power_name == "Focus Down":
				self.apply_debuff(self.player, "Focus Down", -1 * power.amount)
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
				
	# Note: this function isn't called anywhere yet, but it also might not need to ever be simulated
	def apply_start_of_combat_effects(self, character):
	
		# TODO move innate cards to top of deck / starting hand
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
	
		if character is self.player:
			# FIXME relics technically activate in order of acquisition

			if self.player.current_hp / self.player.max_hp < 0.50:
				self.tracked_state["below_half_health"] = True
				if self.has_relic("Red Skull") and self.tracked_state["below_half_health"]:
					self.player.add_power("Strength", 3)
			if self.has_relic("Thread and Needle"):
				character.add_power("Plated Armor", 4)
			if self.has_relic("Anchor"):
				self.add_block(character, 10)
			if self.has_relic("Fossilized Helix"):
				self.player.add_power("Buffer", 1)
			if self.has_relic("Vajra"):
				self.player.add_power("Strength", 1)
			if self.has_relic("Oddly Smooth Stone"):
				self.player.add_power("Dexterity", 1)
			if self.has_relic("Bronze Scales"):
				character.add_power("Thorns", 3)
			if self.has_relic("Mark of Pain"):
				self.draw_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
				self.draw_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
				random.shuffle(draw_pile)
			if self.has_relic("Philosopher's Stone"):
				available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
				for monster in available_monsters:
					monster.add_power("Strength", 1)
			if self.has_relic("Bag of Preparation"):
				random.shuffle(self.draw_pile)
				self.hand += self.draw_pile.pop(0)
				self.hand += self.draw_pile.pop(0)
			if self.has_relic("Bag of Marbles"):
				for monster in available_monsters:
					monster.add_power("Vulnerable", 1)
			if self.has_relic("Red Mask"):
				for monster in available_monsters:
					monster.add_power("Weakened", 1)
			if self.has_relic("Snecko Eye"):
				self.player.add_power("Confused", 1)
				
	def check_intents(self):
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for monster in available_monsters:
			pass	
			

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
		# TODO use this to replace all hp subtractions
		# TODO check for changes to intent and effects on death
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
		
		# death checks
		if target.current_hp <= 0 and unblocked_damage > 0: # just died
		
			self.debug_log.append("Killed " + str(target))
		
			if self.has_relic("Gremlin Horn"):
				self.draw_card()
				self.player.energy += 1
		
			if target.has_power("Spore Cloud"):
				self.player.add_power("Vulnerable", target.get_power_amount("Spore Cloud"))
				target.remove_power("Spore Cloud")
			# TODO corpse explosion, that relic that shifts poison (specimen?)
			if target.has_power("Thievery"):
				self.tracked_state["incoming_gold"] += target.misc
				
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		
		
		# TODO add this in when we start pre-calculating intents (for MCTS). Right now we only calculate intents on their turn
		for monster in available_monsters:
			#if monster.monster_id == "GremlinTsundere" and len(available_monsters) < 2:
				
			
				
			# intent change checks
			# Check if Lagavulin should still be sleeping
			
			moveset = monster.intents["moveset"]
			if monster.monster_id == "Lagavulin":
				if monster.current_hp != monster.max_hp and monster.has_power("Asleep"):
					# wake up 
					monster.current_move = "Stunned"
					monster.add_power("Metallicize", -8)
					monster.remove_power("Asleep")
		
		
		
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
	
	def draw_card(self, draw=1):
		if self.player.has_power("No Draw"):
			return
		if len(self.draw_pile) == 0:
			self.reshuffle_deck()
		card = self.draw_pile.pop(0)
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
		spirecomm.spire.potion.Potion("Steroid Potion", "Steroid Potion", True, True, False),
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
		
	def generate_random_colorless_card(self):
		cards = []
		
		# card_id, name, card_type, rarity, upgrades=0, has_target=False, cost=0, misc=0, is_playable=False, exhausts=False
		
	
		return cards
		
	def generate_random_attack_card(self, player_class=spirecomm.spire.character.PlayerClass.IRONCLAD):
		cards = []
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			pass # TODO
	
		return cards
	
	def generate_random_skill_card(self, player_class=spirecomm.spire.character.PlayerClass.IRONCLAD):
		cards = []
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			pass # TODO
	
		return cards
	
	def generate_random_power_card(self, player_class=spirecomm.spire.character.PlayerClass.IRONCLAD):
		cards = []
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			pass # TODO
	
		return cards
		
	
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
					# if self.combat_round == 1:
		
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
											hits += 1
									if hits == monster.move_hits:
										monster.current_move = move
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
						effs = monster.intents["moveset"][move]["effects"]
						json_base = None
						for eff in effs:
							if eff["name"] == "Damage":
								json_base = eff["amount"]
						if not json_base:
							raise Exception("Malformed Louse json when calculating base damage")
						attack_adjustment = monster.move_base_damage - json_base
						monster.misc = attack_adjustment
						self.debug_log.append("Adjusted damage for louse: " + str(monster.misc))
								
					# Finally, apply the intended move
					effects = monster.intents["moveset"][monster.current_move]["effects"]
					for effect in effects:
						
						if effect["name"] == "Damage":
							base_damage = effect["amount"]
							if monster.monster_id == "FuzzyLouseNormal" or monster.monster_id == "FuzzyLouseDefensive":
								base_damage += monster.misc # adjustment because louses are variable
								self.debug_log.append("Adjusted damage for louse: " + str(monster.misc))
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
						
						elif effect["name"] == "Escape":
							monster.is_gone = True
						
						else:
							self.debug_log.append("WARN: Unknown effect " + effect["name"])
						
					# increment count of moves in a row
					if str(monster) in self.tracked_state["monsters_last_attacks"]:
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
			
			
		# TODO check if any enemies died / half-health effects and if anything happens when they do, e.g. thieves return gold
		
			
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
		# TODO
		
	
		return new_state
		
		
	# Returns a new state
	def simulate_potion(self, action):
	
		self.potions.remove(action.potion) # fixme? might need to match on name rather than ID
		self.potions.append(spirecomm.spire.potion.Potion("Potion Slot", "Potion Slot", False, False, False))
		
		if action.potion.name == "Artifact Potion":
			self.player.add_power("Artifact", 1)
		
		elif action.potion.name == "Attack Potion":
			# TODO
			pass
		
		elif action.potion.name == "Block Potion":
			self.add_block(self.player, 12)
		
		elif action.potion.name == "Blood Potion":
			hp_gained = int(math.ceil(self.player.max_hp * 0.10)) # FIXME updated to 0.25 in a recent patch, but we're not on that patch yet
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
		
		elif action.potion.name == "Steroid Potion":
			self.player.add_power("Strength", 5)
			self.player.add_power("Strength Down", 5)
		
		elif action.potion.name == "Strength Potion":
			self.player.add_power("Strength", 3)
		
		elif action.potion.name == "Swift Potion":
			self.draw_card(3)
		
		elif action.potion.name == "Weak Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				if monster == action.target_monster:
					monster.add_power("Weakened", 3)
		
		else:
			self.debug_log.append("ERROR: No handler for potion: " + str(action.potion))
			
			
		# TODO check if any enemies died and if anything happens when they do
			
		
		if self.debug_file and self.debug_log != []:
			with open(self.debug_file, 'a+') as d:
				d.write('\n')
				d.write('\n'.join(self.debug_log))
				d.write('\n')
				#d.write("\nNew State:\n")
				#d.write(str(self))
		
		self.tracked_state["is_simulation"] = True
		
		return self
		
		
	# Returns a new state
	def simulate_play(self, action, free_play=False):
	
		if not action.card.loadedFromJSON:
			raise Exception("Card not loaded from JSON: " + str(action.card.name))
			
		if action.card.type != spirecomm.spire.card.CardType.CURSE:
			# Velvet Choker does count copies of free_play cards, but allows them to go off past 6
			self.increment_relic("Velvet Choker") # doesn't count Blue Candle
			
		self.tracked_state["cards_played_this_turn"] += 1
		
		# Fix for IDs not matching
		found = False # test
		for c in self.hand:
			if action.card == c:
				action.card = c
				found = True 
		if not found:
			raise Exception("Could not find " + action.card.get_id_str() + " in " + str([card.get_id_str() for card in self.hand]))
							
		if not free_play:
			# move card to discard
			self.player.energy -= action.card.cost
			self.hand.remove(action.card)
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
						raise Exception("Action expects a target; check " + str(action.card) + ".json for potential error.")
					if action.target_monster == monster:
						effect_targets = [monster]
						break
			elif effect["target"] == "all":
				effect_targets = available_monsters
			elif effect["target"] == "random":
				effect_targets = random.choice(available_monsters)
				
			
			# Do effect
			for target in effect_targets:
			
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
					
				elif effect["effect"] == "Armaments+":
					for card in self.hand:
						card.upgrade()
					
					
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
						
				elif effect["effect"] == "Havoc":
					havoc_card = self.draw_pile.pop(0)
					# randomly play the card
					play_action = PlayCardAction(havoc_card)
					if havoc_card.has_target:
						available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
						selected_monster = random.choice(available_monsters)
						play_action.target_index = selected_monster.monster_index
						play_action.target_monster = selected_monster
						
					self.simulate_play(play_action)
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
					
				elif effect["effect"] == "Draw":
					self.draw_card(draw=effect["amount"])
						
				elif effect["effect"] == "Madness":
					selected_card = random.choice([c for c in self.hand if c.cost > 0])
					selected_card.cost = 0
					
				else:
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
						
		# TODO check if any enemies died / half-health effects and if anything happens when they do (e.g. ritual dagger)
		
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
		
		
		
		