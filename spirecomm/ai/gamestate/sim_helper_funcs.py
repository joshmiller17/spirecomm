from enum import Enum
import copy
import random
import math
import os
import spirecomm

# This helper file contains minor simulation calculations for the main simulation functions
# generally the workhorse functions, e.g. what happens at the end of turns




		
			
def decrement_duration_powers(self, character):
	turn_based_powers = ["Vulnerable", "Frail", "Weakened", "No Block", "No Draw"]
	for power in character.powers:
		if power.power_name in turn_based_powers:
			character.decrement_power(power.power_name)	
	
def apply_end_of_turn_effects(self, monster): # (not for player use)

	for power in monster.powers:
		if power.power_name == "Shackles":
			monster.remove_power("Shackles")
		elif power.power_name == "Ritual":
			monster.add_power("Strength", power.amount)
		elif power.power_name == "Incantation":
			monster.add_power("Ritual", 3) # eventually adjust for ascensions
			monster.remove_power("Incantation")
		elif power.power_name == "Metallicize":
			monster.block += power.amount
		elif power.power_name == "Regen":
			monster.current_hp = min(monster.current_hp + power.amount, monster.max_hp)
			monster.decrement_power(power.power_name)

	self.decrement_duration_powers(monster)
			
			
# DEPRECATED - we already get this information when we see the first state of combat
# tracking it again here creates duplicates
def apply_start_of_combat_effects(self):

	available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
	
	for monster in available_monsters:
		if monster.monster_id == "Lagavulin" and monster.move_base_damage == 0:
			self.tracked_state["lagavulin_is_asleep"] = True
			
		# if "powers" in monster.intents:
			# for power in monster.intents["powers"]:
				# monster.add_power(power["name"], power["amount"])
				# self.debug_log.append("DEBUG: " + str(monster) + " has power " + str(power))
			

	# FIXME relics technically activate in order of acquisition (?)

	# if self.player.current_hp / self.player.max_hp < 0.50:
		# self.tracked_state["below_half_health"] = True
		# if self.has_relic("Red Skull") and self.tracked_state["below_half_health"]:
			# self.player.add_power("Strength", 3)
	# if self.has_relic("Thread and Needle"):
		# self.player.add_power("Plated Armor", 4)
	# if self.has_relic("Anchor"):
		# self.add_block(self.player, 10)
	# if self.has_relic("Fossilized Helix"):
		# self.player.add_power("Buffer", 1)
	# if self.has_relic("Vajra"):
		# self.player.add_power("Strength", 1)
	# if self.has_relic("Oddly Smooth Stone"):
		# self.player.add_power("Dexterity", 1)
	# if self.has_relic("Bronze Scales"):
		# self.player.add_power("Thorns", 3)
	# if self.has_relic("Mark of Pain"):
		# self.draw_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
		# self.draw_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
		# random.shuffle(draw_pile)
	# if self.has_relic("Philosopher's Stone"):
		# available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		# for monster in available_monsters:
			# monster.add_power("Strength", 1)
	# if self.has_relic("Bag of Preparation"):
		# random.shuffle(self.draw_pile)
		# self.hand += self.draw_pile.pop(0)
		# self.hand += self.draw_pile.pop(0)
	# if self.has_relic("Bag of Marbles"):
		# for monster in available_monsters:
			# monster.add_power("Vulnerable", 1)
	# if self.has_relic("Red Mask"):
		# for monster in available_monsters:
			# monster.add_power("Weakened", 1)
	# if self.has_relic("Snecko Eye"):
		# self.player.add_power("Confused", 1)
	# if self.has_relic("Gambling Chip"):
		# self.current_action = "GamblingChipAction"
		# self.screen = HandSelectScreen(self.hand, selected=[], num_cards=99, can_pick_zero=True)
		# self.screen_type = spirecomm.spire.screen.ScreenType.HAND_SELECT
		# self.screen_up = True
		
		
	# # TODO bottled cards are waiting on patch to CommMod
					
	# draw = self.draw_pile
	# for card in draw:
		# for effect in card.effects:
			# if effect["effect"] == "Innate":
				# self.hand += card
				# if self.has_power("Confused"):
					# card.cost = random.choice(range(4))
				# self.draw_pile.remove(card)
				# continue
		
def check_effects_on_kill(self, target):
	# Note: Ritual Dagger and Feed tracked by the card effects
	
	if target.current_hp > 0:
		return
	
	self.debug_log.append("Killed " + str(target))
	
	if self.has_relic("Gremlin Horn"):
		self.draw_card()
		self.player.energy += 1

	if target.has_power("Spore Cloud"):
		self.player.add_power("Vulnerable", target.get_power_amount("Spore Cloud"))
		target.remove_power("Spore Cloud")
	if target.has_power("Thievery") and not self.has_relic("Ectoplasm"):
		self.tracked_state["incoming_gold"] += target.misc
	
		
		
	# TODO corpse explosion, that relic that shifts poison (specimen?)
	
	
def choose_move(self, monster):
	available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
	if self.combat_round == 1 and "startswith" in monster.intents:
		selected_move = monster.intents["startswith"]
	elif monster.monster_id == "GremlinTsundere" and len(available_monsters) > 1:
		selected_move == "Protect"
	else:
		# make sure the attack we pick is not limited
		while True: # do-while
			move_weights = []
			moves = []
			moveset = monster.intents["moveset"]
			
			# change moveset to next move if exists
			if str(monster) in self.tracked_state["monsters_last_attacks"]:
				last_move = self.tracked_state["monsters_last_attacks"][str(monster)][0]
				self.debug_log.append("Last move was " + str(last_move) + "[" + str(self.tracked_state["monsters_last_attacks"][str(monster)][1]) + "]")
				if "next_move" in moveset[last_move]:
					list_of_next_moves = moveset[last_move]["next_move"]
					moveset = {}
					for movedict in list_of_next_moves:
						moveset[movedict["name"]] = monster.intents["moveset"][movedict["name"]]
						moveset[movedict["name"]]["probability"] = movedict["probability"]
					self.debug_log.append("Found next moves to be: " + str(moveset))
			
			# pick from our moveset
			if len(moveset) < 1:
				self.debug_log.append("ERR: no moves to pick from") # TODO remove after figuring out this bug
			for move, details in moveset.items():
				moves.append(move)
				move_weights.append(details["probability"])
			selected_move = random.choices(population=moves, weights=move_weights)[0] # choices returns as a list of size 1
			
			if selected_move is None:
				self.debug_log.append("ERR: selected move is none") # TODO remove after figuring out this bug
			
			# check limits
			if "limits" not in monster.intents or str(monster) not in self.tracked_state["monsters_last_attacks"]:
				# don't worry about limits, choose a random attack
				break
			else:
				exceeds_limit = False
				for limited_move, limited_times in monster.intents["limits"].items():
					if selected_move == limited_move and selected_move == self.tracked_state["monsters_last_attacks"][str(monster)][0]:
						if self.tracked_state["monsters_last_attacks"][str(monster)][1] + 1 >= limited_times: # selecting this would exceed limit:
							exceeds_limit = True
							self.debug_log.append("Tried to use " + selected_move + " but that would exceed a move limit")
				if not exceeds_limit:
					break
	
	# Check if Lagavulin should still be sleeping
	moveset = monster.intents["moveset"]
	if monster.monster_id == "Lagavulin":
		if monster.current_hp != monster.max_hp and self.tracked_state["lagavulin_is_asleep"]:
			# wake up
			selected_move = "Stunned"
			monster.add_power("Metallicize", -8)
			#monster.remove_power("Asleep") # I think this doesn't actually exist in the code
			self.tracked_state["lagavulin_is_asleep"] = False
	
	return selected_move

			
def check_intents(self):

	available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
	
	for monster in available_monsters:
	
		if monster.monster_id == "GremlinTsundere" and len(available_monsters) < 2:
			monster.current_move = None # reset to attacking
								
		# Check if Lagavulin should still be sleeping
		if monster.monster_id == "Lagavulin":
			if monster.current_hp != monster.max_hp and self.tracked_state["lagavulin_is_asleep"]:
				# wake up
				selected_move = "Stunned"
				monster.add_power("Metallicize", -8)
				monster.remove_power("Asleep") # I think this doesn't actually exist in the code
				self.tracked_state["lagavulin_is_asleep"] = False
	
		if "half_health" in monster.intents and not monster.used_half_health_ability:
			monster.used_half_health_ability = True
			monster.current_move = monster.intents["half_health"]
		

def apply_start_of_turn_effects(self, character):

	if character.has_power("Barricade"):
		pass
	elif character is self.player and self.has_relic("Calipers"):
		character.block = max(character.block - 15, 0)
	else:
		character.block = 0

	if character is self.player:
	
		self.player.block += self.tracked_state["next_turn_block"]
		self.tracked_state["next_turn_block"] = 0
		
		if self.has_relic("Brimstone"):
			self.player.add_power("Strength", 2)
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				monster.add_power("Strength", 1)
		
		if self.has_relic("Pocketwatch") and self.tracked_state["cards_played_last_turn"] <= 3:
			self.draw_card(3)
	
		if self.has_relic("Mercury Hourglass"):
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				self.apply_damage(3, None, monster)
	
		if self.has_relic("Runic Dodecahedron") and character.current_hp == character.max_hp:
			character.energy += 1
		if self.has_relic("Art of War") and self.tracked_state["attacks_played_last_turn"] == 0:
			character.energy += 1
			
		flower = self.get_relic("Happy Flower")
		if flower:
			flower.counter += 1
			if flower.counter >= 3:
				self.set_relic_counter("Happy Flower", 0)
				self.player.energy += 1
				
		burner = self.get_relic("Incense Burner")
		if burner:
			burner.counter += 1
			if burner.counter >= 6:
				self.set_relic_counter("Incense Burner", 0)
				self.player.add_power("Intangible", 1)
			
		if character.has_power("Brutality"):
			self.lose_hp(character, 1, from_card=True)
			self.draw_card()
			
		if self.has_relic("Warped Tongs"):
			selected_card = random.choice(self.hand)
			while selected_card.type == spirecomm.spire.card.CardType.CURSE or selected_card.type == spirecomm.spire.card.CardType.SPECIAL or (selected_card.upgrades > 0 and not selected_card.name.startswith("Searing Blow")):
				selected_card = random.choice(self.hand)
			selected_card.upgrade()
			
		if character.has_power("Mayhem"):
			for _ in range(character.get_power_amount("Mayhem")):
				card = self.draw_top_card()
				play_action = self.get_random_play(card)
				self.simulate_play(play_action)
				
			

def apply_debuff(self, target, debuff, amount):
	if debuff == "Weakened" and target is self.player and self.has_relic("Ginger"):
		return
	if debuff == "Frail" and target is self.player and self.has_relic("Turnip"):
		return	
	if debuff in spirecomm.spire.power.DEBUFFS and target.has_power("Artifact"):
		target.decrement_power("Artifact")
	else:
		target.add_power(debuff, amount)
		if debuff == "Vulnerable" and self.has_relic("Champion Belt"):
			self.apply_debuff(target, "Weakened", 1)
		if target is not self.player and self.player.has_power("SadisticNature"):
			target.current_hp = max(target.current_hp - self.player.get_power_amount("SadisticNature"), 0)
		
# helper function to calculate damage
# note: attacker may be None (e.g. Burn)
def calculate_real_damage(self, base_damage, attacker, target):
	damage = base_damage
	if attacker is not None:
		damage += attacker.get_power_amount("Strength")
		damage -= attacker.get_power_amount("Shackles")
		if attacker.has_power("Weakened"):
			if attacker is not self.player and self.has_relic("Paper Krane"):
				damage = damage - (0.40 * damage)
			else:
				damage = damage - (0.25 * damage)
	if target.has_power("Vulnerable"):
		if target is not self.player and self.has_relic("Paper Phrog"):
			damage = damage + (0.75 * damage)
		elif target is self.player and self.has_relic("Odd Mushroom"):
			damage = damage + (0.25 * damage)
		else:
			damage = damage + (0.50 * damage)
	return int(math.floor(damage))
	
# Note attacker may be None, e.g. from Burn card
def apply_damage(self, damage, attacker, target, from_attack=False, ignores_block=False):
	if target.has_power("Intangible") and not from_attack: # already adjusted for this in use_attack
		damage = 1
	if not ignores_block and target.block > 0:
		unblocked_damage = max(damage - target.block, 0)
		target.block = max(target.block - damage, 0)
		if target.block == 0 and target is not self.player and self.has_relic("Hand Drill"):
			self.apply_debuff(target, "Vulnerable", 2)
	else:
		unblocked_damage = damage
	capped_damage = min(target.current_hp, unblocked_damage)
	if unblocked_damage > 0 and unblocked_damage <= 5 and target is self.player and self.has_relic("Torii"):
		unblocked_damage = 1
	
	if unblocked_damage > 0:
		
		if target.has_power("Buffer"):
			target.decrement_power("Buffer")
		else:
			target.current_hp -= unblocked_damage
			self.check_effects_on_kill(target) # see if we killed them and if we do something about that
	
		# Guardian Mode Shift
		if target is not self.player and target.monster_id == "TheGuardian" and target.has_power("Mode Shift"):
			shift_amt = min(target.get_power_amount("Mode Shift", unblocked_damage))
			target.add_power("Mode Shift", -1 * shift_amt)
			if target.get_power_amount("Mode Shift") == 0: # Shift to Defensive
				target.current_move = "Defensive Mode"
	
	if unblocked_damage > 0 and target is self.player:
			
		if self.has_relic("Runic Cube"):
			self.draw_card()
	
		if self.has_relic("Self-Forming Clay"):
			self.tracked_state["next_turn_block"] += 3
	
		if target.current_hp / target.max_hp < 0.50:
			if self.has_relic("Red Skull") and not self.tracked_state["below_half_health"]:
				self.player.add_power("Strength", 3)
			self.tracked_state["below_half_health"] = True
	
		if self.tracked_state["times_lost_hp_this_combat"] == 0 and self.has_relic("Centennial Puzzle"):
			self.draw_card(3)
		self.tracked_state["times_lost_hp_this_combat"] += 1
		# TODO reduce the cost of blood for blood wherever it is in our deck
	
	
	self.check_intents()
	
	
	
# applies Damage attack and returns unblocked damage
# Note: this should only be used for ATTACK damage
# Note attacker may be None, e.g. from Burn card
def use_attack(self, base_damage, attacker, target):
	adjusted_damage = self.calculate_real_damage(base_damage, attacker, target)
	adjusted_damage = max(adjusted_damage, 0)
	pen_nib = self.get_relic("Pen Nib")
	if pen_nib is not None and pen_nib.counter >= 10:
		adjusted_damage *= 2 
		self.set_relic_counter("Pen Nib", 0)
	if attacker is not None:
		if attacker.has_power("Thievery"):
			gold_stolen = min(self.gold, attacker.get_power_amount("Thievery"))
			self.gold = self.gold - gold_stolen
			attacker.misc += gold_stolen
	if target.has_power("Angry"):
		target.add_power("Strength", target.get_power_amount("Angry"))
	if target.has_power("Intangible"):
		adjusted_damage = 1
	unblocked_damage = adjusted_damage - target.block
	unblocked_damage = max(unblocked_damage, 0)
	if unblocked_damage > 0:
		if unblocked_damage <= 5 and attacker is self.player and self.has_relic("The Boot"):
			unblocked_damage = 5
		if target is not self.player and target.block > 0 and self.has_relic("Hand Drill"):
			self.apply_debuff(target, "Vulnerable", 2)
		target.block = 0
		self.apply_damage(unblocked_damage, attacker, target, from_attack=True)
		if target.has_power("Plated Armor"):
			target.decrement_power("Plated Armor")
	else:
		target.block -= adjusted_damage
	if attacker is not None:
		if target.has_power("Flame Barrier"):
			self.use_attack(target.get_power_amount("Flame Barrier"), None, attacker)
		if target.has_power("Thorns"):
			self.use_attack(target.get_power_amount("Thorns"), None, attacker)
	if target.has_power("Curl Up"):
		curl = target.get_power_amount("Curl Up")
		self.add_block(target, curl)
		target.remove_power("Curl Up")
	return unblocked_damage
	
def add_block(self, target, amount):
	if not target.has_power("NoBlock"):
		if amount == "Entrench":
			target.block *= 2
		else:
			target.block += amount
		if target.has_power("Juggernaut"):
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			selected_monster = random.choice(available_monsters)
			self.use_attack(target.get_power_amount("Juggernaut"), None, selected_monster)
		
# HP lost from cards / relics
def lose_hp(self, target, amount, from_card=False):
	self.apply_damage(amount, None, target, ignores_block=True)
	if target is self.player and from_card and target.has_power("Rupture"):
		target.add_power("Strength", target.get_power_amount("Rupture"))
		
def gain_gold(self, gold):
	if not self.has_relic("Ectoplasm"):
		self.gold += gold
	
def gain_hp(self, target, amount): # assumes we're in combat
	if target is self.player:
		if self.has_relic("Magic Flower"):
			amount = math.ceil(amount * 1.5)
		if target.current_hp / target.max_hp > 0.50:
			if self.has_relic("Red Skull") and self.tracked_state["below_half_health"]:
				self.player.add_power("Strength", -3)
			self.tracked_state["below_half_health"] = False
			
	target.current_hp += amount
	
def exhaust_card(self, card):
	if card.name != "Necronomicurse":
		if self.has_relic("Strange Spoon") and random.random() > 0.50:
			self.discard_pile.append(card)
			return
		self.exhaust_pile.append(card)
	if self.player.has_power("DarkEmbrace"):
		self.draw_card()
	if self.player.has_power("Feel No Pain"):
		self.add_block(self.player, self.player.get_power_amount("Feel No Pain"))
	if card.name.startswith("Sentinel"):
		for effect in card.effects:
			if effect["effect"] == "Sentinel":
				self.player.energy += effect["amount"]
	if self.has_relic("Charon's Ashes"):
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for monster in available_monsters:
			monster.current_hp = max(monster.current_hp - 3, 0)
			
def reshuffle_deck(self):		
	self.draw_pile = self.discard_pile
	random.shuffle(self.draw_pile)
	self.discard_pile = []
	self.tracked_state["just_reshuffled"] = True
			
	sundial = self.get_relic("Sundial")
	if sundial:
		sundial.counter += 1
		if sundial.counter >= 3:
			self.set_relic_counter("Sundial", 0)
			self.player.energy += 2
			
	if self.has_relic("The Abacus"):
		self.player.block += 6
		
def draw_top_card(self):
	if len(self.draw_pile) == 0:
		self.reshuffle_deck()
	card = self.draw_pile.pop(0)
	return card

def draw_card(self, draw=1):
	if self.player.has_power("No Draw"):
		return
	card = self.draw_top_card()
	if len(self.hand) >= 10:
		self.discard_pile.append(card)
	else:
		self.hand.append(card)
	if card.type == spirecomm.spire.card.CardType.STATUS and self.player.has_power("Evolve"):
		for _ in range(self.player.get_power_amount("Evolve")):
			self.draw_card()
	if self.player.has_power("Confused"):
		card.cost = random.choice(range(4))
	if card.type == spirecomm.spire.card.CardType.SKILL and self.player.has_power("Corruption"):
		card.cost = 0
	
	for effect in card.effects:
		if effect["effect"] == "Void":
			self.player.energy = max(self.player.energy - 1, 0)
	
	if draw > 1:
		self.draw_card(draw - 1)
		
	
# parses damage in the form of amount or amount x hits, returns amounts and hits
def read_damage(self, string):
	if 'x' in str(string):
		list = string.split('x')
		return list[0], list[1]
	else:
		return string, 1
		
	
def get_random_play(self, card):
	# randomly play the card
	play_action = PlayCardAction(card)
	if card.has_target:
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		selected_monster = random.choice(available_monsters)
		play_action.target_index = selected_monster.monster_index
		play_action.target_monster = selected_monster
	return play_action
	
def find_monsters_move_deductively(self, monster):
	timeout = 100 # assume trying 100 times will be enough unless there's a problem
	while timeout > 0:
		# continue to randomly sample moves until we find one that fits
		move = self.choose_move(monster)
		details = monster.intents["moveset"][move]
		intent_str = details["intent_type"]
		if spirecomm.spire.character.Intent[intent_str] == monster.intent or self.has_relic("Runic Dome"):
			# if it's an attack, check the number of hits also
			if monster.intent.is_attack():
				hits = 0
				effects = details["effects"]
				for effect in effects:
					if effect["name"] == "Damage":
						amt, h = self.read_damage(effect["amount"])
						hits += h
				if hits == monster.move_hits:
					monster.current_move = move
					self.debug_log.append("DEBUG: counted hits " + str(hits) + " is " + str(hits)) # TODO remove
				else: 
					self.debug_log.append("DEBUG: counted hits " + str(hits) + " is not " + str(hits)) # TODO remove
			else:
				monster.current_move = move
				
		if monster.current_move is not None:
			if self.has_relic("Runic Dome"):
				self.debug_log.append("Guessed intent for " + str(monster) + " is " + str(monster.current_move))
			else:
				self.debug_log.append("Recognized intent for " + str(monster) + " is " + str(monster.current_move))
			break
		timeout -= 1
	return monster.current_move
	
def get_monsters_move(self, monster):
	if monster.current_move is not None:
		return monster.current_move
	else:
		if self.combat_round == 1 and "startswith" in monster.intents:
			monster.current_move = monster.intents["startswith"]
			if monster.monster_id == "Sentry" and monster.monster_index == 1: 	# The second Sentry starts with an attack rather than debuff
				monster.current_move = "Beam"
			self.debug_log.append("Known initial intent for " + str(monster) + " is " + str(monster.current_move))
		elif self.tracked_state["is_simulation"]: # generate random move
			monster.current_move = self.choose_move(monster)
			self.debug_log.append("Simulated intent for " + str(monster) + " is " + str(monster.current_move))
		else: # figure out move from what we know about it
			monster.current_move = self.find_monsters_move_deductively(monster)
			
	return monster.current_move

def apply_monster_effect(self, monster):
	if monster.intent == spirecomm.spire.character.Intent.ATTACK and (monster.monster_id == "FuzzyLouseNormal" or monster.monster_id == "FuzzyLouseDefensive"):
		# louses have a variable base attack
		effs = monster.intents["moveset"][monster.current_move]["effects"]
		json_base = None
		for eff in effs:
			if eff["name"] == "Damage":
				json_base = eff["amount"]
		if not json_base:
			raise Exception("Malformed Louse JSON when calculating base damage for " + str(monster.current_move))
		attack_adjustment = monster.move_base_damage - json_base
		monster.misc = attack_adjustment
		self.debug_log.append("Adjusted damage for louse: " + str(monster.misc))
				
	# Finally, apply the intended move
	effects = monster.intents["moveset"][monster.current_move]["effects"]
	for effect in effects:
		
		if effect["name"] == "Damage":
			amount, hits = self.read_damage(effect["amount"])
			base_damage = amount
			if monster.monster_id == "FuzzyLouseNormal" or monster.monster_id == "FuzzyLouseDefensive":
				base_damage += monster.misc # adjustment because louses are variable
				self.debug_log.append("Adjusted damage for louse: " + str(monster.misc))
			for _ in range(hits):
				unblocked_damage = self.use_attack(base_damage, monster, self.player)
				self.debug_log.append("Taking " + str(unblocked_damage) + " damage from " + str(monster))
				
		elif effect["name"] == "Block":
			self.add_block(monster, effect["amount"])
			
		elif effect["name"] == "BlockOtherRandom":
			selected_ally = None
			while selected_ally is None or selected_ally is monster:
				selected_ally = random.choice(available_monsters)
			self.add_block(selected_ally, effect["amount"])
			
		elif effect["name"] in BUFFS:
			monster.add_power(effect["name"], effect["amount"])
			
		elif effect["name"] in DEBUFFS:
			self.apply_debuff(self.player, effect["name"], effect["amount"])
										
		elif effect["name"] == "AddSlimedToDiscard":
			for __ in range(effect["amount"]):
				slimed = spirecomm.spire.card.Card("Slimed", "Slimed", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL)
				self.discard_pile.append(slimed)
				
		elif effect["name"] == "AddDazedToDiscard":
			for __ in range(effect["amount"]):
				slimed = spirecomm.spire.card.Card("Dazed", "Dazed", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL)
				self.discard_pile.append(slimed)
				
		elif effect["name"] == "GainBurnToDiscard" or effect["name"] == "AddBurnToDiscard":
			for _ in range(effect["amount"]):
				self.discard_pile.append(spirecomm.spire.card.Card("Burn", "Burn", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
			1	
		elif effect["name"] == "GainBurn+ToDiscard" or effect["name"] == "AddBurn+ToDiscard":
			for _ in range(effect["amount"]):
				self.discard_pile.append(spirecomm.spire.card.Card("Burn+", "Burn+", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL, upgrades=1))
				
		elif effect["name"] == "GainBurnToDeck" or effect["name"] == "AddBurnToDeck":
			for _ in range(effect["amount"]):
				self.draw_pile.append(spirecomm.spire.card.Card("Burn", "Burn", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))	
		
		elif effect["name"] == "Sleep":
			pass # take one (1) snoozle
			
		elif effect["name"] == "Charge":
			pass # i'ma chargin' mah fireball!
			
		elif effect["name"] == "Split":
			for new_monster in effect["amount"]:
				m = spirecomm.spire.character.Monster(new_monster, new_monster, monster.current_hp,  monster.current_hp, 0, None, False, False)
				self.monsters.append(m)
				self.monsters.remove(monster)
		
		elif effect["name"] == "Escape":
			monster.is_gone = True
			
		elif effect["name"] == "Offensive Mode":
			monster.add_power("Mode Shift", 30 + monster.misc) # TODO account for ascension_level
			monster.misc += 10
		
		elif effect["name"] not in PASSIVE_EFFECTS:
			self.debug_log.append("WARN: Unknown effect " + effect["name"])
		
	# increment tracked count of moves in a row
	if str(monster) in self.tracked_state["monsters_last_attacks"] and self.tracked_state["monsters_last_attacks"][str(monster)][0] == monster.current_move:
		self.tracked_state["monsters_last_attacks"][str(monster)][1] += 1
	else:
		self.tracked_state["monsters_last_attacks"][str(monster)] = [monster.current_move, 1]
	
	
def apply_monsters_turn(self, monster):
	self.apply_start_of_turn_effects(monster)
			
	if monster.intents != {}: # we have correctly loaded intents JSON
	
		monster.current_move = self.get_monsters_move(monster)
						
		if monster.current_move is None:
			self.debug_log.append("ERROR: Could not determine " + monster.name + "\'s intent of " + str(monster.intent))
		else:
			self.apply_monster_effect(monster)
	
	if monster.intents == {} or monster.current_move is None:
		self.debug_log.append("WARN: unable to get intent for " + str(monster))
		# default behaviour: just assume the same move as the first turn of simulation
		if monster.intent.is_attack():
			if monster.move_adjusted_damage is not None:
				# are weak and vulnerable accounted for in default logic?
				for _ in range(monster.move_hits):
					unblocked_damage = self.use_attack(monster.move_base_damage, monster, self.player)
					self.debug_log.append("Taking " + str(unblocked_damage) + " damage from " + str(monster))
					
	monster.current_move = None # now that we used the move, clear it
	
		
		
def apply_end_of_player_turn_effects(self):

	# reset relics
	self.set_relic_counter("Kunai", 0)
	self.set_relic_counter("Shuriken", 0)
	self.set_relic_counter("Ornamental Fan", 0)
	self.set_relic_counter("Velvet Choker", 0)
	self.set_relic_counter("Letter Opener", 0)
	self.tracked_state["attacks_played_last_turn"] = self.tracked_state["attacks_played_this_turn"]
	self.tracked_state["attacks_played_this_turn"] = 0
	self.tracked_state["cards_played_last_turn"] = self.tracked_state["cards_played_this_turn"]
	self.tracked_state["cards_played_this_turn"] = 0
	self.tracked_state["skills_played_this_turn"] = 0
	self.tracked_state["powers_played_this_turn"] = 0
	self.tracked_state["necronomicon_triggered"] = False
	
	self.decrement_duration_powers(self.player)
	
	self.increment_relic("Stone Calendar")
	
	if self.player.has_power("Fire Breathing"):
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		amt = self.player.get_power_amount("Fire Breathing") * self.tracked_state["attacks_played_this_turn"]
		if amt > 0:
			for monster in available_monsters:
				self.apply_damage(amt, None, monster)
	
	if self.combat_round == 7 and self.has_relic("Stone Calendar"):
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for monster in available_monsters:
			self.apply_damage(52, None, monster)
			
	available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
	for monster in available_monsters:
		if monster.has_power("Poison"):
			self.apply_damage(monster.get_power_amount("Poison"), None, monster, ignores_block=True)
			monster.decrement_power("Poison")
		
	
	if self.player.block == 0 and self.has_relic("Orichalcum"):
		self.player.block += 6 # note, this happens before all other end of turn block gaining effects like frost orbs, metallicize, etc
		
	if not self.has_relic("Ice Cream"):
		self.player.energy = 0
		
	# Hand discarded
	for card in self.hand:
		for effect in card.effects:
			if effect["effect"] == "Regret":
				self.lose_hp(self.player, len(self.hand), from_card=True)
			if effect["effect"] == "Ethereal":
				self.hand.remove(card)
				self.exhaust_card(card)
				continue
			elif effect["effect"] == "SelfWeakened":
				self.apply_debuff(self.player, "Weakened", effect["amount"])
			elif effect["effect"] == "SelfFrail":
				self.apply_debuff(self.player, "Frail", effect["amount"])
			elif effect["effect"] == "SelfDamage":
				self.apply_damage(effect["amount"], None, self.player)
				
	if not self.has_relic("Runic Pyramid"):
		self.discard_pile += self.hand
		self.hand = []
		
	if self.has_relic("Nilry's Codex"):
		pass # TODO discovery
	
	for power in self.player.powers:
		if power.power_name == "Strength Down":
			self.apply_debuff(self.player, "Strength", -1 * power.amount)
			self.player.remove_power("Strength Down")
		elif power.power_name == "Dexterity Down":
			self.apply_debuff(self.player, "Dexterity", -1 * power.amount)
			self.player.remove_power("Dexterity Down")
		elif power.power_name == "Focus Down":
			self.apply_debuff(self.player, "Focus", -1 * power.amount)
			self.player.remove_power("Focus Down")
		elif power.power_name == "Plated Armor":
			self.add_block(self.player, power.amount)
		elif power.power_name == "Metallicize":
			self.add_block(self.player, power.amount)
		elif power.power_name == "Combust":
			self.lose_hp(self.player, 1, from_card=True)
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				monster.current_hp = max(monster.current_hp - power.amount, 0)
		elif power.power_name == "Regen":
			self.player.current_hp = min(self.player.current_hp + power.amount, self.player.max_hp)
			self.player.decrement_power(power.power_name)
		elif power.power_name == "DemonForm":
			character.add_power("Strength", power.amount)