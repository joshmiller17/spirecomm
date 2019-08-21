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

				
	# Check that the simulator predicted this outcome was possible
	def simulation_sanity_check(self, original_state, action):
		original_state.debug_file = self.logfile_name
		simulated_state = original_state.takeAction(action, from_real=True)
		while len(simulated_state.debug_log):
			self.log(simulated_state.debug_log.pop(0))
		real_differ = StateDiff(original_state, self.blackboard.game, ignore_randomness=True)
		real_diff = real_differ.get_diff()
		if real_diff == {}:
			self.log("WARN: real diff is null", debug=3)
			self.note(str(original_state))
			self.note(str(self.blackboard.game))
		sim_differ = StateDiff(original_state, simulated_state, ignore_randomness=True)
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
		#diff = self.state_diff(self.blackboard.game, simulated_state)
		if diff_diff != {}:
			# check for just drawing different cards
			# if simulated_state.just_reshuffled:
				# if len(simulated_state.hand) == len(self.blackboard.game.hand) and len(simulated_state.discard_pile) == len(self.blackboard.game.discard_pile) and original_state.known_top_cards == []:
					# self.log("minor warning: reshuffled different cards in simulation")
					# skip_warn = True
			# elif "sims_val_drawn" in diff_diff and "real_val_drawn" in diff_diff:
				# if len(simulated_state.hand) == len(self.blackboard.game.hand) and original_state.known_top_cards == []:
					# self.log("minor warning: drew different cards in simulation")
					# if len(diff_diff) == 2:
						# skip_warn = True
					
			if not skip_warn:
				self.log("WARN: simulation discrepency, see log for details", debug=3)
			self.log("actual/sim diff: " + str(diff_diff), debug=3)
			self.log("sim diff: " + str(sim_diff), debug=3)
			self.log("real diff: " + str(real_diff), debug=3)
			# self.note("Simulated:")
			# self.note(str(simulated_state))
			# self.note("Actual:")
			# self.note(str(self.blackboard.game))
		else:
			self.log("Simulation sanity check success!", debug=5)
		return simulated_state
		
	
		
		
			
	# return a dict of powers and amount difference, assume 0 for non existent
	def get_power_changes(self, powers1, powers2):
		# convert tuples to dicts
		p1 = {}
		p2 = {}
		for p in powers1:
			p1[p.power_name] = p.amount
		for p in powers2:
			p2[p.power_name] = p.amount
			

		diff = {}
		powers = set(())
		for p in p1.keys():
			powers.add(p)
		for p in p2.keys():
			powers.add(p)
		for power in powers:
			amt1 = 0
			if power in p1:
				amt1 = p1[power]
			amt2 = 0
			if power in p2:
				amt2 = p2[power]
			if amt2 != amt1:
				diff[power] = amt2 - amt1
		
		return diff