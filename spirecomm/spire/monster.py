import json
import os
import random

from spirecomm.spire.power import Power
import spirecomm.config as config

MONSTERS_PATH = os.path.join(config.SPIRECOMM_PATH, "spirecomm", "ai", "monsters")

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
		self.used_half_health_ability = False
		
		self.misc = 0 # used by Louses to track their bonus damage. Used by thieves to track gold stolen. Used by Guardian to track mode shifts

		
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
				if (self.monster_index is None or other.monster_index is None) or (self.monster_index == other.monster_index):
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