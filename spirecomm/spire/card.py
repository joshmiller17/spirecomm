from enum import Enum
import os
import json
import spirecomm.config as config

CARDS_PATH = os.path.join(config.SPIRECOMM_PATH, "spirecomm", "ai", "cards")

VALID_CLASSES = ["EVENT", "COLORLESS", "IRONCLAD", "THE_SILENT", "DEFECT"]

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
	def __init__(self, card_id, name, card_type, rarity, upgrades=0, has_target=False, cost=0, uuid="", misc=0, price=0, is_playable=False, exhausts=False, test_only=False):
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
		
		self.test_only = test_only
		
		
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
				try:
					jsonData["class"] and jsonData["cost"] and jsonData["has_target"] and jsonData["is_playable"] and jsonData["exhausts"]
				except Exception as e:
					if not test_only:
						if not os.path.exists(os.path.join(CARDS_PATH, "temp")):
							os.makedirs(os.path.join(CARDS_PATH, "temp"))
						with open(os.path.join(CARDS_PATH, "temp", str(self.card_id) + ".json"), "w") as jf:
							d = {}
							d["card_id"] = self.card_id
							d["class"] = "FIXME"
							d["type"] = self.type.name
							d["rarity"] = self.rarity.name
							d["upgrades"] = self.upgrades
							d["has_target"] = self.has_target
							d["cost"] = self.cost
							d["misc"] = self.misc
							d["is_playable"] = self.is_playable
							d["exhausts"] = self.exhausts
							json.dump(d, jf)
						raise Exception("missing data; written to cards/temp/" + str(self.card_id) + ".json for you")
					else:
						raise Exception("missing data")
				else:
					if jsonData["class"] not in VALID_CLASSES:
						raise Exception("invalid class")
					if not any(jsonData["type"] == type.name for type in CardType):
						raise Exception("invalid type")
					if not any(jsonData["rarity"] == rarity.name for rarity in CardRarity):
						raise Exception("invalid rarity")
				actually_exhausts = False
				for effect in self.effects:
					if effect["effect"] == "Exhaust":
						actually_exhausts = True 
				if jsonData["exhausts"] != actually_exhausts:
					raise Exception("invalid exhaust: JSON says " + str(self.exhausts) + " but effects say " + str(actually_exhausts))
				
		except Exception as e:
			with open('err.log', 'a+') as err_file:
				if e in ['class', 'cost', 'has_target', 'is_playable', 'exhausts']:
					e = "missing data"
				err_file.write("\nCard Error: (" + str(self.get_clean_name() + ") "))
				err_file.write(str(e))
		
		# Dynamic values
		self.value["upgrade value"] = None # How much do we want to upgrade this card?
		self.value["purge value"] = None # How much do we want to get rid of this card?
		self.value["synergy value"] = None # How well does this work with our deck?
		
	# Strip periods and extra upgrades for cards like J.A.X. and Searing Blow+3
	def get_clean_name(self):
		new_name = ''.join(self.name.split('.'))
		if new_name.find('+') != -1:
			new_name = new_name[:new_name.find('+')+1]
		return new_name
		
	def upgrade(self): # FIXME I'm not sure that's how this works
		self.upgrades += 1
		if self.upgrades == 1:
			self.name.append("+")
			self.card_id.append("+")
			
		try:
			with open(os.path.join(CARDS_PATH, self.get_clean_name() + ".json"),"r") as f:
				jsonData = json.load(f)
				self.value = jsonData["value"]
				self.effects = jsonData["effects"]
				self.loadedFromJSON = True
		except Exception as e:
			with open('err.log', 'a+') as err_file:
				err_file.write("\nCard Error: " + str(self.get_clean_name()))
				err_file.write(str(e))

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
		return str(self) + " <" + str(self.uuid)[:4] + "...>"
		
	def __str__(self):
		name = self.get_clean_name() + " (" + str(self.card_id) +")"
		if self.upgrades > 1:
			name += str(self.upgrades)
		playcost = str(self.cost) if self.is_playable else "-" + str(self.cost) + "-"
		misc = ""
		if self.misc != 0:
			misc = " [" + str(self.misc) + "]"
		return name + misc + " (" + playcost +")"
		
	
	def __eq__(self, other):
		if self.uuid != "" and other.uuid != "":
			return self.uuid == other.uuid
		else:
			return self.name == other.name and self.cost == other.cost and self.misc == other.misc and self.upgrades == other.upgrades
		
	def __hash__(self):
		return hash(str(self.uuid))
