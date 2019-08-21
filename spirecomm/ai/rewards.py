
# This helper file enables a Game object to estimate its value



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
