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
		"lagavulin_is_asleep" : False,
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
		"powers_played_this_turn" : 0,
		"registered_start_of_combat" : False,
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
		self.tracked_state["lagavulin_is_asleep"] = False
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
		self.tracked_state["registered_start_of_combat"] = False

		
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
		
	# True iff either we're dead or the monsters are (or we smoke bomb)
	def isTerminal(self):
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		return self.player.current_hp <= 0 or len(available_monsters) < 1 or not self.in_combat
		
	def get_upgradable_cards(self, cards):
		upgradable = []
		for card in cards:
			if card.upgrades == 0 or card.get_base_name() == "Searing Blow":
				upgradable.append(card)
		return upgradable
	
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
		
		
		
		