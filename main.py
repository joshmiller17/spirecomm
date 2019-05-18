import itertools
import datetime
import sys
import os
import collections
import time
from threading import Thread


import spirecomm.communication.coordinator as coord
from spirecomm.ai.agent import SimpleAgent
from spirecomm.ai.evolver import EvolvingAgent
from spirecomm.spire.character import PlayerClass


def run_agent():
	#agent = SimpleAgent(chosen_class=PlayerClass.THE_SILENT)
	coordinator = coord.Coordinator()
	agent = EvolvingAgent(coordinator=coordinator,chosen_class=PlayerClass.IRONCLAD) # Start with just training on one class
	coordinator.signal_ready()
	coordinator.register_command_error_callback(agent.handle_error)
	coordinator.register_state_change_callback(agent.get_next_action_in_game)
	coordinator.register_out_of_game_callback(agent.get_next_action_out_of_game)

	while True:
		result = coordinator.play_one_game(PlayerClass.IRONCLAD)
	# Play games forever, cycling through the various classes
#	for chosen_class in itertools.cycle(PlayerClass):
		#agent.change_class(chosen_class) # Start with just training on one class
#		result = coordinator.play_one_game(chosen_class)


if __name__ == "__main__":
	run_agent()