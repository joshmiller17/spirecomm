
	# quick function for setting a discover action
	def discover(self, player_class, card_type="ALL", rarity="ALL", action="DiscoverAction", skip_available=False):
		self.screen_up = True
		self.screen_type = spirecomm.spire.screen.ScreenType.CardRewardScreen
		self.current_action = action
		
		generated_cards = []
		for _ in range(3):
			generated_cards.append(self.generate_card(player_class, card_type, rarity))
		
		self.screen = spirecomm.spire.screen.CardRewardScreen(cards=generated_cards,can_bowl=False, can_skip=skip_available)
		self.choice_list = [card.get_choice_str() for card in generated_cards]
		return self
			
			
	# used to simulate entropic brew
	def generate_random_potion(self, player_class=spirecomm.spire.character.PlayerClass.IRONCLAD):
		# fixme not sure if entropic brew can generate fruit juice
		possible_potions = [ 
		spirecomm.spire.potion.Potion("Ancient Potion", "Ancient Potion", True, True, False),
		spirecomm.spire.potion.Potion("Attack Potion", "Attack Potion", True, True, False),
		spirecomm.spire.potion.Potion("Block Potion", "Block Potion", True, True, False),
		spirecomm.spire.potion.Potion("Dexterity Potion", "Dexterity Potion", True, True, False),
		spirecomm.spire.potion.Potion("Essence of Steel", "Essence of Steel", True, True, False),
		spirecomm.spire.potion.Potion("Explosive Potion", "Explosive Potion", True, True, False),
		spirecomm.spire.potion.Potion("Fairy in a Bottle", "Fairy in a Bottle", False, True, False),
		spirecomm.spire.potion.Potion("Fear Potion", "Fear Potion", True, True, True),
		spirecomm.spire.potion.Potion("Fire Potion", "Fire Potion", True, True, True),
		spirecomm.spire.potion.Potion("Gambler's Brew", "Gambler's Brew", True, True, False),
		spirecomm.spire.potion.Potion("Liquid Bronze", "Liquid Bronze", True, True, False),
		spirecomm.spire.potion.Potion("Power Potion", "Power Potion", True, True, False),
		spirecomm.spire.potion.Potion("Regen Potion", "Regen Potion", True, True, False),
		spirecomm.spire.potion.Potion("Skill Potion", "Skill Potion", True, True, False),
		spirecomm.spire.potion.Potion("Smoke Bomb", "Smoke Bomb", True, True, False),
		spirecomm.spire.potion.Potion("Snecko Oil", "Snecko Oil", True, True, False),
		spirecomm.spire.potion.Potion("Speed Potion", "Speed Potion", True, True, False),
		spirecomm.spire.potion.Potion("Flex Potion", "Flex Potion", True, True, False),
		spirecomm.spire.potion.Potion("Strength Potion", "Strength Potion", True, True, False),
		spirecomm.spire.potion.Potion("Swift Potion", "Swift Potion", True, True, False),
		spirecomm.spire.potion.Potion("Weak Potion", "Weak Potion", True, True, True),
		]
	
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			possible_potions.append(spirecomm.spire.potion.Potion("Blood Potion", "Blood Potion", True, True, False))
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			possible_potions.append(spirecomm.spire.potion.Potion("Ghost In A Jar", "Ghost In A Jar", True, True, False))
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			possible_potions.append(spirecomm.spire.potion.Potion("Focus Potion", "Focus Potion", True, True, False))
		
		return random.choice(possible_potions)
		
		
	def generate_card(self, player_class, card_type="ALL", rarity="ALL"):
		# card_id, name, card_type, rarity, upgrades=0, has_target=False, cost=0, misc=0, is_playable=False, exhausts=False
	
		return card

		
	def generate_random_colorless_card(self, rare_only=False):
		cards = []
		
		
	
		return cards
		
	def generate_random_attack_card(self, player_class, rare_only=False):
		cards = []
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			pass # TODO
	
		return cards
	
	def generate_random_skill_card(self, player_class, rare_only=False):
		cards = []
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			pass # TODO
	
		return cards
	
	def generate_random_power_card(self, player_class, rare_only=False):
		cards = []
	
		if player_class == spirecomm.spire.character.PlayerClass.IRONCLAD:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.THE_SILENT:
			pass # TODO
		if player_class == spirecomm.spire.character.PlayerClass.DEFECT:
			pass # TODO
	
		return cards