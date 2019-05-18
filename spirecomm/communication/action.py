from spirecomm.spire.screen import ScreenType, RewardType


class Action:
	"""A base class for an action to take in Slay the Spire"""

	def __init__(self, command="state", requires_game_ready=True):
		self.command = command
		self.requires_game_ready = requires_game_ready

	def can_be_executed(self, coordinator):
		"""Indicates whether the given action can currently be executed, given the coordinator's state

		:param coordinator: The coordinator which will be used to execute the action
		:return: True if the action can currently be executed
		":rtype: boolean
		"""
		if self.requires_game_ready:
			return coordinator.game_is_ready
		else:
			return True

	def execute(self, coordinator):
		"""Given the coordinator's current state, execute the given action

		:param coordinator: The coordinator which will be used to execute the action
		:return: None
		"""
		coordinator.send_message(self.command)
		
	def __str__(self):
		return "[Default Action] {}".format(self.command)


class PlayCardAction(Action):
	"""An action to play a specified card from your hand"""

	def __init__(self, card=None, card_index=-1, target_monster=None, target_index=None):
		super().__init__("play")
		self.card = card
		self.card_index = card_index
		self.target_index = target_index
		self.target_monster = target_monster

	def execute(self, coordinator):
		if self.card is not None:
			self.card_index = coordinator.last_game_state.hand.index(self.card)
		if self.card_index == -1:
			raise Exception("Specified card for CardAction is not in hand")
		hand_card_index = self.card_index + 1
		if self.target_monster is not None:
			self.target_index = self.target_monster.monster_index
		if self.target_index is None:
			coordinator.send_message("{} {}".format(self.command, hand_card_index))
		else:
			coordinator.send_message("{} {} {}".format(self.command, hand_card_index, self.target_index))

		def __str__(self):
			return "[Play Action] {} {} on {} {}".format(self.card, self.card_index, self.target_index, self.target_monster)
		

class PotionAction(Action):
	"""An action to use or discard a selected potion"""

	def __init__(self, use, potion=None, potion_index=-1, target_monster=None, target_index=None):
		super().__init__("potion")
		self.use = use
		self.potion = potion
		self.potion_index = potion_index
		self.target_monster = target_monster
		self.target_index = target_index

	def execute(self, coordinator):
		if self.potion is not None:
			self.potion_index = coordinator.last_game_state.potions.index(self.potion)
		if self.potion_index == -1:
			raise Exception("Specified potion for PotionAction is not available")
		arguments = [self.command]
		if self.use:
			arguments.append("use")
		else:
			arguments.append("discard")
		arguments.append(str(self.potion_index))
		if self.target_monster is not None:
			self.target_index = self.target_monster.monster_index
		if self.target_index is not None:
			arguments.append(str(self.target_index))
		coordinator.send_message(" ".join(arguments))
		
	def __str__(self):
		return "[Potion Action] use {} potion {} {} on {} {}".format(self.use, self.potion, self.potion_index, self.target_monster, self.target_index)


class EndTurnAction(Action):
	"""An action to end your turn"""

	def __init__(self):
		super().__init__("end")
		
	def __str__(self):
		return "[End Turn Action]"


class ProceedAction(Action):
	"""An action to use the CommunicationMod 'Proceed' command"""

	def __init__(self):
		super().__init__("proceed")
		
	def __str__(self):
		return "[Proceed Action]"


class CancelAction(Action):
	"""An action to use the CommunicationMod 'Cancel' command"""

	def __init__(self):
		super().__init__("cancel")
		
	def __str__(self):
		return "[Cancel Action]"


class ChooseAction(Action):
	"""An action to use the CommunicationMod 'Choose' command"""

	def __init__(self, choice_index=0, name=None):
		super().__init__("choose")
		self.choice_index = choice_index
		self.name = name

	def execute(self, coordinator):
		if self.name is not None:
			coordinator.send_message("{} {}".format(self.command, self.name))
		else:
			coordinator.send_message("{} {}".format(self.command, self.choice_index))

	def __str__(self):
		return "[Choose Action] {} {}".format(self.choice_index, self.name)

class ChooseShopkeeperAction(ChooseAction):
	"""An action to open the shop on a shop screen"""

	def __init__(self):
		super().__init__(name="shop")
		
	def __str__(self):
		return "[Shop Action]" + super().__str__()


class OpenChestAction(ChooseAction):
	"""An action to open a chest on a chest screen"""

	def __init__(self):
		super().__init__(name="open")
		
	def __str__(self):
		return "[Chest Action (Open)]" + super().__str__()


class BuyCardAction(ChooseAction):
	"""An action to buy a card in a shop"""

	def __init__(self, card):
		super().__init__(name=card.name)
		
	def __str__(self):
		return "[Buy Card Action]" + super().__str__()


class BuyPotionAction(ChooseAction):
	"""An action to buy a potion in a shop. Currently, buys the first available potion of the same name."""

	def __init__(self, potion):
		super().__init__(name=potion.name)

	def execute(self, coordinator):
		if coordinator.game.are_potions_full():
			raise Exception("Cannot buy potion because potion slots are full.")
		super().execute(coordinator)
		
	def __str__(self):
		return "[Buy Potion Action]" + super().__str__()


class BuyRelicAction(ChooseAction):
	"""An action to buy a relic in a shop"""

	def __init__(self, relic):
		super().__init__(name=relic.name)
		
	def __str__(self):
		return "[Buy Relic Action]" + super().__str__()


class BuyPurgeAction(Action):
	"""An action to buy a card removal at a shop"""

	def __init__(self, card_to_purge=None):
		super().__init__()
		self.card_to_purge = card_to_purge

	def execute(self, coordinator):
		if coordinator.last_game_state.screen_type != ScreenType.SHOP_SCREEN:
			raise Exception("BuyPurgeAction is only available on a Shop Screen")
		coordinator.add_action_to_queue(ChooseAction(name="purge"))
		if self.card_to_purge is not None:
			coordinator.add_action_to_queue(CardSelectAction([self.card_to_purge]))
			
	def __str__(self):
		return "[Buy Purge Action]" + super().__str__()


class EventOptionAction(ChooseAction):
	"""An action to choose an event option"""

	def __init__(self, option):
		super().__init__(choice_index=option.choice_index)
		
	def __str__(self):
		return "[Event Option Action]" + super().__str__()


class RestAction(ChooseAction):
	"""An action to choose a rest option at a rest site"""

	def __init__(self, rest_option):
		super().__init__(name=rest_option.name)
		
	def __str__(self):
		return "[Rest Action]" + super().__str__()


class CardRewardAction(ChooseAction):
	"""An action to choose a card reward, or use Singing Bowl"""

	def __init__(self, card=None, bowl=False):
		if bowl:
			name = "bowl"
		elif card is not None:
			name = card.name
		else:
			raise Exception("Must provide a card for CardRewardAction if not choosing the Singing Bowl")
		super().__init__(name=name)
		
	def __str__(self):
		return "[Card Reward Action]" + super().__str__()


class CombatRewardAction(ChooseAction):
	"""An action to choose a combat reward"""

	def __init__(self, combat_reward):
		self.combat_reward = combat_reward
		super().__init__()

	def execute(self, coordinator):
		if coordinator.last_game_state.screen_type != ScreenType.COMBAT_REWARD:
			raise Exception("CombatRewardAction is only available on a Combat Reward Screen.")
		reward_list = coordinator.last_game_state.screen.rewards
		if self.combat_reward not in reward_list:
			raise Exception("Reward is not available: {}".format(self.combat_reward.reward_type))
		if self.combat_reward.reward_type == RewardType.POTION and coordinator.last_game_state.are_potions_full():
			raise Exception("Cannot choose potion reward with full potion slots.")
		self.choice_index = reward_list.index(self.combat_reward)
		super().execute(coordinator)
		
	def __str__(self):
		return "[Combat Reward Action]" + super().__str__()


class BossRewardAction(ChooseAction):
	"""An action to choose a boss relic"""

	def __init__(self, relic):
		super().__init__(name=relic.name)
		
	def __str__(self):
		return "[Boss Reward Action]" + super().__str__()


class OptionalCardSelectConfirmAction(Action):
	"""An action to click confirm on a hand or grid select screen, only if available"""

	def __init__(self):
		super().__init__()

	def execute(self, coordinator):
		screen_type = coordinator.last_game_state.screen_type
		if screen_type == ScreenType.HAND_SELECT:
			coordinator.add_action_to_queue(ProceedAction())
		elif screen_type == ScreenType.GRID and coordinator.last_game_state.screen.confirm_up:
			coordinator.add_action_to_queue(ProceedAction())
		else:
			coordinator.add_action_to_queue(StateAction())
			
	def __str__(self):
		return "[Optional Card Select Confirm Action]"


class CardSelectAction(Action):
	"""An action to choose the selected cards on a hand or grid select screen"""

	def __init__(self, cards):
		self.cards = cards
		super().__init__()

	def execute(self, coordinator):
		screen_type = coordinator.last_game_state.screen_type
		if screen_type not in [ScreenType.HAND_SELECT, ScreenType.GRID]:
			raise Exception("CardSelectAction is only available on a Hand Select or Grid Select Screen.")
		num_selected_cards = len(coordinator.last_game_state.screen.selected_cards)
		num_remaining_cards = coordinator.last_game_state.screen.num_cards - num_selected_cards
		available_cards = coordinator.last_game_state.screen.cards
		if screen_type == ScreenType.HAND_SELECT and len(self.cards) > num_remaining_cards:
			raise Exception("Too many cards selected for CardSelectAction (provided {}, max {})".format(len(self.cards), num_remaining_cards))
		elif screen_type == ScreenType.GRID and len(self.cards) != num_remaining_cards:
			raise Exception("Wrong number of cards selected for CardSelectAction (provided {}, need {})".format(len(self.cards), num_remaining_cards))
		chosen_indices = []
		for card in self.cards:
			if card not in available_cards:
				raise Exception("Card {} is not available in the Hand Select Screen".format(card.name))
			else:
				chosen_indices.append(available_cards.index(card))
		chosen_indices.sort(reverse=True)
		for index in chosen_indices:
			coordinator.add_action_to_queue(ChooseAction(choice_index=index))
		coordinator.add_action_to_queue(OptionalCardSelectConfirmAction())
		
	def __str__(self):
		return "[Card Select Action]"


class ChooseMapNodeAction(ChooseAction):
	"""An action to choose a map node, other than the boss"""

	def __init__(self, node):
		self.node = node
		super().__init__()

	def execute(self, coordinator):
		if coordinator.last_game_state.screen_type != ScreenType.MAP:
			raise Exception("MapChoiceAction is only available on a Map Screen")
		next_nodes = coordinator.last_game_state.screen.next_nodes
		if self.node not in next_nodes:
			raise Exception("Node {} is not available to choose.".format(self.node))
		self.choice_index = next_nodes.index(self.node)
		super().execute(coordinator)
		
	def __str__(self):
		return "[Choose Map Action] {}".format(self.node) + super().__str__()


class ChooseMapBossAction(ChooseAction):
	"""An action to choose the boss map node"""

	def __init__(self):
		super().__init__()

	def execute(self, coordinator):
		if coordinator.last_game_state.screen_type != ScreenType.MAP:
			raise Exception("ChooseMapBossAction is only available on a Map Screen")
		if not coordinator.last_game_state.screen.boss_available:
			raise Exception("The boss is not available to choose.")
		self.name = "boss"
		super().execute(coordinator)
		
	def __str__(self):
		return "[Choose Map Boss Action]" + super().__str__()


class StartGameAction(Action):
	"""An action to start a new game, if not already in a game"""

	def __init__(self, player_class, ascension_level=0, seed=None):
		super().__init__("start")
		self.player_class = player_class
		self.ascension_level = ascension_level
		self.seed = seed

	def execute(self, coordinator):
		arguments = [self.command, self.player_class.name, str(self.ascension_level)]
		if self.seed is not None:
			arguments.append(str(self.seed))
		coordinator.send_message(" ".join(arguments))
		
	def __str__(self):
		return "[Start Game Action] As {} A{} Seed:{}".format(self.player_class, self.ascension_level, self.seed)


class StateAction(Action):
	"""An action to use the CommunicationMod 'State' command"""

	def __init__(self, requires_game_ready=False):
		super().__init__(command="state", requires_game_ready=False)
		
	def __str__(self):
		return super().__str__()

