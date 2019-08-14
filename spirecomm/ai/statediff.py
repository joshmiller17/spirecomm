from enum import Enum
import copy
import random
import math
import os
import spirecomm

# The StateDiff object is similar to a dictionary and contains all attributes by which two states are different


class StateDiff:


# Returns a dict of what changed between game states
	# ignore_randomness is used by simulation_sanity_check and ignores poor simulations due to chance
	def state_diff(self, state1, state2, ignore_randomness=False):	

		if state1.player is None or state2.player is None:
			self.log("ERR: Null player")
			if state1.player is None:
				self.log("in state 1")
				self.log(str(state1))
			else:
				self.log("in state 2")
				self.log(str(state2))
			raise Exception("Null player")

		diff = {}
		if state1.room_phase != state2.room_phase:
			diff["room_phase"] = str(state2.room_phase)
		if state1.room_type != state2.room_type:
			diff["room_type"] = str(state2.room_type)
		choices_added = set(state2.choice_list) - (set(state1.choice_list))
		choices_added = list(choices_added)
		if choices_added != []:
			diff["choices_added"] = choices_added
		choices_removed = set(state1.choice_list) - (set(state2.choice_list))
		choices_removed = list(choices_removed)
		if choices_removed != []:
			diff["choices_removed"] = choices_removed
		if state1.current_action != state2.current_action:
			diff["current_action"] = str(state2.current_action)
		if state1.act_boss != state2.act_boss:
			diff["act_boss"] = state2.act_boss
		if state1.player.current_hp != state2.player.current_hp:
			diff["current_hp"] = state2.player.current_hp - state1.player.current_hp
		if state1.player.max_hp != state2.player.max_hp:
			diff["max_hp"] = state2.player.max_hp - state1.player.max_hp
		if state1.floor != state2.floor:
			diff["floor"] = state2.floor
		if state1.act != state2.act:
			diff["act"] = state2.act
		if state1.gold != state2.gold:
			diff["gold"] = state2.gold - state1.gold
		#if state1.state_id != state2.state_id:
		#	diff["state_id"] = state2.state_id - state1.state_id
		if state1.combat_round != state2.combat_round:
			diff["combat_round"] = state2.combat_round - state1.combat_round
			
		# relics
		if state1.relics != state2.relics:
			diff["relics"] = []
			for relic2 in state2.relics:
				found = False
				for relic1 in state1.relics:
					if relic1.name == relic2.name:
						found = True
						if relic1.counter != relic2.counter:
							diff["relics"].append((relic2.name, relic2.counter - relic1.counter))
				if not found:
					diff["relics"].append(relic2.name)
			if diff["relics"] == []:
				diff.pop("relics", None)
				
		# deck
		if state1.deck != state2.deck:
			diff["cards_added"] = []
			diff["cards_removed"] = []
			diff["cards_upgraded"] = []
			cards_changed = set(state2.deck).symmetric_difference(set(state1.deck))
			for card in cards_changed:
				if card not in state2.deck:
					diff["cards_removed"].append(str(card))
				elif card not in state1.deck:
					diff["cards_added"].append(str(card))
				else: # assume upgraded or changed in some way
					diff["cards_upgraded"].append(str(card))
			if diff["cards_added"] == []:
				diff.pop("cards_added", None)
			if diff["cards_removed"] == []:
				diff.pop("cards_removed", None)
			if diff["cards_upgraded"] == []:
				diff.pop("cards_upgraded", None)
			#diff["deck_added"] = [c.name for c in list(set(state2.deck) - set(state1.deck))]
			#diff["deck_removed"] = [c.name for c in list(set(state1.deck) - set(state2.deck))]
			
			
		if state1.potions != state2.potions:
			diff["potions_added"] = [str(p) for p in list(set(state2.potions) - set(state1.potions))]
			diff["potions_removed"] = [str(p) for p in list(set(state1.potions) - set(state2.potions))]	
		if state1.in_combat != state2.in_combat:
			diff["in_combat"] = state2.in_combat
		

		if state1.in_combat and state2.in_combat:
		
			monster_changes = {}
			
			monsters1 = [monster for monster in state1.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			monsters2 = [monster for monster in state2.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]

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
								diff[m_id + "_power_change_" + name] = amount
								self.log("DEBUG: m1 powers are " + str([str(power) for power in monster1.powers]))
								self.log("DEBUG: m2 powers are " + str([str(power) for power in monster2.powers]))
								self.log("DEBUG: m1 is " + str(monster1))
								self.log("DEBUG: m2 is " + str(monster2))
						break
						
					elif monster1 not in monsters2:
						try:
							unavailable_monster = [monster for monster in state2.monsters if monster1 == monster][0]
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
					diff[key] = value
			
			# general fixme?: better record linking between state1 and state2? right now most record linking is by name or ID (which might not be the same necessarily)
			
			delta_hand = len(state2.hand) - len(state1.hand)
			delta_draw_pile = len(state2.draw_pile) - len(state1.draw_pile)
			delta_discard = len(state2.discard_pile) - len(state1.discard_pile)
			delta_exhaust = len(state2.exhaust_pile) - len(state1.exhaust_pile)
			if delta_hand != 0:
				diff["delta_hand"] = delta_hand
			if delta_draw_pile != 0:
				diff["delta_draw_pile"] = delta_draw_pile
			if delta_discard != 0:
				diff["delta_discard"] = delta_discard
			if delta_exhaust != 0:
				diff["delta_exhaust"] = delta_exhaust
			
			if not ignore_randomness:
		
				cards_changed_from_hand = set(state2.hand).symmetric_difference(set(state1.hand))
				cards_changed_from_draw = set(state2.draw_pile).symmetric_difference(set(state1.draw_pile))
				cards_changed_from_discard = set(state2.discard_pile).symmetric_difference(set(state1.discard_pile))
				cards_changed_from_exhaust = set(state2.exhaust_pile).symmetric_difference(set(state1.exhaust_pile))
				cards_changed = cards_changed_from_hand | cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
				cards_changed_outside_hand = cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
				
				choice_then_discard = ["Headbutt", "Armaments", "True Grit", "Dual Wield"]
				choice_then_exhaust = ["Warcry", "Infernal Blade"] # FIXME exhaust is possibly atomic with the card effect? more data collection needed, might need to make the card effect composite so that exhausting can happen atomically with effect
				
				card_actions = ["drawn", "hand_to_deck", "discovered", "exhausted", "exhumed", "discarded",
								"discard_to_hand", "deck_to_discard", "discard_to_deck",
								"discovered_to_deck", "discovered_to_discard", # "playability_changed", <- deprecated
								 "power_played", "upgraded", "exhausted_from_deck", "unknown_change", "err_pc"]
				
				for a in card_actions:
					diff[a] = []
					
				# TODO some checks if none of these cases are true
				for card in cards_changed:
					if card in cards_changed_from_draw and card in cards_changed_from_hand:
						# draw
						if card in state2.hand:
							diff["drawn"].append(card.get_id_str())
							continue
						# hand to deck
						elif card in state1.hand:
							diff["hand_to_deck"].append(card.get_id_str())
							continue	
					elif card in cards_changed_from_hand and card in cards_changed_from_discard:
						# discard
						if card in state1.hand:
							diff["discarded"].append(card.get_id_str())
							continue
						# discard to hand
						elif card in state2.hand:
							diff["discard_to_hand"].append(card.get_id_str())
							continue	
					elif card in cards_changed_from_exhaust and card in cards_changed_from_hand:
						#exhaust
						if card in state1.hand:
							diff["exhausted"].append(card.get_id_str())
							continue
						#exhume
						elif card in state2.hand:
							diff["exhumed"].append(card.get_id_str())
							continue
					elif card in state1.draw_pile and card in state2.exhaust_pile:
						# havoc etc
						diff["exhausted_from_deck"].append(card.get_id_str())
						continue
						
					elif card in cards_changed_from_discard and card in cards_changed_from_draw:
						#deck to discard
						if card in state2.discard_pile:
							diff["deck_to_discard"].append(card.get_id_str())
							continue
						# discard to draw_pile
						elif card in state1.discard_pile:
							diff["discard_to_deck"].append(card.get_id_str())
							continue
					elif card in cards_changed_from_hand and card in state2.hand and card not in cards_changed_outside_hand:
						#discovered
						if card not in state1.hand and card not in state1.draw_pile and card not in state1.discard_pile and card not in state1.exhaust_pile:
							diff["discovered"].append(card.get_id_str())
							continue
					elif card in cards_changed_from_hand and card in state1.hand and card not in cards_changed_outside_hand:
						if card.type is spirecomm.spire.card.CardType.POWER and card not in state2.hand:
							# power played
							diff["power_played"].append(card.get_id_str())
							continue
						elif card.upgrades > 0: # assume upgrading it was the different thing
							diff["upgraded"].append(card.get_id_str()) # FIXME check this more strongly
							continue	
					elif card in state2.draw_pile and card not in state1.draw_pile and card not in state1.hand and card not in state1.discard_pile and card not in state1.exhaust_pile:
						# discovered to draw pile, e.g. status effect
						diff["discovered_to_deck"].append(card.get_id_str())
						continue
					elif card in state2.discard_pile and card not in state1.discard_pile and card not in state1.hand and card not in state1.draw_pile and card not in state1.exhaust_pile:
						# discovered to discard, e.g. status effect
						diff["discovered_to_discard"].append(card.get_id_str())
						continue
					elif card.get_base_name() in choice_then_discard and card in state2.discard_pile: # these cards are weird since they get played and there's a state of change before it's discarded
						diff["made_choice_then_discarded"].append(card.get_id_str())
					elif card.get_base_name() in choice_then_exhaust and card in state2.exhaust:  # these cards are weird since they get played and there's a state of change before it's exhausted
						diff["made_choice_then_exhausted"].append(card.get_id_str())
					else:
						self.log("WARN: unknown card change " + card.get_id_str(), debug=3)
						diff["unknown_change"].append(card.get_id_str())
						if card in state1.draw_pile:
							self.log("card was in state1 draw pile")
						if card in state2.draw_pile:
							self.log("card is in state2 draw pile")
						if card in state1.discard_pile:
							self.log("card was in state1 discard")
						if card in state2.discard_pile:
							self.log("card is in state2 discard")
						if card in state1.hand:
							self.log("card was in state1 hand")
						if card in state2.hand:
							self.log("card is in state2 hand")
						if card in state1.exhaust_pile:
							self.log("card was in state1 exhaust")
						if card in state2.exhaust_pile:
							self.log("card is in state2 exhaust")
				
				for a in card_actions:
					if diff[a] == []:
						diff.pop(a, None)
		
			if state1.player.block != state2.player.block:
				diff["block"] = state2.player.block - state1.player.block
				
			if state1.player.powers != state2.player.powers:
				powers_changed = self.get_power_changes(state1.player.powers, state2.player.powers)
				for name, amount in powers_changed.items():
					diff["player_power_change_" + name] = amount
					

		# if diff != {}:
			# # TEST ONLY
			# self.log("Our deck (state1):")
			# for card in state1.deck:
				# self.log(card.get_id_str())
			# self.log("Our hand (state1):")
			# for card in state1.hand:
				# self.log(card.get_id_str())
			# self.log("Our draw pile (state1):")
			# for card in state1.draw_pile:
				# self.log(card.get_id_str())
			# self.log("Our discard pile (state1):")
			# for card in state1.discard_pile:
				# self.log(card.get_id_str())
			
			# self.log("Our deck (state2):")
			# for card in state2.deck:
				# self.log(card.get_id_str())
			# self.log("Our hand (state2):")
			# for card in state2.hand:
				# self.log(card.get_id_str())
			# self.log("Our draw pile (state2):")
			# for card in state2.draw_pile:
				# self.log(card.get_id_str())
			# self.log("Our discard pile (state2):")
			# for card in state2.discard_pile:
				# self.log(card.get_id_str())
		
			
			
		return diff