from enum import Enum
import copy
import random
import math
import os
import spirecomm


# This helper file contains main simulation functions for a Game object to simulate actions
# generally the main logic for calling the workhorse functions


BUFFS = ["Ritual", "Strength", "Dexterity", "Incantation", "Enrage", "Metallicize", "SadisticNature", "Juggernaut", "DoubleTap", "DemonForm", "DarkEmbrace", "Brutality", "Berserk", "Rage", "Feel No Pain", "Flame Barrier", "Corruption", "Combust", "Fire Breathing", "Mayhem"]
DEBUFFS = ["Frail", "Vulnerable", "Weakened", "Entangled", "Shackles", "NoBlock", "No Draw", "Strength Down", "Dexterity Down", "Focus Down"]
PASSIVE_EFFECTS = ["Strike Damage", "Ethereal"] # these don't do anything by themselves
		
		
	# a test bed for checking our surroundings
	def debug_game_state(self):
		available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for monster in available_monsters:
			if monster.monster_id == "Lagavulin":
				self.debug_log.append("Lagavulin's powers: " + str([str(power) for power in monster.powers]))

	# logs the game state
	def print_state(self):
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				d.write(str(self))
				
				
	# logs a list of contents one line at a time with a newline at end
	# if a divider is specified, prints a line of this char before and after
	def print_to_log(self, contents, divider=""):
		if contents == "" or contents == []:
			return
		if not isinstance(contents, list):
			contents = [contents]
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				if divider != "":
					d.write(divider * 30 + "\n"
				d.write("\n".join([str(c) for c in contents] + "\n"))		
				if divider != "":
					d.write(divider * 30 + "\n"				
				
	def getPossibleActions(self):
		if self.game.tracked_state["possible_actions"] == None:
		
			possible_actions = [EndTurnAction()]
			available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				pass
				#monster.recognize_intents() # FIXME
			
			for potion in self.game.get_real_potions():
				if potion.requires_target:
					for monster in available_monsters:
						possible_actions.append(PotionAction(True, potion=potion, target_monster=monster))
				else:
					possible_actions.append(PotionAction(True, potion=potion))
					
			for card in self.game.hand:
				if len(available_monsters) == 0 and card.type != spirecomm.spire.card.CardType.POWER:
					continue
				if card.cost > self.game.player.energy:
					continue
				if card.has_target:
					for monster in available_monsters:
						possible_actions.append(PlayCardAction(card=card, target_monster=monster))
				else:
					possible_actions.append(PlayCardAction(card=card))
			
			self.print_to_log(["Possible Actions:"] + possible_actions, divider=" ")

			self.game.tracked_state["possible_actions"] = possible_actions
				
		return self.game.tracked_state["possible_actions"]
		
	
	
	# Handler that calls the appropriate simulate_action function and returns a new state
	def takeAction(self, action, from_real=False):
	
		if self.game.in_combat and not self.game.tracked_state["registered_start_of_combat"]:
			self.game.apply_start_of_combat_effects()
			self.game.tracked_state["registered_start_of_combat"] = True
	
		if from_real:
			self.game.tracked_state["is_simulation"] = False
	
		self.game.debug_game_state()
	
		self.debug_log.append("Simulating taking action: " + str(action))
		#self.debug_log.append("Combat round: " + str(self.combat_round))
	
		self.print_to_log("Simulating taking action: " + str(action))
		
		new_state = copy.deepcopy(self.game)
		new_state.tracked_state["possible_actions"] = None
		new_state.original_state = self.game
		new_state.state_id += 1
		
		new_state.tracked_state["just_reshuffled"] = False
		
		if action.command.startswith("end") and not self.game.screen_up:
			return new_state.simulate_end_turn(action)
		elif action.command.startswith("potion") and not self.game.screen_up:
			# assumes we have this potion, will throw an error if we don't I think
			return new_state.simulate_potion(action)
		elif action.command.startswith("play") and not self.game.screen_up:
			return new_state.simulate_play(action)
		elif action.command.startswith("state"):
			return new_state
		elif action.command.startswith("choose") and self.game.screen_up and new_state.current_action == "DiscoveryAction":
			return new_state.simulate_discovery(action)
		elif action.command.startswith("choose") and self.game.screen_up and new_state.current_action == "ExhaustAction":
			return new_state.simulate_exhaust(action)
		elif action.command.startswith("choose") and self.game.screen_up and new_state.current_action == "DiscardPileToTopOfDeckAction":
			return new_state.simulate_headbutt(action)
		elif action.command.startswith("choose") and self.game.screen_up and new_state.current_action == "PutOnDeckAction":
			return new_state.simulate_hand_to_topdeck(action)
		elif action.command.startswith("choose") and self.game.screen_up and new_state.current_action == "ArmamentsAction":
			return new_state.simulate_upgrade(action)
		elif action.command.startswith("choose") and self.game.screen_up and new_state.current_action == "DualWieldAction": # FIXME?
			return new_state.simulate_dual_wield(action)
		elif action.command.startswith("choose") and self.game.screen_up and new_state.current_action == "ExhumeAction": # FIXME?
			return new_state.simulate_exhume(action)
		elif action.command.startswith("choose") and self.game.screen_up and new_state.current_action == "ForethoughtAction": # FIXME?
			return new_state.simulate_forethought(action)
		else:
			raise Exception("Chosen simulated action is not a valid combat action in the current state: " + str(action) + ", " + str(self.game.screen) + " (" + str(self.game.screen_type) + ") " + ("[UP]" if self.game.screen_up else ""))

	
	# Returns a new state
	def simulate_end_turn(self, action):
		
		self.check_intents()
		
		# TODO consider retaining cards (well-laid plans) or runic pyramid
		
		# end player's turn
		self.apply_end_of_player_turn_effects()
		
		# MONSTER TURN / MONSTERS ATTACK
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		for monster in available_monsters:
			if monster is None:
				self.debug_log.append("WARN: Monster is None")
				continue
				
			self.apply_monsters_turn(monster)
				
		for monster in available_monsters:
			self.apply_end_of_turn_effects(monster)

		
		self.player.energy += 3
		for relic in ["Coffee Dripper", "Mark of Pain", "Sozu", "Ectoplasm", "Cursed Key", "Runic Dome", "Philosopher's Stone", "Fusion Hammer"]:
			if self.has_relic(relic):
				self.player.energy += 1
		if self.player.has_power("Berserk"):
			self.player.energy += 1
			
		self.combat_round += 1
		self.apply_start_of_turn_effects(self.player)

		# Draw new hand - TODO consider relic modifiers and known information
		hand_size = 5
		if self.has_relic("Snecko Eye"):
			hand_size += 2
		while len(self.hand) < hand_size:
			self.draw_card()
			
		self.print_to_log(self.debug_log)
			
		self.tracked_state["is_simulation"] = True
		
		return self
				
		
	def simulate_discovery(self, action):
		self.choice_list = []
		self.current_action = None
		
		# TODO actually discover the card
	
		return self
		
	def simulate_exhaust(self, action):
		self.hand.remove(action.card)
		self.exhaust_card(action.card)
		return self
		
	def simulate_headbutt(self, action):
		card = action.cards[0]
		self.discard_pile.remove(card)
		self.draw_pile.insert(0, card)
		return self
		
	def simulate_hand_to_topdeck(self, action):
		self.hand.remove(action.card)
		self.draw_pile.insert(0, action.card)
		return self
		
	def simulate_upgrade(self, action):
		action.card.upgrade()
		return self

	def simulate_exhume(self, action):
		card = action.cards[0]
		self.exhaust_pile.remove(card)
		self.hand.append(card)
		return self
		
	def simulate_dual_wield(self, action):
		# TODO how to know whether it's dualwield+?
		
	
		return self
		
	def simulate_forethought(self, action):
		# TODO
		
	
		return self
		
		
	# Returns a new state
	def simulate_potion(self, action):
	
		self.potions.remove(action.potion) # fixme? might need to match on name rather than ID
		self.potions.append(spirecomm.spire.potion.Potion("Potion Slot", "Potion Slot", False, False, False))
		
		if action.potion.name == "Ancient Potion":
			self.player.add_power("Artifact", 1)
		
		elif action.potion.name == "Attack Potion":
			# TODO
			pass
		
		elif action.potion.name == "Block Potion":
			self.add_block(self.player, 12)
		
		elif action.potion.name == "Blood Potion":
			hp_gained = int(math.ceil(self.player.max_hp * 0.25))
			new_hp = min(self.player.max_hp, self.player.current_hp + hp_gained)
			self.player.current_hp = new_hp
		
		elif action.potion.name == "Dexterity Potion":
			self.player.add_power("Dexterity", 2)
		
		elif action.potion.name == "Energy Potion":
			self.player.energy += 2
		
		elif action.potion.name == "Entropic Brew":
			for i in range(len(self.potions)):
				if self.potions[i].potion_id == "Potion Slot":
					self.potions[i] = self.generate_random_potion()
		
		elif action.potion.name == "Essence of Steel":
			self.player.add_power("Plated Armor", 4)
		
		elif action.potion.name == "Explosive Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				self.apply_damage(10, None, monster)
		
		# TODO Fairy in a Bottle is not usable but should be considered in game state
		
		elif action.potion.name == "Fear Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				if monster == action.target_monster:
					monster.add_power("Vulnerable", 3)
		
		elif action.potion.name == "Fire Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				if monster == action.target_monster:
					self.apply_damage(20, None, monster)
		
		elif action.potion.name == "Focus Potion":
			self.player.add_power("Focus", 2)
		
		elif action.potion.name == "Fruit Juice":
			self.player.max_hp += 5
			self.player.current_hp += 5
		
		elif action.potion.name == "Gambler's Brew":
			# TODO
			pass
			
		elif action.potion.name == "Ghost In A Jar":
			self.player.add_power("Intangible", 1)
		
		elif action.potion.name == "Liquid Bronze":
			self.player.add_power("Thorns", 3)
		
		elif action.potion.name == "Poison Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				if monster == action.target_monster:
					monster.add_power("Poison", 6)
		
		elif action.potion.name == "Power Potion":
			# TODO
			pass
			
		elif action.potion.name == "Regen Potion":
			self.player.add_power("Regen", 5)
		
		elif action.potion.name == "Skill Potion":
			# TODO
			pass
		
		elif action.potion.name == "Smoke Bomb":
			if self.blackboard.game.room_type != "MonsterRoomBoss":
				self.in_combat = False
		
		elif action.potion.name == "Snecko Oil":
			self.player.add_power("Confused")
			self.draw_card(3)
		
		elif action.potion.name == "Speed Potion":
			self.player.add_power("Dexterity", 5)
			self.player.add_power("Dexterity Down", 5)
		
		elif action.potion.name == "Flex Potion":
			self.player.add_power("Strength", 5)
			self.player.add_power("Strength Down", 5)
		
		elif action.potion.name == "Strength Potion":
			self.player.add_power("Strength", 2)
		
		elif action.potion.name == "Swift Potion":
			self.draw_card(3)
		
		elif action.potion.name == "Weak Potion":
			available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			for monster in available_monsters:
				if monster == action.target_monster:
					monster.add_power("Weakened", 3)
		
		else:
			self.debug_log.append("ERROR: No handler for potion: " + str(action.potion))
			
			
		self.print_to_log(self.debug_log)
		
		self.tracked_state["is_simulation"] = True
		
		return self
		
		
	# Returns a new state
	def simulate_play(self, action, free_play=False, from_deck=False):
	
		if not action.card.loadedFromJSON:
			raise Exception("Card not loaded from JSON: " + str(action.card.name))
			
		if action.card.type != spirecomm.spire.card.CardType.CURSE:
			# Velvet Choker does count copies of free_play cards, but allows them to go off past 6
			self.increment_relic("Velvet Choker") # doesn't count Blue Candle
			
		self.tracked_state["cards_played_this_turn"] += 1
		
		# Fix for IDs not matching
		found = False # test
		possible_cards = self.hand
		if from_deck:
			possible_cards = self.draw_pile
		for c in possible_cards:
			if action.card == c:
				action.card = c
				found = True 
		if not found:
			raise Exception("Could not find action card " + action.card.get_id_str() + " in hand " + str([card.get_id_str() for card in possible_cards]))
		
		if not free_play:
			# move card to discard
			self.player.energy -= action.card.cost
			self.hand.remove(action.card)
			if action.card.type != spirecomm.spire.card.CardType.POWER: # powers just get removed from play
				self.discard_pile.append(action.card)
		
		available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]

			
		X_cost = -1
		if "X" in [effect["effect"] for effect in action.card.effects]:
			X_cost = self.player.energy
			if self.has_relic("Chemical X"):
				X_cost += 2
			self.player.energy = 0
			
			
		effect_targets = []
		for effect in action.card.effects:
			
			# Pick target(s)
			if effect["target"] == "self":
				effect_targets = [self.player]
			elif effect["target"] == "one":
				for monster in available_monsters:
					if action.target_monster is None:
						raise Exception("Action expects a target; check " + str(action.card.get_clean_name()) + ".json for potential error.")
					if action.target_monster == monster:
						effect_targets = [monster]
						break
			elif effect["target"] == "all":
				effect_targets = available_monsters
			elif effect["target"] == "random":
				effect_targets = [random.choice(available_monsters)]
				
			
			# Do effect
			for target in effect_targets:
			
				effects_that_can_target_unavailable = ["Feed", "RitualDagger", "Greed"]
			
				available_monsters = [monster for monster in self.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
				if target is not self.player and target not in available_monsters and effect["effect"] not in effects_that_can_target_unavailable:
					continue # we probably killed it, just ignore remaining effects
			
				if effect["effect"] == "Block":
					real_amount = effect["amount"]
					real_amount += target.get_power_amount("Dexterity")
					if target.has_power("Frail"):
						real_amount = int(math.floor(real_amount - (0.25 * real_amount)))
					self.add_block(target, real_amount)
					
				elif effect["effect"] == "Entrench":
					self.add_block(target, "Entrench")
					
				elif effect["effect"] == "Damage":
					base_damage = effect["amount"]
					if action.card.name.startswith("Searing Blow"):
						upgrades = action.card.upgrades
						base_damage = math.ceil((upgrades * ((upgrades + 7) / 2)) + 12)
					if action.card.name == "Ritual Dagger" or action.card.name == "Rampage":
						base_damage += action.card.misc
					
					for effect in action.card.effects:
						if effect["effect"] == "Strike Damage":
							cards = self.draw_pile + self.discard_pile + self.hand
							for card in cards:
								if "Strike" in card.name:
									base_damage += effect["amount"]
						if effect["effect"] == "Bonus Strength Damage":
							base_damage += effect["amount"] * self.player.get_power_amount("Strength")
					
					self.use_attack(base_damage, self.player, target)
					
				elif effect["effect"] == "XDamage":
					if X_cost < 0:
						raise Exception("Non X-cost card using an X-cost ability")
					for _ in range(X_cost):
						base_damage = effect["amount"]
						self.use_attack(base_damage, self.player, target)
					
				elif effect["effect"] == "Corruption":
					cards = self.draw_pile + self.discard_pile + self.hand
					for card in cards:
						if card.type == spirecomm.spire.card.CardType.SKILL:
							card.cost = 0
					self.player.add_power(effect["effect"], effect["amount"])
					
				elif effect["effect"] == "Armaments":
					upgradable_cards = self.get_upgradable_cards(self.hand)
					if len(upgradable_cards) == 0:
						pass
					elif len(upgradable_cards) == 1:
						action = CardSelectAction(cards=upgradable_cards)
						self.simulate_upgrade(action)
					else:
						self.screen = spirecomm.spire.screen.HandSelectScreen(cards=upgradable_cards, selected=[], num_cards=1, can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.HAND_SELECT
						self.current_action = "ArmamentsAction"
						self.choice_list = [card.get_choice_str() for card in upgradable_cards]
					
				elif effect["effect"] == "Armaments+":
					for card in self.hand:
						card.upgrade()
						
				elif effect["effect"] == "HandToDeck":
					if len(self.hand) == 0:
						pass
					elif len(self.hand) == 1:
						action = CardSelectAction(cards=self.hand)
						self.simulate_hand_to_topdeck(action)
					else:
						self.screen = spirecomm.spire.screen.HandSelectScreen(cards=self.hand, selected=[], num_cards=effect["amount"], can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.HAND_SELECT
						self.current_action = "PutOnDeckAction"
						self.choice_list = [card.get_choice_str() for card in self.hand]
						
				elif effect["effect"] == "Headbutt":
					if len(self.discard_pile) == 0:
						pass
					elif len(self.discard_pile) == 1:
						action = CardSelectAction(cards=self.discard_pile)
						self.simulate_headbutt(action)
					else:
						self.screen = spirecomm.spire.screen.GridSelectScreen(cards=self.discard_pile, selected_cards=[], num_cards=1, can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.GRID_SELECT
						self.current_action = "PutOnDeckAction"
						self.choice_list = [card.get_choice_str() for card in self.discard_pile]
						
				elif effect["effect"] == "Exhume":
					if len(self.exhaust_pile) == 0:
						pass
					elif len(self.exhaust_pile) == 1:
						action = CardSelectAction(cards=self.exhaust_pile)
						self.simulate_exhume(action)
					else:
						self.screen = spirecomm.spire.screen.GridSelectScreen(cards=self.hand, selected_cards=[], num_cards=1, can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.GRID_SELECT
						self.current_action = "ExhumeAction"
					
					
				elif effect["effect"] in BUFFS:
					self.player.add_power(effect["effect"], effect["amount"])
						
				elif effect["effect"] in DEBUFFS:
					self.apply_debuff(target, effect["effect"], effect["amount"])
					
				elif effect["effect"] == "Block as Damage":
					base_damage = self.player.block
					self.use_attack(base_damage, self.player, target)
					
				elif effect["effect"] == "MindBlast":
					base_damage = len(self.draw_pile)
					self.use_attack(base_damage, self.player, target)
					
				elif effect["effect"] ==  "Violence":
					available_attacks = [c for c in self.draw_pile if c.type == spirecomm.spire.card.CardType.ATTACK]
					for _ in range(min(effect["amount"], len(available_attacks))):
						selected_card = random.choice(available_attacks)
						self.hand.append(selected_card)
						self.draw_pile.remove(selected_card)
						available_attacks.remove(selected_card)
						
				elif effect["effect"] == "Heal":
					self.gain_hp(target, effect["amount"])
					
				elif effect["effect"] == "Energy":
					self.player.energy += effect["amount"]
					
				elif effect["effect"] == "Dropkick":
					if target.has_power("Vulnerable"):
						self.player.energy += 1 
						self.draw_card()
					
				elif effect["effect"] == "Anger":
					new_card = copy.deepcopy(action.card)
					new_card.uuid = ""
					self.discard_pile.append(new_card)
					
				elif effect["effect"] == "Rampage":
					action.card.misc += effect["amount"]				
					
				
				elif effect["effect"] == "SpotWeakness":
					if target.intent.is_attack():
						self.player.add_power("Strength", effect["amount"])
						
				elif effect["effect"] == "SecondWind":
					hand = self.hand
					for card in hand:
						if card.type != spirecomm.spire.card.CardType.ATTACK:
							self.exhaust_card(card)
							self.add_block(self.player, effect["amount"])
						
						
				elif effect["effect"] == "ExhaustAllNonAttacks":
					hand = self.hand
					for card in hand:
						if card.type != spirecomm.spire.card.CardType.ATTACK:
							self.exhaust_card(card)
					
				elif effect["effect"] == "FiendFire":
					hand = self.hand
					for card in hand:
						self.hand.remove(card)
						self.exhaust_card(card)
						self.use_attack(effect["amount"], self.player, target)
						
				elif effect["effect"] == "GainBurnToDiscard":
					for _ in range(effect["amount"]):
						self.discard_pile.append(spirecomm.spire.card.Card("Burn", "Burn", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
						
				elif effect["effect"] == "DazedToDraw":
					for _ in range(effect["amount"]):
						self.draw_pile.append(spirecomm.spire.card.Card("Dazed", "Dazed", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
						
				elif effect["effect"] == "WoundToHand":
					for _ in range(effect["amount"]):
						if len(self.hand) >= 10:
							self.discard_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
						else:
							self.hand.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
							
				elif effect["effect"] == "WoundToDeck":
					for _ in range(effect["amount"]):
						self.draw_pile.append(spirecomm.spire.card.Card("Wound", "Wound", spirecomm.spire.card.CardType.STATUS, spirecomm.spire.card.CardRarity.SPECIAL))
					
				elif effect["effect"] == "Reaper":
					base_damage = effect["amount"]
					unblocked_damage = self.use_attack(base_damage, self.player, target)
					self.gain_hp(unblocked_damage)
					
				elif effect["effect"] == "LimitBreak":
					target.add_power("Strength", target.get_power_amount("Strength"))
					
				elif effect["effect"] == "Feed":
					if monster.current_hp <= 0 and not monster.half_dead and not monster.has_power("Minion"):
						self.player.max_hp += effect["amount"]
						self.player.current_hp += effect["amount"]
						
				elif effect["effect"] == "Impatience":
					no_attacks = True
					for card in self.hand:
						if card.type == spirecomm.spire.card.CardType.ATTACK:
							no_attacks = False
							break
					if no_attacks:
						self.draw_card(2)
						
				elif effect["effect"] == "Greed":
					if monster.current_hp <= 0 and not monster.half_dead and not monster.has_power("Minion"):
						self.player.gain_gold(20)
					
				elif effect["effect"] == "RitualDagger":
					if monster.current_hp <= 0 and not monster.half_dead:
						action.card.misc += effect["amount"]
						
				elif effect["effect"] == "Havoc":
					havoc_card = self.draw_pile.pop(0)
					play_action = self.get_random_play(havoc_card)
					self.simulate_play(play_action, from_deck=True)
					self.discard_pile.remove(havoc_card)
					self.exhaust_card(havoc_card)
					
				elif effect["effect"] == "Apotheosis":
					cards = self.draw_pile + self.discard_pile + self.hand
					for card in cards:
						if card is not action.card:
							card.upgrade()
							
				elif effect["effect"] == "Lose HP":
					self.lose_hp(self.player, effect["amount"], from_card=True)
					
				elif effect["effect"] == "DiscardToDraw":
					self.reshuffle_deck()
					
				elif effect["effect"] == "Exhaust":
					self.discard_pile.remove(action.card)
					self.exhaust_card(action.card)
				elif effect["effect"] == "ExhaustRandom":
					exhausted_card = random.choice(self.hand)
					self.hand.remove(exhausted_card)
					self.exhaust_card(exhausted_card)
					
				elif effect["effect"] == "ExhaustSelect":
					if len(self.hand) == 0:
						pass
					elif len(self.hand) == 1:
						action = CardSelectAction(cards=self.hand)
						self.simulate_exhaust(action)
					else:
						self.screen = spirecomm.spire.screen.HandSelectScreen(cards=self.hand, selected=[], num_cards=effect["amount"], can_pick_zero=False)
						self.screen_up = True
						self.screen_type = spirecomm.spire.screen.ScreenType.HAND_SELECT
						self.current_action = "ExhaustAction"
					
				elif effect["effect"] == "Draw":
					self.draw_card(draw=effect["amount"])
						
				elif effect["effect"] == "Madness":
					selected_card = random.choice([c for c in self.hand if c.cost > 0])
					selected_card.cost = 0
					
				elif effect["effect"] not in PASSIVE_EFFECTS:
					self.debug_log.append("WARN: Unknown effect " + effect["effect"])
					
					
					
					
		if action.card.type == spirecomm.spire.card.CardType.ATTACK:
	
			self.tracked_state["attacks_played_this_turn"] += 1
			if self.tracked_state["attacks_played_this_turn"] == 1 and self.tracked_state["skills_played_this_turn"] > 0 and self.tracked_state["powers_played_this_turn"] > 0 and self.has_relic("Orange Pellets"):
				self.remove_all_debuffs()
		
			if self.player.has_power("Rage"):
				self.add_block(self.player, self.player.get_power_amount("Rage"))
		
			fan = self.get_relic("Ornamental Fan")
			if fan:
				fan.counter += 1
				if fan.counter >= 3:
					self.set_relic_counter("Ornamental Fan", 0)
					self.add_block(self.player, 4)
					
			kunai = self.get_relic("Kunai")
			if kunai:
				kunai.counter += 1
				if kunai.counter >= 3:
					self.set_relic_counter("Kunai", 0)
					self.player.add_power("Dexterity", 1)
			
			shuriken = self.get_relic("Shuriken")
			if shuriken:
				shuriken.counter += 1
				if shuriken.counter >= 3:
					self.set_relic_counter("Shuriken", 0)
					self.player.add_power("Strength", 1)
			
			self.increment_relic("Pen Nib")
			
			nunchaku = self.get_relic("Nunchaku")
			if nunchaku:
				nunchaku.counter += 1
				if nunchaku.counter >= 10:
					self.set_relic_counter("Nunchaku", 0)
					self.player.energy += 1
			
			if self.player.has_power("DoubleTap"):
				self.player.decrement_power("DoubleTap")
				self.simulate_play(action, free_play=True)
			
		if action.card.cost >= 2 and self.has_relic("Necronomicon") and not self.tracked_state["necronomicon_triggered"]:
			self.tracked_state["necronomicon_triggered"] = True
			self.simulate_play(action, free_play=True)
				
				
				
		if action.card.type == spirecomm.spire.card.CardType.SKILL:
		
			self.tracked_state["skills_played_this_turn"] += 1
			if self.tracked_state["skills_played_this_turn"] == 1 and self.tracked_state["attacks_played_this_turn"] > 0 and self.tracked_state["powers_played_this_turn"] > 0 and self.has_relic("Orange Pellets"):
				self.remove_all_debuffs()
	
			letter = self.get_relic("Letter Opener")
			if letter:
				letter.counter += 1
				if letter.counter >= 3:
					self.set_relic_counter("Letter Opener", 0)
					for monster in available_monsters:
						self.apply_damage(5, None, monster)
		
			for monster in available_monsters:
				if monster.has_power("Enrage"):
					monster.add_power("Strength", monster.get_power_amount("Enrage"))

			if self.player.has_power("Corruption"):
				self.discard_pile.remove(exhausted_card) # FIXME if might not have gone to discard
				self.exhaust_card(action.card)
			
		if action.card.type == spirecomm.spire.card.CardType.POWER:
		
			self.tracked_state["powers_played_this_turn"] += 1
			if self.tracked_state["powers_played_this_turn"] == 1 and self.tracked_state["attacks_played_this_turn"] > 0 and self.tracked_state["skills_played_this_turn"] > 0 and self.has_relic("Orange Pellets"):
				self.remove_all_debuffs()
		
			if self.has_relic("Mummified Hand"):
				selected_card = random.choice(self.hand)
				while selected_card.cost == 0: #or selected_card.type == spirecomm.spire.card.CardType.CURSE (should be covered by cost)
					selected_card = random.choice(self.hand)
				selected_card.cost = 0
			
			
		for card in self.hand:
			for effect in card.effects:
				if effect["effect"] == "Pain":
					self.lose_hp(self.player, 1, from_card=True)
						
		if self.hand == [] and self.has_relic("Unceasing Top"):
			self.draw_card()
						
		
		self.check_intents()
					
			
		self.print_to_log(self.debug_log)
			
		self.tracked_state["is_simulation"] = True
			
		return self