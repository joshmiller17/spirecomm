from enum import Enum
import json
import os
import random

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
		
	def __str__(self):
		return "[Player] " + str(self.current_hp) + "/" + str(self.max_hp) + ", Block " + str(self.block) + ", Energy " + str(self.energy)
		
	# orange pellets
	def remove_all_debuffs(self):
		for power in self.powers:
			if power.power_name in Power.DEBUFFS:
				self.remove_power(power.power_name)
			if (power.power_name is "Strength" or power.power_name is "Dexterity" or power.power_name is "Focus") and power.amount < 0:
				self.remove_power(power.power_name)