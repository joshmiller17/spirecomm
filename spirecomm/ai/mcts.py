import math
import random
import time

def rolloutPolicy(state):
	while not state.isTerminal():
		try:
			weights = [1] * len(state.getPossibleActions())
			weights[0] *= 0.15 # weigh End Turn less, this is usually not the right action if there's something else we can do
			action = random.choice(state.getPossibleActions())
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
		self.totalReward = 0
		self.children = {}
		
	# Returns a tree that explains its decision-making process
	def explain(self):
		pass # TODO
		
	def __str__(self):
		# TEST
		print(str(self.state))
		print("Reward is " + str(self.totalReward))
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
		self.explorationConstant = explorationConstant
		self.rollout = rolloutPolicy

	def search(self, initialState):
		self.root = treeNode(initialState, None)

		if self.limitType == 'time':
			timeLimit = time.time() + self.timeLimit / 1000
			while time.time() < timeLimit:
				self.executeRound()
		else:
			for i in range(self.searchLimit):
				self.executeRound()

		bestChild = self.getBestChild(self.root, 0)
		#TEST
		# print(self.root.children.keys())
		# for action,child in self.root.children.items():
		# 	nodeValue = child.totalReward / child.numVisits
		# 	print("%s: %f"%(action,nodeValue))
		return self.getAction(self.root, bestChild)

	def executeRound(self):
		node = self.selectNode(self.root)
		reward = self.rollout(node.state)
		self.backpropogate(node, reward)

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
			node.totalReward += reward
			node = node.parent

	def getBestChild(self, node, explorationValue):
		bestValue = float("-inf")
		bestNodes = []
		for child in node.children.values():
			nodeValue = child.totalReward / child.numVisits + explorationValue * math.sqrt(
				2 * math.log(node.numVisits) / child.numVisits)
			if nodeValue > bestValue:
				bestValue = nodeValue
				bestNodes = [child]
			elif nodeValue == bestValue:
				bestNodes.append(child)
		return random.choice(bestNodes)

	def getAction(self, root, bestChild):		
		#print(str(root)) # TEST
		for action, node in root.children.items():
			if node is bestChild:
				return action