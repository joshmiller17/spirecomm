from enum import Enum
import copy
import random
import math
import os
import spirecomm


# This helper file contains a static database loaded from JSONs of Card metadata for Game state change simulations

class CardDatabase:

	VALID_CLASSES = ["COLORLESS", "IRONCLAD", "THE_SILENT", "DEFECT"]
	
	def __init__():
		# from JSON for discovery: ignores cards that are from an event or healing, sort by class
		self.cards = {"ATTACK": {}, "SKILL": {}, "POWER": {}}
		for player_class in VALID_CLASSES:
			self.cards[player_class] = {"RARE":[], "UNCOMMON": [], "COMMON": []}
			
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