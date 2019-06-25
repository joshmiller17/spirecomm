from enum import Enum
import json

from spirecomm.spire.power import Power


class Intent(Enum):
	ATTACK = 1
	ATTACK_BUFF = 2
	ATTACK_DEBUFF = 3
	ATTACK_DEFEND = 4
	BUFF = 5
	DEBUFF = 6
	STRONG_DEBUFF = 7
	DEBUG = 8
	DEFEND = 9
	DEFEND_DEBUFF = 10
	DEFEND_BUFF = 11
	ESCAPE = 12
	MAGIC = 13
	NONE = 14
	SLEEP = 15
	STUN = 16
	UNKNOWN = 17

	def is_attack(self):
		return self in [Intent.ATTACK, Intent.ATTACK_BUFF, Intent.ATTACK_DEBUFF, Intent.ATTACK_DEFEND]


class PlayerClass(Enum):
	IRONCLAD = 1
	THE_SILENT = 2
	DEFECT = 3


class Orb:

	def __init__(self, name, orb_id, evoke_amount, passive_amount):
		self.name = name
		self.orb_id = orb_id
		self.evoke_amount = evoke_amount
		self.passive_amount = passive_amount

	@classmethod
	def from_json(cls, json_object):
		name = json_object.get("name")
		orb_id = json_object.get("id")
		evoke_amount = json_object.get("evoke_amount")
		passive_amount = json_object.get("passive_amount")
		orb = Orb(name, orb_id, evoke_amount, passive_amount)
		return orb


class Character:

	def __init__(self, max_hp, current_hp=None, block=0):
		self.max_hp = max_hp
		self.current_hp = current_hp
		if self.current_hp is None:
			self.current_hp = self.max_hp
		self.block = block
		self.powers = []


class Player(Character):

	def __init__(self, max_hp, current_hp=None, block=0, energy=0):
		super().__init__(max_hp, current_hp, block)
		self.energy = energy
		self.orbs = []

	@classmethod
	def from_json(cls, json_object):
		player = cls(json_object["max_hp"], json_object["current_hp"], json_object["block"], json_object["energy"])
		player.powers = [Power.from_json(json_power) for json_power in json_object["powers"]]
		player.orbs = [Orb.from_json(orb) for orb in json_object["orbs"]]
		return player


class Monster(Character):

	def __init__(self, name, monster_id, max_hp, current_hp, block, intent, half_dead, is_gone, move_id=-1, move_base_damage=0, move_adjusted_damage=0, move_hits=0):
		super().__init__(max_hp, current_hp, block)
		self.name = name
		self.monster_id = monster_id
		self.intent = intent
		self.half_dead = half_dead
		self.is_gone = is_gone # dead or out of combat
		self.move_id = move_id
		self.move_base_damage = move_base_damage
		self.move_adjusted_damage = move_adjusted_damage
		self.move_hits = move_hits
		self.monster_index = 0
		
		# Load from monsters/[name].json
		'''
		Move format
		name : effects (list)
		
		Effect format
		(name, value)
		e.g. Damage, 10; Vulnerable, 2
		
		'''
		self.moves = {}
		'''
		States format
		state : { transition: [(new state, probability), ...], moveset: [(move, probability), ...]}
		Always starts in state 1
		states dict lists probability to transition to other states
		TODO some enemies transition on trigger condition, like half health
		'''
		self.states = {}
		
		try:
			with open(os.path.join("..", "ai", "monsters", self.name + ".json"),"r") as f:
				jsonDict = json.load(f)
				self.states = jsonDict["states"]
				self.moves = jsonDict["moves"]
		except Exception as e:
			with open('err.log', 'a+') as err_file:
				err_file.write("\nMonster Error: " + str(self.name))
				err_file.write(str(e))
			#raise Exception(e)

	@classmethod
	def from_json(cls, json_object):
		name = json_object["name"]
		monster_id = json_object["id"]
		max_hp = json_object["max_hp"]
		current_hp = json_object["current_hp"]
		block = json_object["block"]
		intent = Intent[json_object["intent"]]
		half_dead = json_object["half_dead"]
		is_gone = json_object["is_gone"]
		move_id = json_object.get("move_id", -1)
		move_base_damage = json_object.get("move_base_damage", 0)
		move_adjusted_damage = json_object.get("move_adjusted_damage", 0)
		move_hits = json_object.get("move_hits", 0)
		monster = cls(name, monster_id, max_hp, current_hp, block, intent, half_dead, is_gone, move_id, move_base_damage, move_adjusted_damage, move_hits)
		monster.powers = [Power.from_json(json_power) for json_power in json_object["powers"]]
		return monster

	def __eq__(self, other):
		if self.name == other.name and self.current_hp == other.current_hp and self.max_hp == other.max_hp and self.block == other.block:
			if len(self.powers) == len(other.powers):
				for i in range(len(self.powers)):
					if self.powers[i] != other.powers[i]:
						return False
				return True
		return False
