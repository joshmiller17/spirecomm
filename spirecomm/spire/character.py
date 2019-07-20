from enum import Enum
import json
import os
import random

from spirecomm.spire.power import Power
import spirecomm.config as config

MONSTERS_PATH = os.path.join(config.SPIRECOMM_PATH, "spirecomm", "ai", "monsters")


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

	def add_power(self, power_name, amount):
		for power in self.powers:
			if power.power_name == power_name:
				power.amount += amount
				if power.amount == 0:
					self.remove_power(power_name)
				return
		self.powers.append(Power(power_name, power_name, amount)) # FIXME setting power ID to power_name as temp fix
		
	def remove_power(self, power_name):
		for power in self.powers:
			if power.power_name == power_name:
				self.powers.remove(power)
				return
				
	def decrement_power(self, power_name):
		self.add_power(power_name, -1)
		
	def has_power(self, power_name):
		for power in self.powers:
			if power.power_name == power_name:
				return True
		return False
		
	def get_power(self, power_name):
		for power in self.powers:
			if power.power_name == power_name:
				return power
		return None
		
	def get_power_amount(self, power_name):
		for power in self.powers:
			if power.power_name == power_name:
				return power.amount
		return 0
		
	def __str__(self):
		return "[Character] " + str(self.current_hp) + "/" + str(self.max_hp) + ", Block " + str(self.block)

class Player(Character):

	# NOTE: DO NOT USE CURRENT_HP/MAX_HP
	# Use game.current_hp and game.max_hp instead

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
		self.move_base_damage = move_base_damage # the base attack amount
		self.move_adjusted_damage = move_adjusted_damage # the damage number the player sees
		self.move_hits = move_hits
		self.monster_index = 0
		
		self.misc = 0 # used by Louses to track their bonus damage. Will also probably be used by others in the future

		
		self.move_powers = []
		self.move_block = 0
		
		# Load from monsters/[name].json
		'''
		Intents format
		startswith: Move or none
		moveset: {
			name : 
				{
				probability: chance to use
				effects: list of effects as { name : name, amount: amount}
				}
			}
		limits: { (Movename, # in a row max) }
		'''
		#TODO some enemies transition on trigger condition, like half health

		self.intents = {}
		self.current_move = None
		self.expected_next_move = None # not used yet
		
		try:
			with open(os.path.join(MONSTERS_PATH, self.monster_id + ".json"),"r") as f:
				self.intents = json.load(f)
		except Exception as e:
			with open('err.log', 'a+') as err_file:
				err_file.write("\nMonster Error: " + str(self.monster_id))
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
		
	def __str__(self):
		return str(self.monster_id) + " <" + str(self.monster_index) + "> "


	# FIXME, which __eq__ do we want?
	
	def __eq__(self, other):
			if self.monster_id == other.monster_id and self.name == other.name:
				if (self.monster_index is None and other.monster_index is None) or (self.monster_index == other.monster_index):
					return True
			return False

	# def __eq__(self, other):
		# if self.name == other.name and self.current_hp == other.current_hp and self.max_hp == other.max_hp and self.block == other.block:
			# if len(self.powers) == len(other.powers):
				# for i in range(len(self.powers)):
					# if self.powers[i] != other.powers[i]:
						# return False
				# return True
		# return False
