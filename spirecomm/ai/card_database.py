from enum import Enum
import copy
import random
import math
import os
import spirecomm

import spirecomm.config as config


# This helper file contains a static database loaded from JSONs of Card metadata for Game state change simulations and discoveries
VALID_CLASSES = ["COLORLESS", "IRONCLAD", "THE_SILENT", "DEFECT"]
CARDS_PATH = os.path.join(config.SPIRECOMM_PATH, "spirecomm", "ai", "cards")
DEBUG_FILE = "game.log"

class CardDatabase:
	
	def __init__(self):
		# from JSON for discovery: ignores cards that are from an event or healing, sort by class
		self.cards = {"ATTACK": {}, "SKILL": {}, "POWER": {}}
		for player_class in VALID_CLASSES:
			self.cards[player_class] = {"RARE":[], "UNCOMMON": [], "COMMON": []}
			
		self.load_cards_from_json()
		
		
	def load_cards_from_json(self):
		d = open(DEBUG_FILE, 'a+')
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
		
	def load_by_name(self, name):
		card = spirecomm.spire.card.Card(f, f, -1, -1, compare_to_real=False)
		return card
		
		
	def get_cards(self, player_class="ANY", type="ALL", rarity="ALL"):
		ret = []
		
		for t in ["ATTACK", "SKILL", "POWER"]:
			if t == type or type == "ALL":
				for c in VALID_CLASSES:
					if c == player_class or player_class == "ANY":
						for r in ["RARE", "UNCOMMON", "COMMON"]:
							if r == rarity or rarity == "ALL":
								ret += self.cards[t][c][r]
		
		return ret
		
	def pick_card(self, player_class="ANY", type="ALL", rarity="ALL"): # FIXME for a more precise generator, add a cantbe=[] param to exclude cards we've already picked
		cards = self.get_cards(player_class, type, rarity)
		return random.choice(cards)
		
		
# --- Discovery ----
		
	# quick function for setting a discover action
	def discover(self, game, player_class, card_type="ALL", rarity="ALL", action="DiscoverAction", skip_available=False):
		game.screen_up = True
		game.screen_type = spirecomm.spire.screen.ScreenType.CardRewardScreen
		game.current_action = action
		
		generated_cards = []
		for _ in range(3):
			generated_cards.append(self.pick_card(player_class, card_type, rarity))
		
		game.screen = spirecomm.spire.screen.CardRewardScreen(cards=generated_cards,can_bowl=False, can_skip=skip_available)
		game.choice_list = [card.get_choice_str() for card in generated_cards]
		return game
			
			
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
		
	def generate_random_card(self, player_class, card_type, rare_only=False):
		if rare_only:
			return self.pick_card(player_class, card_type, "RARE")
		else:
			return self.pick_card(player_class, card_type, "ALL")

	
	def generate_random_colorless_card(self, rare_only=False):		
		return self.generate_random_card("COLORLESS", "ALL", rare_only)
		
	def generate_random_attack_card(self, player_class, rare_only=False):
		return self.generate_random_card(player_class, "ATTACK", rare_only)
	
	def generate_random_skill_card(self, player_class, rare_only=False):
		return self.generate_random_card(player_class, "SKILL", rare_only)
	
	def generate_random_power_card(self, player_class, rare_only=False):
		return self.generate_random_card(player_class, "POWER", rare_only)