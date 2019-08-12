class Reward:
	
	def __init__(self, reward={}):
		self.totalItemized = reward
		
	def __str__(self):
		ret = ", ".join([key + ": " + str(value) for key, value in self.totalItemized.items()])
		return ret
		
	def addReward(self, reward):
		if reward is None:
			return self
		for key, value in reward.totalItemized.items():
			if key in self.totalItemized:
				self.totalItemized[key] += value
			else:
				self.totalItemized[key] = value
		return self
		
	def getTotalReward(self):
		ret = 0
		for key, value in self.totalItemized.items():
			ret += value
		return ret
		
	def getTotalItemized(self):
		return self.totalItemized
		

		
# return value of terminal state
def getReward(self):
		
		# Trace back to where we started
		original_game_state = self.game
		while original_game_state.original_state is not None:
			original_game_state = original_game_state.original_state
			
		delta_hp = self.game.player.current_hp - original_game_state.player.current_hp
		delta_max_hp = self.game.player.max_hp - original_game_state.player.max_hp
		orig_potions = 0
		for p in original_game_state.potions:
			if p.name != "Potion Slot":
				orig_potions += 1
		delta_potions = -1 * orig_potions
		for p in original_game_state.potions:
			if p.name != "Potion Slot":
				delta_potions += 1
		
		r = {}
		r["HP"] = delta_hp * MCTS_HP_VALUE
		r["max HP"] = delta_max_hp * MCTS_MAX_HP_VALUE
		#r["potions"] = delta_potions * MCTS_POTION_VALUE
		#r -= self.game.combat_round * MCTS_ROUND_COST
		reward = Reward(r)
		
		if self.debug_file:
			with open(self.debug_file, 'a+') as d:
				d.write("\n~~~~~~~~~~~~~~\n")
				d.write("\nTerminal state reached, reward: " + str(reward.getTotalItemized()) + "\n")
				d.write(str(self))
				d.write("\n~~~~~~~~~~~~~~\n")
		
		return reward