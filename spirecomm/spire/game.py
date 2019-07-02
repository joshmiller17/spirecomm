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

from spirecomm.communication.action import *

# MCTS values for changes to game state
MCTS_MAX_HP_VALUE = 7
MCTS_HP_VALUE = 1
MCTS_POTION_VALUE = 7 # TODO change by potion type
MCTS_ROUND_COST = 0.5 # penalize long fights

class RoomPhase(Enum):
	COMBAT = 1,
	EVENT = 2,
	COMPLETE = 3,
	INCOMPLETE = 4


class Game:

	def __init__(self):

		# General state

		self.current_action = None
		self.act_boss = None
		self.current_hp = 0
		self.max_hp = 0
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
		self.original_state = None # For MCTS simulations; FIXME might be a huge memory storage for in-depth simulations? Consider only storing values important for reward func
		self.debug_file = None
		self.visited_shop = False
		self.previous_floor = 0 # used to recognize floor changes, i.e. when floor != previous_floor
		self.possible_actions = None
	
	# for some reason, pausing the game invalidates the state
	def is_valid(self):
		return self.end_available or self.potion_available or self.play_available or self.proceed_available or self.cancel_available
		
	# do any internal state updates we need to do if we change floors
	def on_floor_change(self):
		self.visited_shop = False
		self.combat_round = 1
		self.original_state = None
	
	def __str__(self):
		string = "\n\n---- Game State ----\n"
		#string += "Screen: " + str(self.screen) + " (" + str(self.screen_type) + ")\n"
		#string += "Room: " + str(self.room_type) + "\n"
		if self.in_combat:
			string += "\nHP: " + str(self.current_hp) + "/" + str(self.max_hp)
			string += "\nBlock: " + str(self.player.block)
			string += "\nRound: " + str(self.combat_round)
			string += "\nEnergy: " + str(self.player.energy)
			string += "\nMonsters: "
			string += "\n    ".join([str(monster.name) + "(" + str(monster.current_hp) + \
						"/" + str(monster.max_hp) + ") using {} {}".format(str(monster.intent), 
						"" if not monster.intent.is_attack() else "for {}x{}".format(monster.move_adjusted_damage, monster.move_hits)) for monster in self.monsters])
			string += "\nHand: " + ", ".join([card.name for card in self.hand])
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
		string += "\n\nAvailable commands: " + ", ".join(available_commands)
		return string


	@classmethod
	def from_json(cls, json_state, available_commands):
		game = cls()
		game.current_action = json_state.get("current_action", None)
		game.current_hp = json_state.get("current_hp")
		game.max_hp = json_state.get("max_hp")
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
		if game.floor != game.previous_floor:
			game.on_floor_change()
			game.previous_floor = game.floor
		
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

	# True iff either we're dead or the monsters are
	def isTerminal(self):
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		return self.current_hp <= 0 or len(available_monsters) < 1
		
	# return value of terminal state
	def getReward(self):
		
		# Trace back to where we started
		original_game_state = self
		while original_game_state.original_state is not None:
			original_game_state = original_game_state.original_state
			
		delta_hp = self.current_hp - original_game_state.current_hp
		delta_max_hp = self.max_hp - original_game_state.max_hp
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
		if self.possible_actions == None:
		
			possible_actions = [EndTurnAction()]
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				monster.recognize_intents()
			
			for potion in self.get_real_potions():
				if potion.requires_target:
					for monster in available_monsters:
						possible_actions.append(PotionAction(True, potion=potion, target_monster=monster))
				else:
					possible_actions.append(PotionAction(True, potion=potion))
					
			for card in self.hand:
				if len(available_monsters) == 0 and card != spirecomm.spire.card.CardType.POWER:
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

			self.possible_actions = possible_actions
				
		return self.possible_actions
	
	
	# Returns a new state
	def takeAction(self, action):
	
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				d.write("\n\nTaking Action: ")
				d.write(str(action) + "\n\n")
		
		new_state = copy.deepcopy(self)
		new_state.possible_actions = None
		new_state.original_state = self
		
		if action.command.startswith("end"):
			return new_state.simulate_end_turn(action)
		elif action.command.startswith("potion"):
			# assumes we have this potion, will throw an error if we don't I think
			new_state.potions.remove(action.potion) # fixme? might need to match on name rather than ID
			return new_state.simulate_potion(action)
		elif action.command.startswith("play"):
			return new_state.simulate_play(action)
		else:
			raise Exception("Chosen simulated action is not a valid combat action.")
		
		
	# Returns a new state
	def simulate_end_turn(self, action):
		
		debug_log = []
		
		self.combat_round += 1
		self.player.energy = 3 # hard coded energy per turn. TODO energy relics; if icecream, += 3
		# TODO this technically happens at the start of turn
		
		# TODO consider retaining cards (well-laid plans) or runic pyramid
		
		# Hand discarded
		self.discard_pile += self.hand
		self.hand = []
		
		# MONSTER TURN / MONSTERS ATTACK
		# TODO consider known intent rotation with more nuance
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for monster in available_monsters:
			#if monster.intents != {}: # we have correctly loaded intents JSON
			#	
			#else:
			# default behaviour: just assume the same move as the first turn of simulation
			if monster.intent.is_attack():
				if monster.move_adjusted_damage is not None:
					# are weak and vulnerable accounted for?
					incoming_damage = monster.move_adjusted_damage * monster.move_hits
					damage_after_block = incoming_damage - self.player.block
					if damage_after_block > 0:
						self.current_hp -= damage_after_block
						self.player.block = 0
					else:
						self.player.block -= incoming_damage

		# Draw new hand - TODO consider relic modifiers and known information
		while len(self.hand) < 5:
			if len(self.draw_pile) == 0:
				self.draw_pile = self.discard_pile
				self.discard_pile = []
			self.hand.append(self.draw_pile.pop(random.randrange(len(self.draw_pile))))
			
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				d.write('\n'.join(debug_log))
				#d.write("\nNew State:\n")
				#d.write(str(self))
			
		return self
		
		
	# Returns a new state
	def simulate_potion(self, action):
	
		debug_log = []
		
		if action.potion.name == "Artifact Potion":
			self.player.add_power("Artifact", 1)
		
		elif action.potion.name == "Attack Potion":
			# TODO
			pass
		
		elif action.potion.name == "Block Potion":
			self.player.block += 12
		
		elif action.potion.name == "Blood Potion":
			hp_gained = int(math.ceil(self.max_hp * 0.10))
			new_hp = min(self.max_hp, self.current_hp + hp_gained)
			self.current_hp = new_hp
		
		elif action.potion.name == "Dexterity Potion":
			self.player.add_power("Dexterity", 2)
		
		elif action.potion.name == "Energy Potion":
			self.player.energy += 2
		
		elif action.potion.name == "Entropic Brew":
			# TODO
			pass
		
		elif action.potion.name == "Essence of Steel":
			self.player.add_power("Plated Armor", 4)
		
		elif action.potion.name == "Explosive Potion":
			# TODO
			pass
		
		# TODO Fairy in a Bottle is not usable but should be considered in game state
		
		elif action.potion.name == "Fear Potion":
			# TODO
			pass
		
		elif action.potion.name == "Fire Potion":
			# TODO
			pass
		
		elif action.potion.name == "Focus Potion":
			self.player.add_power("Focus", 2)
		
		elif action.potion.name == "Fruit Juice":
			self.max_hp += 5
			self.current_hp += 5
		
		elif action.potion.name == "Gambler's Brew":
			# TODO
			pass
		
		elif action.potion.name == "Liquid Bronze":
			self.player.add_power("Thorns", 3)
		
		elif action.potion.name == "Poison Potion":
			# TODO
			pass
		
		elif action.potion.name == "Power Potion":
			# TODO
			pass
		
		elif action.potion.name == "Skill Potion":
			# TODO
			pass
		
		elif action.potion.name == "Smoke Bomb":
			# TODO
			pass
		
		elif action.potion.name == "Snecko Oil":
			# TODO
			pass
		
		elif action.potion.name == "Speed Potion":
			self.player.add_power("Dexterity", 5)
			self.player.add_power("Dexterity Down", 5)
		
		elif action.potion.name == "Steroid Potion":
			self.player.add_power("Strength", 5)
			self.player.add_power("Strength Down", 5)
		
		elif action.potion.name == "Strength Potion":
			self.player.add_power("Strength", 3)
		
		elif action.potion.name == "Swift Potion":
			# TODO
			pass
		
		elif action.potion.name == "Weak Potion":
			# TODO
			pass
		
		else:
			raise Exception("No handler for potion: " + str(action.potion))
		
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				d.write('\n'.join(debug_log))
				#d.write("\nNew State:\n")
				#d.write(str(self))
		
		return self
		
		
	# Returns a new state
	def simulate_play(self, action):
		# TODO
		
		debug_log = []
		
		if not action.card.loadedFromJSON:
			raise Exception("Card not loaded from JSON: " + str(action.card.name))
			
		
		# Fix for IDs not matching
		for c in self.hand:
			if action.card == c:
				action.card = c
			
		# move card to discard
		self.player.energy -= action.card.cost
		self.hand.remove(action.card)
		self.discard_pile.append(action.card)
			
		effect_targets = []
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for effect in action.card.effects:
			
			# Pick target(s)
			if effect["target"] == "self":
				effect_targets = [self.player]
			elif effect["target"] == "one":
				for monster in available_monsters:
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
					target.block += real_amount
					
				if effect["effect"] == "Damage":
					real_amount = effect["amount"]
					real_amount += self.player.get_power_amount("Strength")
					if self.player.has_power("Weakened"):
						real_amount = int(math.floor(real_amount - (0.25 * real_amount)))
					if target.has_power("Vulnerable"):
						real_amount = int(math.floor(real_amount + (0.50 * real_amount)))
					target.current_hp = max(target.current_hp - real_amount, 0)
			
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				d.write('\n'.join(debug_log))
				#d.write("\nNew State:\n")
				#d.write(str(self))
			
	
		return self
		
		
		
		