from __future__ import division
import time
import random
import collections

from spirecomm.spire.game import Game
from spirecomm.spire.character import Intent, PlayerClass
import spirecomm.spire.card
from spirecomm.spire.screen import RestOption
from spirecomm.communication.action import *
from spirecomm.ai.priorities import *

import py_trees

AI_DELAY = 0.5 # seconds delay per action, useful for actually seeing what's going on
ASCENSION = 0

class TestBehaviour(py_trees.behaviour.Behaviour):
	def __init__(self, name, agent):
		"""
		Minimal one-time initialisation. A good rule of thumb is
		to only include the initialisation relevant for being able
		to insert this behaviour in a tree for offline rendering to
		dot graphs.

		Other one-time initialisation requirements should be met via
		the setup() method.
		"""
		super(TestBehaviour, self).__init__(name)
		self.agent = agent
		
	def log(self, msg):
		self.agent.log(msg)

	def setup(self):
		"""
		When is this called?
		  This function should be either manually called by your program
		  to setup this behaviour alone, or more commonly, via
		  :meth:`~py_trees.behaviour.Behaviour.setup_with_descendants`
		  or :meth:`~py_trees.trees.BehaviourTree.setup`, both of which
		  will iterate over this behaviour, it's children (it's children's
		  children ...) calling :meth:`~py_trees.behaviour.Behaviour.setup`
		  on each in turn.

		  If you have vital initialisation necessary to the success
		  execution of your behaviour, put a guard in your
		  :meth:`~py_trees.behaviour.Behaviour.initialise` method
		  to protect against entry without having been setup.

		What to do here?
		  Delayed one-time initialisation that would otherwise interfere
		  with offline rendering of this behaviour in a tree to dot graph
		  or validation of the behaviour's configuration.

		  Good examples include:

		  - Hardware or driver initialisation
		  - Middleware initialisation (e.g. ROS pubs/subs/services)
		  - A parallel checking for a valid policy configuration after
			children have been added or removed
		"""
		pass

	def initialise(self):
		"""
		When is this called?
		  The first time your behaviour is ticked and anytime the
		  status is not RUNNING thereafter.

		What to do here?
		  Any initialisation you need before putting your behaviour
		  to work.
		"""
		pass

	def update(self):
		"""
		When is this called?
		  Every time your behaviour is ticked.

		What to do here?
		  - Triggering, checking, monitoring. Anything...but do not block!
		  - Set a feedback message
		  - return a py_trees.common.Status.[RUNNING, SUCCESS, FAILURE]
		"""
		self.log("test leaf tick")
		self.agent.cmd_queue.append(self.agent.default_logic(self.agent.game))
		return py_trees.common.Status.SUCCESS

	def terminate(self, new_status):
		"""
		When is this called?
		   Whenever your behaviour switches to a non-running state.
			- SUCCESS || FAILURE : your behaviour's work cycle has finished
			- INVALID : a higher priority branch has interrupted, or shutting down
		"""
		pass
		

class SimpleAgent:

	def __init__(self, logfile, chosen_class=PlayerClass.IRONCLAD):
		self.game = Game()
		self.chosen_class = chosen_class
		self.change_class(chosen_class)
		self.debug_queue = ["Initting AI.", "Delay timer set to " + str(AI_DELAY)]
		self.cmd_queue = []
		self.logfile = logfile
		self.skipping_card = False
		self.root = py_trees.composites.Selector("Root")
		self.init_behaviour_tree(self.root) # Warning: uses British spelling
		self.behaviour_tree = py_trees.trees.BehaviourTree(self.root)
		# call behaviour_tree.tick() for one tick
		# can use behaviour.tick_once() to tick a specific behaviour
		
		# SIMPLE TRAITS
		self.errors = 0
		self.choose_good_card = False
		self.map_route = []
		self.upcoming_rooms = []
		self.priorities = Priority()
		
	def log(self, msg):
		print(str(time.time()) + ": " + msg, file=self.logfile, flush=True)
		self.debug_queue.append(msg)
		
	def init_behaviour_tree(self, root):
		# Template stuff FIXME
		test_leaf = TestBehaviour(name="Test", agent=self)
		root.add_children([test_leaf])
		self.log("behaviour tree initted")
		
	# For this to get plugged in, need to set pre_tick_handler = this func at some point
	# Can also set a post tick handler
	#def pre_tick_handler(self.behaviour_tree):
	#	pass
		
	def get_next_msg(self):
		try:
			return self.debug_queue.pop()
		except:
			return ""
			
	def think(self, msg):
		self.debug_queue.append(msg)
			
	def get_next_cmd(self):
		try:
			return self.cmd_queue.pop()
		except:
			return "STATE"
			
	def decide(self, action):
		self.log(str(action))
		return action
		
	def change_class(self, new_class):
		self.chosen_class = new_class
		if self.chosen_class == PlayerClass.THE_SILENT:
			self.priorities = SilentPriority() # Simple FIXME
		elif self.chosen_class == PlayerClass.IRONCLAD:
			self.priorities = IroncladPriority()  # Simple FIXME
		elif self.chosen_class == PlayerClass.DEFECT:
			self.priorities = DefectPowerPriority()  # Simple FIXME
		else:
			self.priorities = random.choice(list(PlayerClass))  # Simple FIXME

	def handle_error(self, error):
		self.log("ERROR: " + str(error))
		print(self.get_next_action_in_game(self.game), file=self.logfile, flush=True)
		#raise Exception(error)
		
	def default_logic(self, game_state):
	
		self.log("The game state is " + str(self.game))
		if self.game.choice_available:
			return self.decide(self.handle_screen())
		if self.game.proceed_available:
			return self.decide(ProceedAction())
		if self.game.play_available or self.game.end_available:
			return self.handle_combat()
		if self.game.cancel_available:
			return self.decide(CancelAction())
		self.log("Did you pause? I don't know what to do! I'll just wait a sec...")
		time.sleep(3)
		return "STATE"

	def get_next_action_in_game(self, game_state):
		time.sleep(AI_DELAY)
		self.game = game_state
		STATE = self.game
		
		try:
			self.log("starting tick")
			self.compute_smart_state()
			self.behaviour_tree.tick() # should add an action to the self.cmd_queue
			self.log("finished tick")
		except Exception as e:
			self.log("agent encountered error")
			self.log(str(e))
			self.log(traceback.format_exc())
			print(traceback.format_exc(), file=self.logfile, flush=True)
		
		return self.get_next_cmd()
		

	def get_next_action_out_of_game(self):
		self.log("starting game")
		return StartGameAction(self.chosen_class, ascension_level=ASCENSION)
		
	def compute_smart_state(self):
		pass
		#g = self.game
		#hp_percent = (g.current_hp * 100.0) / g.max_hp
		#self.think("I'm at {0:.0f}% HP".format(hp_percent))
		
		for monster in self.game.monsters:
			if monster.half_dead:
				self.think("{} ({}) is half-dead!".format(monster.name, monster.monster_index))
			#if monster.is_gone:
			#	self.think("{} ({}) is gone!".format(monster.name, monster.monster_index))
			if monster.intent.is_attack():
				if monster.move_adjusted_damage is not None:
					self.think("{} ({}) is hitting me for {}x{} damage".format(monster.name, monster.monster_index, monster.move_adjusted_damage, monster.move_hits))
				else: 
					self.think("{} ({}) is hitting me for {} damage".format(monster.name, monster.monster_index, monster.incoming_damage))
		
		# FIXME map_route isn't actually nodes, but a set of X coords
		#upcoming_rooms = collections.defaultdict(int)
		#self.generate_map_route()
		#for node in self.map_route:
		#	upcoming_rooms[node.symbol] += 1
		#self.think("My chosen map route has these rooms:")
		#for key,value in upcoming_rooms.items():
		#	self.think("{}.{}".format(key,value))	
		
		
		
# ---------------------------------------------

	def handle_combat(self):
		if self.game.room_type == "MonsterRoomBoss" and len(self.game.get_real_potions()) > 0:
			potion_action = self.use_next_potion()
			if potion_action is not None:
				return self.decide(potion_action)
		if self.game.play_available:
			return self.decide(self.get_play_card_action())
		return self.decide(EndTurnAction())

	def is_monster_attacking(self):
		for monster in self.game.monsters:
			if monster.intent.is_attack() or monster.intent == Intent.NONE:
				return True
		return False

	def get_incoming_damage(self):
		incoming_damage = 0
		for monster in self.game.monsters:
			if not monster.is_gone and not monster.half_dead:
				if monster.move_adjusted_damage is not None:
					incoming_damage += monster.move_adjusted_damage * monster.move_hits
				elif monster.intent == Intent.NONE:
					incoming_damage += 5 * self.game.act
		return incoming_damage

	def get_low_hp_target(self):
		available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		best_monster = min(available_monsters, key=lambda x: x.current_hp)
		return best_monster

	def get_high_hp_target(self):
		available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		best_monster = max(available_monsters, key=lambda x: x.current_hp)
		return best_monster

	def many_monsters_alive(self):
		available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
		return len(available_monsters) > 1

	def get_play_card_action(self):
		playable_cards = [card for card in self.game.hand if card.is_playable]
		zero_cost_cards = [card for card in playable_cards if card.cost == 0]
		zero_cost_attacks = [card for card in zero_cost_cards if card.type == spirecomm.spire.card.CardType.ATTACK]
		zero_cost_non_attacks = [card for card in zero_cost_cards if card.type != spirecomm.spire.card.CardType.ATTACK]
		nonzero_cost_cards = [card for card in playable_cards if card.cost != 0]
		aoe_cards = [card for card in playable_cards if self.priorities.is_card_aoe(card)]
		if self.game.player.block > self.get_incoming_damage() - (self.game.act + 4):
			offensive_cards = [card for card in nonzero_cost_cards if not self.priorities.is_card_defensive(card)]
			if len(offensive_cards) > 0:
				nonzero_cost_cards = offensive_cards
			else:
				nonzero_cost_cards = [card for card in nonzero_cost_cards if not card.exhausts]
		if len(playable_cards) == 0:
			return EndTurnAction()
		if len(zero_cost_non_attacks) > 0:
			card_to_play = self.priorities.get_best_card_to_play(zero_cost_non_attacks)
		elif len(nonzero_cost_cards) > 0:
			card_to_play = self.priorities.get_best_card_to_play(nonzero_cost_cards)
			if len(aoe_cards) > 0 and self.many_monsters_alive() and card_to_play.type == spirecomm.spire.card.CardType.ATTACK:
				card_to_play = self.priorities.get_best_card_to_play(aoe_cards)
		elif len(zero_cost_attacks) > 0:
			card_to_play = self.priorities.get_best_card_to_play(zero_cost_attacks)
		else:
			# This shouldn't happen!
			return EndTurnAction()
		if card_to_play.has_target:
			available_monsters = [monster for monster in self.game.monsters if monster.current_hp > 0 and not monster.half_dead and not monster.is_gone]
			if len(available_monsters) == 0:
				return EndTurnAction()
			if card_to_play.type == spirecomm.spire.card.CardType.ATTACK:
				target = self.get_low_hp_target()
			else:
				target = self.get_high_hp_target()
			return PlayCardAction(card=card_to_play, target_monster=target)
		else:
			return PlayCardAction(card=card_to_play)

	def use_next_potion(self):
		for potion in self.game.get_real_potions():
			if potion.can_use:
				if potion.requires_target:
					return PotionAction(True, potion=potion, target_monster=self.get_low_hp_target())
				else:
					return PotionAction(True, potion=potion)

	# TODO
	def handle_event(self):
		#if self.game.screen.event_id in ["Vampires", "Masked Bandits", "Knowing Skull", "Ghosts", "Liars Game", "Golden Idol", "Drug Dealer", "The Library"]:
		#		return ChooseAction(len(self.game.screen.options) - 1)
		return ChooseAction(0)
		
	# TODO
	def handle_chest(self):
		return OpenChestAction()
		
	# TODO
	def handle_shop(self):
		return ProceedAction()
		#return ChooseShopkeeperAction()
		
	# TODO
	def handle_shop_screen(self):
		if self.game.screen.purge_available and self.game.gold >= self.game.screen.purge_cost:
			return ChooseAction(name="purge")
		for card in self.game.screen.cards:
			if self.game.gold >= card.price and not self.priorities.should_skip(card):
				return BuyCardAction(card)
		for relic in self.game.screen.relics:
			if self.game.gold >= relic.price:
				return BuyRelicAction(relic)
		return CancelAction()
		
		
	# TODO
	def handle_rewards(self):
		for reward_item in self.game.screen.rewards:
			if reward_item.reward_type == RewardType.POTION and self.game.are_potions_full():
				continue
			elif reward_item.reward_type == RewardType.CARD and self.skipping_card:
				continue
			else:
				return CombatRewardAction(reward_item)
		return ProceedAction()
		
	# TODO
	def handle_boss_reward(self):
		relics = self.game.screen.relics
		best_boss_relic = self.priorities.get_best_boss_relic(relics)
		return BossRewardAction(best_boss_relic)
		
		
	def handle_screen(self):
		if self.game.screen_type == ScreenType.EVENT:
			return self.handle_event()
		elif self.game.screen_type == ScreenType.CHEST:
			return self.handle_chest()
		elif self.game.screen_type == ScreenType.SHOP_ROOM:
			return self.handle_shop()
		elif self.game.screen_type == ScreenType.REST:
			return self.choose_rest_option()
		elif self.game.screen_type == ScreenType.CARD_REWARD:
			return self.choose_card_reward()
		elif self.game.screen_type == ScreenType.COMBAT_REWARD:
			return self.handle_rewards()
		elif self.game.screen_type == ScreenType.MAP:
			return self.make_map_choice()
		elif self.game.screen_type == ScreenType.BOSS_REWARD:
			return self.handle_boss_reward()
		elif self.game.screen_type == ScreenType.SHOP_SCREEN:
			return self.handle_shop_screen();
		elif self.game.screen_type == ScreenType.GRID:
			if not self.game.choice_available:
				return ProceedAction()
			if self.game.screen.for_upgrade or self.choose_good_card:
				available_cards = self.priorities.get_sorted_cards(self.game.screen.cards)
			else:
				available_cards = self.priorities.get_sorted_cards(self.game.screen.cards, reverse=True)
			num_cards = self.game.screen.num_cards
			return CardSelectAction(available_cards[:num_cards])
		elif self.game.screen_type == ScreenType.HAND_SELECT:
			if not self.game.choice_available:
				return ProceedAction()
			# Usually, we don't want to choose the whole hand for a hand select. 3 seems like a good compromise.
			num_cards = min(self.game.screen.num_cards, 3)
			return CardSelectAction(self.priorities.get_cards_for_action(self.game.current_action, self.game.screen.cards, num_cards))
		else:
			return ProceedAction()

	def choose_rest_option(self):
		rest_options = self.game.screen.rest_options
		if len(rest_options) > 0 and not self.game.screen.has_rested:
			if RestOption.REST in rest_options and self.game.current_hp < self.game.max_hp / 2:
				return RestAction(RestOption.REST)
			elif RestOption.REST in rest_options and self.game.act != 1 and self.game.floor % 17 == 15 and self.game.current_hp < self.game.max_hp * 0.9:
				return RestAction(RestOption.REST)
			elif RestOption.SMITH in rest_options:
				return RestAction(RestOption.SMITH)
			elif RestOption.LIFT in rest_options:
				return RestAction(RestOption.LIFT)
			elif RestOption.DIG in rest_options:
				return RestAction(RestOption.DIG)
			elif RestOption.REST in rest_options and self.game.current_hp < self.game.max_hp:
				return RestAction(RestOption.REST)
			else:
				return ChooseAction(0)
		else:
			return ProceedAction()

	def count_copies_in_deck(self, card):
		count = 0
		for deck_card in self.game.deck:
			if deck_card.card_id == card.card_id:
				count += 1
		return count

	def choose_card_reward(self):
		reward_cards = self.game.screen.cards
		if self.game.screen.can_skip and not self.game.in_combat:
			pickable_cards = [card for card in reward_cards if self.priorities.needs_more_copies(card, self.count_copies_in_deck(card))]
		else:
			pickable_cards = reward_cards
		if len(pickable_cards) > 0:
			potential_pick = self.priorities.get_best_card(pickable_cards)
			return CardRewardAction(potential_pick)
		elif self.game.screen.can_bowl:
			return CardRewardAction(bowl=True)
		else:
			self.skipping_card = True
			return CancelAction()
			
	# TODO generate_map_route, then get the actual symbols in order that we'll encounter them
	def get_informative_path(self):
		pass

	# TODO How many possible paths are there? Should I just iterate through all possibilities and pick the one that best fits a set of heuristics?
	def generate_map_route(self):
		node_rewards = self.priorities.MAP_NODE_PRIORITIES.get(self.game.act)
		best_rewards = {0: {node.x: node_rewards[node.symbol] for node in self.game.map.nodes[0].values()}}
		best_parents = {0: {node.x: 0 for node in self.game.map.nodes[0].values()}}
		min_reward = min(node_rewards.values())
		map_height = max(self.game.map.nodes.keys())
		for y in range(0, map_height):
			best_rewards[y+1] = {node.x: min_reward * 20 for node in self.game.map.nodes[y+1].values()}
			best_parents[y+1] = {node.x: -1 for node in self.game.map.nodes[y+1].values()}
			for x in best_rewards[y]:
				node = self.game.map.get_node(x, y)
				best_node_reward = best_rewards[y][x]
				for child in node.children:
					test_child_reward = best_node_reward + node_rewards[child.symbol]
					if test_child_reward > best_rewards[y+1][child.x]:
						best_rewards[y+1][child.x] = test_child_reward
						best_parents[y+1][child.x] = node.x
		best_path = [0] * (map_height + 1)
		best_rooms = [0] * (map_height + 1)
		best_path[map_height] = max(best_rewards[map_height].keys(), key=lambda x: best_rewards[map_height][x])
		for y in range(map_height, 0, -1):
			best_path[y - 1] = best_parents[y][best_path[y]]
			#best_rooms[y - 1] =  # TODO get symbol of best_path[y-1]
		self.map_route = best_path
		self.upcoming_rooms = best_rooms

	def make_map_choice(self):
		if len(self.game.screen.next_nodes) > 0 and self.game.screen.next_nodes[0].y == 0:
			self.generate_map_route()
			self.game.screen.current_node.y = -1
		if self.game.screen.boss_available:
			return ChooseMapBossAction()
		chosen_x = self.map_route[self.game.screen.current_node.y + 1]
		for choice in self.game.screen.next_nodes:
			if choice.x == chosen_x:
				return ChooseMapNodeAction(choice)
		# This should never happen
		return ChooseAction(0)

