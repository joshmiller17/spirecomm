from enum import Enum
import copy
import random
import math
import os
import spirecomm

from spirecomm.ai.statediff import *

# The State Comparer returns a StateDiff object between two Game states
# aka "The Diff Differ"

class StateComparer:

	def __init__(self, original_state, action, agent):
		self.original_state = original_state
		self.action = action
		self.agent = agent
		
	# Check that the simulator predicted this outcome was possible
	# returns simulation
	def compare(self):
		self.original_state.debug_file = self.agent.logfile_name
		simulated_state = self.original_state.takeAction(self.action, from_real=True)
		while len(simulated_state.debug_log):
			self.agent.log(simulated_state.debug_log.pop(0))
		real_differ = StateDiff(self.original_state, self.agent.blackboard.game, ignore_randomness=True, agent=self.agent)
		real_diff = real_differ.get_diff()
		if real_diff == {}:
			self.agent.log("WARN: real diff is null", debug=3)
			self.agent.note(str(self.original_state))
			self.agent.note(str(self.agent.blackboard.game))
		sim_differ = StateDiff(self.original_state, simulated_state, ignore_randomness=True, agent=self.agent)
		sim_diff = sim_differ.get_diff()
		diff_diff = {}
		skip_warn = False
		for key, value in real_diff.items():
			if key not in sim_diff:
				diff_diff["sim_missing_" + key] = value
			else:
				val_diff = value != sim_diff[key]
				if type(value) is list: # compare lists in unordered way
					val_diff = set(value) != set(sim_diff[key])
				if val_diff:
					diff_diff["sims_val_" + key] = sim_diff[key]
					diff_diff["real_val_" + key] = value
		for key, value in sim_diff.items():
			if key not in real_diff:
				diff_diff["sim_added_" + key] = value
		#diff = self.state_diff(self.agent.blackboard.game, simulated_state)
		if diff_diff != {}:
			# check for just drawing different cards
			# if simulated_state.just_reshuffled:
				# if len(simulated_state.hand) == len(self.agent.blackboard.game.hand) and len(simulated_state.discard_pile) == len(self.agent.blackboard.game.discard_pile) and self.original_state.known_top_cards == []:
					# self.agent.log("minor warning: reshuffled different cards in simulation")
					# skip_warn = True
			# elif "sims_val_drawn" in diff_diff and "real_val_drawn" in diff_diff:
				# if len(simulated_state.hand) == len(self.agent.blackboard.game.hand) and self.original_state.known_top_cards == []:
					# self.agent.log("minor warning: drew different cards in simulation")
					# if len(diff_diff) == 2:
						# skip_warn = True
					
			if not skip_warn:
				self.agent.log("WARN: simulation discrepency, see log for details", debug=3)
			self.agent.log("actual/sim diff: " + str(diff_diff), debug=3)
			self.agent.log("sim diff: " + str(sim_diff), debug=3)
			self.agent.log("real diff: " + str(real_diff), debug=3)
			# self.agent.note("Simulated:")
			# self.agent.note(str(simulated_state))
			# self.agent.note("Actual:")
			# self.agent.note(str(self.agent.blackboard.game))
		else:
			self.agent.log("Simulation sanity check success!", debug=5)
		return simulated_state
		
	