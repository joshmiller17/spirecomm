from enum import Enum
import os
import json


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
		self.value = {}
		
		# Static values, load from cards/[name].json
		self.value["damage"] = None
		self.value["mitigation"] = None
		self.value["scaling damage"] = None
		self.value["scaling mitigation"] = None
		self.value["aoe"] = None
		self.value["draw"] = None
		self.value["utility"] = None
		'''
		Synergy format:
		(Synergy type (string), value (float)) tuple
		e.g. pummel might have (Strength, 4)
		'''
		self.value["synergies"] = []
		
		'''
		Effect format:
		(Effect, value) tuple
		e.g.:
		- Well-Laid Plains is (Retain, 1)
		- Defend is (Block, 5)
		- Headbutt is (DiscardToTop, 1) -- cards which have unique abilities can be tracked uniquely
		'''
		self.value["effects"] = []
		
		try:
			with open(os.path.join("cards", self.name + ".json"),"r") as f:
				self.value = json.load(f)
		except Exception as e:
			with open('err.log', 'a+') as err_file:
				err_file.write("Card Error: " + str(self.name))
				err_file.write(e)
			#raise Exception(e)
		
		# Dynamic values
		self.value["upgrade value"] = None # How much do we want to upgrade this card?
		self.value["purge value"] = None # How much do we want to get rid of this card?
		self.value["synergy value"] = None # How well does this work with our deck?
		

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

	def __eq__(self, other):
		return self.uuid == other.uuid
