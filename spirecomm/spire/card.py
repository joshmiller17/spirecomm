from enum import Enum
import os
import json
import spirecomm.config as config

CARDS_PATH = os.path.join(config.SPIRECOMM_PATH, "spirecomm", "ai", "cards")


class CardType(Enum):
	ATTACK = 1
	SKILL = 2
	POWER = 3
	STATUS = 4
	CURSE = 5


class CardRarity(Enum):
	BASIC = 1
	COMMON = 2
	UNCOMMON = 3
	RARE = 4
	SPECIAL = 5
	CURSE = 6


class Card:
	def __init__(self, card_id, name, card_type, rarity, upgrades=0, has_target=False, cost=0, uuid="", misc=0, price=0, is_playable=False, exhausts=False):
		self.card_id = card_id
		self.name = name
		self.type = card_type
		self.rarity = rarity
		self.upgrades = upgrades
		self.has_target = has_target
		self.cost = cost
		self.uuid = uuid
		self.misc = misc
		self.price = price
		self.is_playable = is_playable
		self.exhausts = exhausts
		
		
		# Static values, load from cards/[name].json
		self.value = {}
		self.value["damage"] = None
		self.value["mitigation"] = None
		self.value["scaling damage"] = None
		self.value["scaling mitigation"] = None
		self.value["aoe"] = None
		self.value["draw"] = None
		self.value["utility"] = None
		'''Synergy format:
		name: name of synergy
		amount: float value of effectiveness
		enable: boolean whether it contributes its value to enabling the synergy or just benefits from it
		(Synergy type (string), value (float)) tuple
		e.g. pummel might have (Strength, 4)
		'''
		self.value["synergies"] = []
		
		
		self.effects = {}	
		self.loadedFromJSON = False
		'''Effect format:
		target: self, one, all, or random (enemy)
		effect: effect name
		amount: amount or value of the effect
		random is only randomized once per effect: an effect listed as "one" will take the target of the last effect
		-- this is in case the entire card's target is randomized, simply change the first effect from one -> random
		e.g.:
		- Well-Laid Plains is (self, Retain, 1)
		- Defend is (self, Block, 5)
		- Headbutt is (one, DiscardToTop, 1) -- cards which have unique abilities can be tracked uniquely
		- Sword Boomerang is three copies of (random, damage, 3)
		'''
		self.effects["target"] = None
		self.effects["effect"] = None
		self.effects["amount"] = None
		
		try:
			with open(os.path.join(CARDS_PATH, self.get_clean_name() + ".json"),"r") as f:
				jsonData = json.load(f)
				self.value = jsonData["value"]
				self.effects = jsonData["effects"]
				self.loadedFromJSON = True
		except Exception as e:
			with open('err.log', 'a+') as err_file:
				err_file.write("\nCard Error: " + str(self.get_clean_name(name)))
				err_file.write(str(e))

			#raise Exception(e)
		
		# Dynamic values
		self.value["upgrade value"] = None # How much do we want to upgrade this card?
		self.value["purge value"] = None # How much do we want to get rid of this card?
		self.value["synergy value"] = None # How well does this work with our deck?
		
	# Strip periods and extra upgrades for cards like J.A.X. and Searing Blow+3
	def get_clean_name(self):
		new_name = ''.join(self.name.split('.'))
		if new_name.find('+') != -1:
			new_name = new_name[:new_name.find('+')]
		return new_name
		

	@classmethod
	def from_json(cls, json_object):
		return cls(
			card_id=json_object["id"],
			name=json_object["name"],
			card_type=CardType[json_object["type"]],
			rarity=CardRarity[json_object["rarity"]],
			upgrades=json_object["upgrades"],
			has_target=json_object["has_target"],
			cost=json_object["cost"],
			uuid=json_object["uuid"],
			misc=json_object.get("misc", 0),
			price=json_object.get("price", 0),
			is_playable=json_object.get("is_playable", False),
			exhausts=json_object.get("exhausts", False)
		)
		
	def get_id_str(self):
		return str(self) + " <" + str(self.uuid) + ">"
		
	def __str__(self):
		name = self.get_clean_name()
		if self.upgrades > 1:
			name += str(self.upgrades)
		playcost = str(self.cost) if self.is_playable else "-" + str(self.cost) + "-"
		misc = ""
		if self.misc != 0:
			misc = " [" + str(self.misc) + "]"
		return name + misc + " (" + playcost +")"
		
	
	def __eq__(self, other):
		return self.uuid == other.uuid
		
	def __hash__(self):
		return hash(str(self.uuid))
