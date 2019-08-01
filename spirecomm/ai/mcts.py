import math
import random
import time


COGITATION_LEVEL = 7

def rolloutPolicy(state):
	while not state.isTerminal():
		try:
			action_weights = [1] * len(state.getPossibleActions())
			action_weights[0] *= 0.2 # FIXME this seems to do nothing?? # weigh End Turn less, this is usually not the right action if there's something else we can do
			action = random.choices(population=state.getPossibleActions(), weights=action_weights)[0] # returns a list of len 1, extract the choice
		except IndexError:
			raise Exception("Non-terminal state has no possible actions: " + str(state))
		state = state.takeAction(action)
	return state.getReward()

class treeNode():
	def __init__(self, state, parent):
		self.state = state
		self.isTerminal = state.isTerminal()
		self.isFullyExpanded = self.isTerminal
		self.parent = parent
		self.numVisits = 0
		self.reward = None
		self.children = {}
		
	# Returns a tree that explains its decision-making process
	def explain(self):
		pass # TODO
		
	def __str__(self):
		#print(str(self.state))
		print("Reward is " + str(self.reward.getTotalReward()))
		print("Visited " + str(self.numVisits))
		for action, node in self.children.items():
			if action:
				print(str(action) + " will lead to:")
			if node:
				print(str(node))
		return ""
			

class mcts():
	def __init__(self, timeLimit=None, iterationLimit=None, explorationConstant=1 / math.sqrt(2),
				 rolloutPolicy=rolloutPolicy):
		if timeLimit != None:
			if iterationLimit != None:
				raise ValueError("Cannot have both a time limit and an iteration limit")
			# time taken for each MCTS search in milliseconds
			self.timeLimit = timeLimit
			self.limitType = 'time'
		else:
			if iterationLimit == None:
				raise ValueError("Must have either a time limit or an iteration limit")
			# number of iterations of the search
			if iterationLimit < 1:
				raise ValueError("Iteration limit must be greater than one")
			self.searchLimit = iterationLimit
			self.limitType = 'iterations'
			
		self.limitType = 'smart' # TEST
			
		self.explorationConstant = explorationConstant
		self.rollout = rolloutPolicy

	def search(self, initialState):
		self.root = treeNode(initialState, None)
				
		if self.limitType == 'time':
			timeLimit = time.time() + self.timeLimit / 1000
			while time.time() < timeLimit:
				self.executeRound()
		elif self.limitType == 'iterations':
			for i in range(self.searchLimit):
				self.executeRound()
		elif self.limitType == 'smart':
			rounds = 1
			best_child = None
			rounds_certainty = 0
			while True:
				self.executeRound()
				rounds += 1
				new_best_child = self.getBestChild(self.root, 0)
				if best_child == new_best_child:
					rounds_certainty += 1
				else:
					best_child = new_best_child
					rounds_certainty = 0

				if rounds_certainty > COGITATION_LEVEL:
					break
				
				if rounds > 20 * len(self.root.children):
					break

		else:
			raise Exception("Unknown MCTS limit type.")

		print("") # TEST
		bestChild = self.getBestChild(self.root, 0)
		return self.getAction(self.root, bestChild)
		
	def get_values_of_children(self):
		vals = []
		for action, node in self.root.children.items():
			vals.append(node.reward.getTotalReward() / node.numVisits)
		return vals

	def executeRound(self):
		node = self.selectNode(self.root)
		reward = self.rollout(node.state)
		self.backpropogate(node, reward)
		
		# TEST
		bestChild = self.getBestChild(self.root, 0)
		vals = self.get_values_of_children()
		if len(vals) > 1:
			vals.remove(max(vals))
			second_highest = max(vals)
		else:
			second_highest = -999
		for action, node in self.root.children.items():
			if node is bestChild:
				best_value = node.reward.getTotalReward() / node.numVisits
				val_diff = best_value - second_highest
				face = "-_-"
				if second_highest != -999:
					if val_diff < 0:
						face = ">_<"
					elif val_diff < 1:
						face = "O_o"
					elif val_diff < 4:
						face = "*_*'"
					elif val_diff < 10:
						face = "^_^"
					else:
						face = "\(^o^)/"
				#print("Considering " + str(action) + " [" + str(val_diff) + "]" + " " * 20, end='\r')
				print("Considering " + str(action) + " [" + face + "]" + " " * 20, end='\r')

	def selectNode(self, node):
		while not node.isTerminal:
			if node.isFullyExpanded:
				node = self.getBestChild(node, self.explorationConstant)
			else:
				return self.expand(node)
		return node

	def expand(self, node):
		actions = node.state.getPossibleActions()
		for action in actions:
			if action not in node.children:
				newNode = treeNode(node.state.takeAction(action), node)
				node.children[action] = newNode
				if len(actions) == len(node.children):
					node.isFullyExpanded = True
				return newNode

		raise Exception("Should never reach here")

	def backpropogate(self, node, reward):
		while node is not None:
			node.numVisits += 1
			if node.reward is None:
				node.reward = reward
			else:
				node.reward.addReward(reward)
			node = node.parent

	def getBestChild(self, node, explorationValue):
		bestValue = float("-inf")
		bestNodes = []
		for child in node.children.values():
			nodeValue = (child.reward.getTotalReward() / child.numVisits) + explorationValue * math.sqrt(
				2 * math.log(node.numVisits) / child.numVisits)
			if nodeValue > bestValue:
				bestValue = nodeValue
				bestNodes = [child]
			elif nodeValue == bestValue:
				bestNodes.append(child)
		return random.choice(bestNodes)

	def getAction(self, root, bestChild):		
		for action, node in root.children.items():
			if node is bestChild:
				return action
				