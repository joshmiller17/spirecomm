from enum import Enum
import copy
import random
import math
import os
import spirecomm

# The State Changer modifies a Game state
# Inputs: Game state, attribute (as a StateDiff key), value to change it by


class StateChanger:

	# related to agent.state_diff(), this function takes a key, value pair from state_diff and creates that change to the state
	def changeState(self, key, value):
		set_attrs = ["room_phase", "room_type", "current_action", "act_boss", "floor", "act", "in_combat"]
		if key in set_attrs:
			setattr(self, key, value)
		if key == "choices_added":
			for v in value:
				self.choice_list.append(v)
		if key == "choices_removed":
			for v in value:
				self.choice_list.remove(v)
		change_attrs = ["gold", "state_id", "combat_round"]
		if key in change_attrs:
			setattr(self, key, self.key + value)
		if key == "relics":
			for v in value:
				if type(v) is tuple and len(v) == 2:
					self.set_relic_counter(v[0], self.get_relic(v[0].counter) + v[1])
				else:
					if self.has_relic(v):
						self.relics.remove(v)
					else:
						self.relics.append(v)
			

		# FIXME state_diff gives string, not the actual card object we would need to do this
		# if key == "cards_added":
			# for v in value:
				# self.deck.append(v)
		# if key == "cards_removed":
			# for v in value:
				# self.deck.remove(v)
		# if key == "cards_upgraded":
			# pass
			

		if key == "potions_added":
			for v in value:
				for p in self.potions:
					if p.name == "Potion Slot":
						p.name = v
						break
		
		if key == "potions_removed":
			for v in value:
				for p in self.potions:
					if p.name == v:
						p.name = "Potion Slot"
						break

		

			
			# monsters1 = [monster for monster in state1.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			# monsters2 = [monster for monster in state2.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]

			# checked_monsters = []
			# for monster1 in monsters1:
				# for monster2 in monsters2:
					# if monster1 == monster2 and monster1 not in checked_monsters:
						# checked_monsters.append(monster1) # avoid checking twice
						# m_id = monster1.monster_id + str(monster1.monster_index)
						# if monster1.current_hp != monster2.current_hp:
							# monster_changes[m_id + "_hp"] = monster2.current_hp - monster1.current_hp
						# if monster1.block != monster2.block:
								# monster_changes[m_id + "_block"] = monster2.block - monster1.block
							
						# if monster1.powers != monster2.powers:
							# monster_changes[m_id + "_powers_changed"] = []
							# monster_changes[m_id + "_powers_added"] = []
							# monster_changes[m_id + "_powers_removed"] = []
							# powers_changed = set([p.power_name for p in set(monster2.powers).symmetric_difference(set(monster1.powers))])
							# for name in powers_changed:
								# powers1 = [p.power_name for p in monster1.powers]
								# powers2 = [p.power_name for p in monster2.powers]
								# if name in powers1 and name in powers2:
									# monster_changes[m_id + "_powers_changed"].append((name, monster2.get_power(name).amount - monster1.get_power(name).amount))
									# continue
								# elif name in powers2:
									# monster_changes[m_id + "_powers_added"].append((name, monster2.get_power(name).amount))
									# continue
								# elif name in powers1:
									# monster_changes[m_id + "_powers_removed"].append((name, monster1.get_power(name).amount))
									# continue
								
							# if monster_changes[m_id + "_powers_added"] == []:
								# monster_changes.pop(m_id + "_powers_added", None)
							# if monster_changes[m_id + "_powers_removed"] == []:
								# monster_changes.pop(m_id + "_powers_removed", None)
							# if monster_changes[m_id + "_powers_changed"] == []:
								# monster_changes.pop(m_id + "_powers_changed", None)
						# break
						
					# elif monster1 not in monsters2:
						# try:
							# unavailable_monster = [monster for monster in state2.monsters if monster1 == monster][0]
							# cause = "unknown"
							# if unavailable_monster.half_dead:
								# cause = "half dead"
							# elif unavailable_monster.is_gone or unavailable_monster.current_hp <= 0:
								# cause = "is gone / dead"
						# except:
							# cause = "no longer exists"
						
						# monster_changes[monster1.monster_id + str(monster1.monster_index) + "_not_available"] = cause
					# elif monster2 not in monsters1:
						# monster_changes[monster1.monster_id + str(monster1.monster_index) + "_returned_with_hp"] = monster2.current_hp
								
						
			
			# if monster_changes != {}:
				# for key, value in monster_changes.items():
					# diff[key] = value
			
			# # general fixme?: better record linking between state1 and state2? right now most record linking is by name or ID (which might not be the same necessarily)
			
			# delta_hand = len(state2.hand) - len(state1.hand)
			# delta_draw_pile = len(state2.draw_pile) - len(state1.draw_pile)
			# delta_discard = len(state2.discard_pile) - len(state1.discard_pile)
			# delta_exhaust = len(state2.exhaust_pile) - len(state1.exhaust_pile)
			# if delta_hand != 0:
				# diff["delta_hand"] = delta_hand
			# if delta_draw_pile != 0:
				# diff["delta_draw_pile"] = delta_draw_pile
			# if delta_discard != 0:
				# diff["delta_discard"] = delta_discard
			# if delta_exhaust != 0:
				# diff["delta_exhaust"] = delta_exhaust
			
			# if not ignore_randomness:
		
				# cards_changed_from_hand = set(state2.hand).symmetric_difference(set(state1.hand))
				# cards_changed_from_draw = set(state2.draw_pile).symmetric_difference(set(state1.draw_pile))
				# cards_changed_from_discard = set(state2.discard_pile).symmetric_difference(set(state1.discard_pile))
				# cards_changed_from_exhaust = set(state2.exhaust_pile).symmetric_difference(set(state1.exhaust_pile))
				# cards_changed = cards_changed_from_hand | cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
				# cards_changed_outside_hand = cards_changed_from_draw | cards_changed_from_discard | cards_changed_from_exhaust
				
				# card_actions = ["drawn", "hand_to_deck", "discovered", "exhausted", "exhumed", "discarded",
								# "discard_to_hand", "deck_to_discard", "discard_to_deck",
								# "discovered_to_deck", "discovered_to_discard", # "playability_changed", <- deprecated
								 # "power_played", "upgraded", "unknown_change", "err_pc"]
				
				# for a in card_actions:
					# diff[a] = []
					
				# # TODO some checks if none of these cases are true
				# for card in cards_changed:
					# if card in cards_changed_from_draw and card in cards_changed_from_hand:
						# # draw
						# if card in state2.hand:
							# diff["drawn"].append(card.get_id_str())
							# continue
						# # hand to deck
						# elif card in state1.hand:
							# diff["hand_to_deck"].append(card.get_id_str())
							# continue	
					# elif card in cards_changed_from_hand and card in cards_changed_from_discard:
						# # discard
						# if card in state1.hand:
							# diff["discarded"].append(card.get_id_str())
							# continue
						# # discard to hand
						# elif card in state2.hand:
							# diff["discard_to_hand"].append(card.get_id_str())
							# continue	
					# elif card in cards_changed_from_exhaust and card in cards_changed_from_hand:
						# #exhaust
						# if card in state1.hand:
							# diff["exhausted"].append(card.get_id_str())
							# continue
						# #exhume
						# elif card in state2.hand:
							# diff["exhumed"].append(card.get_id_str())
							# continue
					# elif card in cards_changed_from_discard and card in cards_changed_from_draw:
						# #deck to discard
						# if card in state2.discard_pile:
							# diff["deck_to_discard"].append(card.get_id_str())
							# continue
						# # discard to draw_pile
						# elif card in state1.discard_pile:
							# diff["discard_to_deck"].append(card.get_id_str())
							# continue
					# elif card in cards_changed_from_hand and card in state2.hand and card not in cards_changed_outside_hand:
						# #discovered
						# if card not in state1.hand and card not in state1.draw_pile and card not in state1.discard_pile and card not in state1.exhaust_pile:
							# diff["discovered"].append(card.get_id_str())
							# continue
					# elif card in cards_changed_from_hand and card in state1.hand and card not in cards_changed_outside_hand:
						# if card.type is spirecomm.spire.card.CardType.POWER and card not in state2.hand:
							# # power played
							# diff["power_played"].append(card.get_id_str())
							# continue
						# elif card.upgrades > 0: # assume upgrading it was the different thing
							# diff["upgraded"].append(card.get_id_str()) # FIXME check this more strongly
							# continue	
					# elif card in state2.draw_pile and card not in state1.draw_pile and card not in state1.hand and card not in state1.discard_pile and card not in state1.exhaust_pile:
						# # discovered to draw pile, e.g. status effect
						# diff["discovered_to_deck"].append(card.get_id_str())
						# continue
					# elif card in state2.discard_pile and card not in state1.discard_pile and card not in state1.hand and card not in state1.draw_pile and card not in state1.exhaust_pile:
						# # discovered to discard, e.g. status effect
						# diff["discovered_to_discard"].append(card.get_id_str())
						# continue
					# else:
						# self.log("WARN: unknown card change " + card.get_id_str(), debug=3)
						# diff["unknown_change"].append(card.get_id_str())
						# if card in state1.draw_pile:
							# self.log("card was in state1 draw pile")
						# if card in state2.draw_pile:
							# self.log("card is in state2 draw pile")
						# if card in state1.discard_pile:
							# self.log("card was in state1 discard")
						# if card in state2.discard_pile:
							# self.log("card is in state2 discard")
						# if card in state1.hand:
							# self.log("card was in state1 hand")
						# if card in state2.hand:
							# self.log("card is in state2 hand")
						# if card in state1.exhaust_pile:
							# self.log("card was in state1 exhaust")
						# if card in state2.exhaust_pile:
							# self.log("card is in state2 exhaust")
				
				# for a in card_actions:
					# if diff[a] == []:
						# diff.pop(a, None)
		
			# if state1.player.block != state2.player.block:
				# diff["block"] = state2.player.block - state1.player.block
				
			# if state1.player.powers != state2.player.powers:
				# diff["powers_changed"] = []
				# diff["powers_added"] = []
				# diff["powers_removed"] = []
				# powers_changed = set(state2.player.powers).symmetric_difference(set(state1.player.powers))
				# for power in powers_changed:
					# #power1 = next(p for p in state1.player.powers if p.power_name == power.power_name)
					# #power2 = next(p for p in state2.player.powers if p.power_name == power.power_name)
					# if power in state1.player.powers and power in state2.player.powers:
							# diff["powers_changed"].append((power.power_name, power2.amount - power1.amount))
					# elif power in state2.player.powers:
						# for p2 in state2.player.powers:
							# if p2.power_name == power.power_name:
								# diff["powers_added"].append((p2.power_name, p2.amount))
								# continue
					# elif power in state1.player.powers:
						# for p1 in state1.player.powers:
							# if p1.power_name == power.power_name:
								# diff["powers_added"].append((p1.power_name, p1.amount))
								# continue
									
				# if diff["powers_added"] == []:
					# diff.pop("powers_added", None)
				# if diff["powers_removed"] == []:
					# diff.pop("powers_removed", None)
				# if diff["powers_changed"] == []:
					# diff.pop("powers_changed", None)