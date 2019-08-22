from enum import Enum
import copy
import random
import math
import os
import spirecomm

# The StateDiff object is similar to a dictionary and contains all attributes by which two states are self.different


# Returns a dict of what changed between game states
# ignore_randomness is used by simulation_sanity_check and ignores poor simulations due to chance
class StateDiff:

	
	def __init__(self, state1, state2, agent, ignore_randomness=False):
		self.state1 = state1
		self.state2 = state2
		self.ignore_randomness = ignore_randomness
		self.agent = agent
		self.diff = {}
		self.get_diff()


	def get_diff(self):
		self.check_basics()
		self.check_relics()
		self.check_deck()
		self.check_potions()
		self.check_combat_status()
		return self.diff
		
	def check_basics(self):
		if self.state1.room_phase != self.state2.room_phase:
			self.diff["room_phase"] = str(self.state2.room_phase)
		if self.state1.room_type != self.state2.room_type:
			self.diff["room_type"] = str(self.state2.room_type)
		choices_added = set(self.state2.choice_list) - (set(self.state1.choice_list))
		choices_added = list(choices_added)
		if choices_added != []:
			self.diff["choices_added"] = choices_added
		choices_removed = set(self.state1.choice_list) - (set(self.state2.choice_list))
		choices_removed = list(choices_removed)
		if choices_removed != []:
			self.diff["choices_removed"] = choices_removed
		if self.state1.current_action != self.state2.current_action:
			self.diff["current_action"] = str(self.state2.current_action)
		if self.state1.act_boss != self.state2.act_boss:
			self.diff["act_boss"] = self.state2.act_boss
		if self.state1.player.current_hp != self.state2.player.current_hp:
			self.diff["current_hp"] = self.state2.player.current_hp - self.state1.player.current_hp
		if self.state1.player.max_hp != self.state2.player.max_hp:
			self.diff["max_hp"] = self.state2.player.max_hp - self.state1.player.max_hp
		if self.state1.floor != self.state2.floor:
			self.diff["floor"] = self.state2.floor
		if self.state1.act != self.state2.act:
			self.diff["act"] = self.state2.act
		if self.state1.gold != self.state2.gold:
			self.diff["gold"] = self.state2.gold - self.state1.gold
		#if self.state1.state_id != self.state2.state_id:
		#	self.diff["state_id"] = self.state2.state_id - self.state1.state_id
		if self.state1.combat_round != self.state2.combat_round:
			self.diff["combat_round"] = self.state2.combat_round - self.state1.combat_round
		
	
	def check_relics(self):
		if self.state1.relics != self.state2.relics:
			self.diff["relics"] = []
			for relic2 in self.state2.relics:
				found = False
				for relic1 in self.state1.relics:
					if relic1.name == relic2.name:
						found = True
						if relic1.counter != relic2.counter:
							self.diff["relics"].append((relic2.name, relic2.counter - relic1.counter))
				if not found:
					self.diff["relics"].append(relic2.name)
			if self.diff["relics"] == []:
				self.diff.pop("relics", None)
				
	def check_deck(self):
		if self.state1.deck != self.state2.deck:
			self.diff["cards_added"] = []
			self.diff["cards_removed"] = []
			self.diff["cards_upgraded"] = []
			cards_changed = set(self.state2.deck).symmetric_difference(set(self.state1.deck))
			for card in cards_changed:
				if card not in self.state2.deck:
					self.diff["cards_removed"].append(str(card))
				elif card not in self.state1.deck:
					self.diff["cards_added"].append(str(card))
				else: # assume upgraded or changed in some way
					self.diff["cards_upgraded"].append(str(card))
			if self.diff["cards_added"] == []:
				self.diff.pop("cards_added", None)
			if self.diff["cards_removed"] == []:
				self.diff.pop("cards_removed", None)
			if self.diff["cards_upgraded"] == []:
				self.diff.pop("cards_upgraded", None)
			#self.diff["deck_added"] = [c.name for c in list(set(self.state2.deck) - set(self.state1.deck))]
			#self.diff["deck_removed"] = [c.name for c in list(set(self.state1.deck) - set(self.state2.deck))]
			
			
	def check_potions(self):
		if self.state1.potions != self.state2.potions:
			self.diff["potions_added"] = [str(p) for p in list(set(self.state2.potions) - set(self.state1.potions))]
			self.diff["potions_removed"] = [str(p) for p in list(set(self.state1.potions) - set(self.state2.potions))]	
		if self.state1.in_combat != self.state2.in_combat:
			self.diff["in_combat"] = self.state2.in_combat
		

	def check_combat_status(self):
		if self.state1.in_combat and self.state2.in_combat:
			self.check_monster_status()
			self.check_card_status()
		
	def check_monster_status(self):
		monster_changes = {}
		
		monsters1 = [monster for monster in self.state1.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		monsters2 = [monster for monster in self.state2.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]

		checked_monsters = []
		for monster1 in monsters1:
			for monster2 in monsters2:
				if monster1 == monster2 and monster1 not in checked_monsters:
					checked_monsters.append(monster1) # avoid checking twice
					m_id = monster1.monster_id + str(monster1.monster_index)
					if monster1.current_hp != monster2.current_hp:
						monster_changes[m_id + "_hp"] = monster2.current_hp - monster1.current_hp
					if monster1.block != monster2.block:
							monster_changes[m_id + "_block"] = monster2.block - monster1.block
						
					if monster1.powers != monster2.powers:
						powers_changed = self.get_power_changes(monster1.powers, monster2.powers)
						for name, amount in powers_changed.items():
							self.diff[m_id + "_power_change_" + name] = amount
							self.agent.log("DEBUG: m1 powers are " + str([str(power) for power in monster1.powers]))
							self.agent.log("DEBUG: m2 powers are " + str([str(power) for power in monster2.powers]))
							self.agent.log("DEBUG: m1 is " + str(monster1))
							self.agent.log("DEBUG: m2 is " + str(monster2))
					break
					
				elif monster1 not in monsters2:
					try:
						unavailable_monster = [monster for monster in self.state2.monsters if monster1 == monster][0]
						cause = "unknown"
						if unavailable_monster.half_dead:
							cause = "half dead"
						elif unavailable_monster.is_gone or unavailable_monster.current_hp <= 0:
							cause = "is gone / dead"
					except:
						cause = "no longer exists"
					
					monster_changes[monster1.monster_id + str(monster1.monster_index) + "_not_available"] = cause
				elif monster2 not in monsters1:
					monster_changes[monster1.monster_id + str(monster1.monster_index) + "_returned_with_hp"] = monster2.current_hp
							
					
		
		if monster_changes != {}:
			for key, value in monster_changes.items():
				self.diff[key] = value
			
	# general fixme?: better record linking between self.state1 and self.state2? right now most record linking is by name or ID (which might not be the same necessarily)
	def check_card_status(self):	
			
		delta_hand = len(self.state2.hand) - len(self.state1.hand)
		delta_draw_pile = len(self.state2.draw_pile) - len(self.state1.draw_pile)
		delta_discard = len(self.state2.discard_pile) - len(self.state1.discard_pile)
		delta_exhaust = len(self.state2.exhaust_pile) - len(self.state1.exhaust_pile)
		if delta_hand != 0:
			self.diff["delta_hand"] = delta_hand
		if delta_draw_pile != 0:
			self.diff["delta_draw_pile"] = delta_draw_pile
		if delta_discard != 0:
			self.diff["delta_discard"] = delta_discard
		if delta_exhaust != 0:
			self.diff["delta_exhaust"] = delta_exhaust
		
		if not self.ignore_randomness:
	
			cards_changed_from_hand = set(self.state2.hand).symmetric_difference(set(self.state1.hand))
			cards_changed_from_draw = set(self.state2.draw_pile).symmetric_difference(set(self.state1.draw_pile))
			cards_changed_from_discard = set(self.state2.discard_pile).symmetric_difference(set(self.state1.discard_pile))
			cards_changed_from_exhaust = set(self.state2.exhaust_pile).symmetric_difference(set(self.state1.exhaust_pile))
			cards_changed = cards_changed_from_hand | cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
			cards_changed_outside_hand = cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
			
			choice_then_discard = ["Headbutt", "Armaments", "True Grit", "Dual Wield"]
			choice_then_exhaust = ["Warcry", "Infernal Blade"] # FIXME exhaust is possibly atomic with the card effect? more data collection needed, might need to make the card effect composite so that exhausting can happen atomically with effect
			
			card_actions = ["drawn", "hand_to_deck", "discovered", "exhausted", "exhumed", "discarded",
							"discard_to_hand", "deck_to_discard", "discard_to_deck",
							"discovered_to_deck", "discovered_to_discard", # "playability_changed", <- deprecated
							 "power_played", "upgraded", "exhausted_from_deck", "unknown_change", "err_pc"]
			
			for a in card_actions:
				self.diff[a] = []
				
			# TODO some checks if none of these cases are true
			for card in cards_changed:
				if card in cards_changed_from_draw and card in cards_changed_from_hand:
					# draw
					if card in self.state2.hand:
						self.diff["drawn"].append(card.get_id_str())
						continue
					# hand to deck
					elif card in self.state1.hand:
						self.diff["hand_to_deck"].append(card.get_id_str())
						continue	
				elif card in cards_changed_from_hand and card in cards_changed_from_discard:
					# discard
					if card in self.state1.hand:
						self.diff["discarded"].append(card.get_id_str())
						continue
					# discard to hand
					elif card in self.state2.hand:
						self.diff["discard_to_hand"].append(card.get_id_str())
						continue	
				elif card in cards_changed_from_exhaust and card in cards_changed_from_hand:
					#exhaust
					if card in self.state1.hand:
						self.diff["exhausted"].append(card.get_id_str())
						continue
					#exhume
					elif card in self.state2.hand:
						self.diff["exhumed"].append(card.get_id_str())
						continue
				elif card in self.state1.draw_pile and card in self.state2.exhaust_pile:
					# havoc etc
					self.diff["exhausted_from_deck"].append(card.get_id_str())
					continue
					
				elif card in cards_changed_from_discard and card in cards_changed_from_draw:
					#deck to discard
					if card in self.state2.discard_pile:
						self.diff["deck_to_discard"].append(card.get_id_str())
						continue
					# discard to draw_pile
					elif card in self.state1.discard_pile:
						self.diff["discard_to_deck"].append(card.get_id_str())
						continue
				elif card in cards_changed_from_hand and card in self.state2.hand and card not in cards_changed_outside_hand:
					#discovered
					if card not in self.state1.hand and card not in self.state1.draw_pile and card not in self.state1.discard_pile and card not in self.state1.exhaust_pile:
						self.diff["discovered"].append(card.get_id_str())
						continue
				elif card in cards_changed_from_hand and card in self.state1.hand and card not in cards_changed_outside_hand:
					if card.type is spirecomm.spire.card.CardType.POWER and card not in self.state2.hand:
						# power played
						self.diff["power_played"].append(card.get_id_str())
						continue
					elif card.upgrades > 0: # assume upgrading it was the self.different thing
						self.diff["upgraded"].append(card.get_id_str()) # FIXME check this more strongly
						continue	
				elif card in self.state2.draw_pile and card not in self.state1.draw_pile and card not in self.state1.hand and card not in self.state1.discard_pile and card not in self.state1.exhaust_pile:
					# discovered to draw pile, e.g. status effect
					self.diff["discovered_to_deck"].append(card.get_id_str())
					continue
				elif card in self.state2.discard_pile and card not in self.state1.discard_pile and card not in self.state1.hand and card not in self.state1.draw_pile and card not in self.state1.exhaust_pile:
					# discovered to discard, e.g. status effect
					self.diff["discovered_to_discard"].append(card.get_id_str())
					continue
				elif card.get_base_name() in choice_then_discard and card in self.state2.discard_pile: # these cards are weird since they get played and there's a state of change before it's discarded
					self.diff["made_choice_then_discarded"].append(card.get_id_str())
				elif card.get_base_name() in choice_then_exhaust and card in self.state2.exhaust_pile:  # these cards are weird since they get played and there's a state of change before it's exhausted
					self.diff["made_choice_then_exhausted"].append(card.get_id_str())
				else:
					self.agent.log("WARN: unknown card change " + card.get_id_str(), debug=3)
					self.diff["unknown_change"].append(card.get_id_str())
					if card in self.state1.draw_pile:
						self.agent.log("card was in self.state1 draw pile")
					if card in self.state2.draw_pile:
						self.agent.log("card is in self.state2 draw pile")
					if card in self.state1.discard_pile:
						self.agent.log("card was in self.state1 discard")
					if card in self.state2.discard_pile:
						self.agent.log("card is in self.state2 discard")
					if card in self.state1.hand:
						self.agent.log("card was in self.state1 hand")
					if card in self.state2.hand:
						self.agent.log("card is in self.state2 hand")
					if card in self.state1.exhaust_pile:
						self.agent.log("card was in self.state1 exhaust")
					if card in self.state2.exhaust_pile:
						self.agent.log("card is in self.state2 exhaust")
			
			for a in card_actions:
				if self.diff[a] == []:
					self.diff.pop(a, None)
	
		if self.state1.player.block != self.state2.player.block:
			self.diff["block"] = self.state2.player.block - self.state1.player.block
			
		if self.state1.player.powers != self.state2.player.powers:
			powers_changed = self.get_power_changes(self.state1.player.powers, self.state2.player.powers)
			for name, amount in powers_changed.items():
				self.diff["player_power_change_" + name] = amount
					

	# DEPRECATED
		# if self.diff != {}:
			# # TEST ONLY
			# self.agent.log("Our deck (self.state1):")
			# for card in self.state1.deck:
				# self.agent.log(card.get_id_str())
			# self.agent.log("Our hand (self.state1):")
			# for card in self.state1.hand:
				# self.agent.log(card.get_id_str())
			# self.agent.log("Our draw pile (self.state1):")
			# for card in self.state1.draw_pile:
				# self.agent.log(card.get_id_str())
			# self.agent.log("Our discard pile (self.state1):")
			# for card in self.state1.discard_pile:
				# self.agent.log(card.get_id_str())
			
			# self.agent.log("Our deck (self.state2):")
			# for card in self.state2.deck:
				# self.agent.log(card.get_id_str())
			# self.agent.log("Our hand (self.state2):")
			# for card in self.state2.hand:
				# self.agent.log(card.get_id_str())
			# self.agent.log("Our draw pile (self.state2):")
			# for card in self.state2.draw_pile:
				# self.agent.log(card.get_id_str())
			# self.agent.log("Our discard pile (self.state2):")
			# for card in self.state2.discard_pile:
				# self.agent.log(card.get_id_str())
				
				
	# return a dict of powers and amount difference, assume 0 for non existent
	def get_power_changes(self, powers1, powers2):
		# convert tuples to dicts
		p1 = {}
		p2 = {}
		for p in powers1:
			p1[p.power_name] = p.amount
		for p in powers2:
			p2[p.power_name] = p.amount
			

		diff = {}
		powers = set(())
		for p in p1.keys():
			powers.add(p)
		for p in p2.keys():
			powers.add(p)
		for power in powers:
			amt1 = 0
			if power in p1:
				amt1 = p1[power]
			amt2 = 0
			if power in p2:
				amt2 = p2[power]
			if amt2 != amt1:
				diff[power] = amt2 - amt1
		
		return diff