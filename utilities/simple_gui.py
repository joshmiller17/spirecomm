import os
import collections
import itertools
import datetime
import sys
import time
import traceback
import threading
import json
import re
import random
import math			

#import spirecomm
#print(spirecomm.__file__)

import spirecomm.config as config
import spirecomm.spire.card
from spirecomm.ai.mcts import *

from spirecomm.spire.game import Game
import spirecomm.communication.coordinator as coord
from spirecomm.ai.agent import SimpleAgent
from spirecomm.spire.character import PlayerClass

os.environ["KIVY_NO_CONSOLELOG"] = "1"

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window

		

class Base(BoxLayout):

	def __init__(self, coordinator, agent, f):
		super().__init__(orientation='vertical')
		self.coordinator = coordinator
		self.agent = agent
		self.log = f
		self.last_comm = ""
		self.step = False # whether to Run or Step when pressing Resume
		self.sleeping = False
		self.z_count = 0
		print("Base: Init", file=self.log, flush=True)

		self.input_text = TextInput(size_hint=(2, 7))
		self.input_text.text = ""
		self.input_text.foreground_color = (1, 1, 1, 1)
		self.input_text.background_color = (.1, .1, .1, 1)
		self.input_text.readonly = True
		self.max_in_history_lines = 500
		self.in_history = collections.deque(maxlen=self.max_in_history_lines)
		self.add_widget(self.input_text)

		self.out_history_text = TextInput(size_hint=(1, 2))
		self.out_history_text.readonly = True
		self.out_history_text.foreground_color = (1, 1, 1, 1)
		self.out_history_text.background_color = (.1, .1, .1, 1)
		self.add_widget(self.out_history_text)

		self.output_text = TextInput(size_hint=(1, 1))
		self.output_text.foreground_color = (1, 1, 1, 1)
		self.output_text.background_color = (.1, .1, .1, 1)
		self.add_widget(self.output_text)

		self.button = Button(text='Send', size_hint=(1, 1))
		self.button.bind(on_press=self.send_output)
		self.add_widget(self.button)
		
		self.pause = Button(text='Pause', size_hint=(1, 1))
		self.pause.bind(on_press=self.do_pause)
		self.add_widget(self.pause)
		
		self.resume = Button(text='Resume', size_hint=(1, 1))
		self.resume.bind(on_press=self.do_resume)
		self.add_widget(self.resume)

		self.max_out_history_lines = 5
		self.out_history_lines = collections.deque(maxlen=self.max_out_history_lines)

		Window.bind(on_key_up=self.key_callback)

	def do_communication(self, dt):
	
		
		new_msg = str(self.agent.get_next_msg())
		if new_msg != "":
			if new_msg == 'z':
				self.sleeping = True
				self.z_count += 1
			else:
				self.sleeping = False
				self.z_count = 0
				msgs = new_msg.split('\n')
				for m in msgs:
					self.in_history.append(m)
			if len(threading.enumerate()) != 4:
				self.in_history.append("[ERR] A thread has crashed, likely the agent.")
				
		
		self.input_text.text = "\n".join(self.in_history)
		if self.sleeping:
			self.input_text.text += "\n" + 'z' * (1 + self.z_count % 3)
		
		action_msg = self.coordinator.get_action_played()
			

	def do_pause(self, instance=None):
		self.agent.pause()
	
	def do_resume(self, instance=None):
		if not self.step:
			self.agent.resume()
		else:
			self.agent.take_step()
		
	def send_output(self, instance=None, text=None):
		if text is None:
			text = self.output_text.text
		text = text.strip()
		if not self.handle_debug_cmds(text):
			print(text, end='\n', flush=True)
		self.out_history_lines.append(text)
		self.out_history_text.text = "\n".join(self.out_history_lines)
		self.output_text.text = ""

	def key_callback(self, window, keycode, *args):
		if keycode == 13:
			self.send_output()
			
	# Returns True if message was a debug command to execute,
	# False if we should print out for CommMod
	def handle_debug_cmds(self, msg):
	
		# testbed
		if msg == "test":
			
			self.in_history.append("Executed test operations successfully.")
			return True
	
		if msg == "threadcheck":
			for thread in threading.enumerate():
				print(thread, file=self.log, flush=True)
				print(thread.isAlive(), file=self.log, flush=True)
				self.in_history.append(str(thread) + str(thread.isAlive()))

			return True
			
		if msg == "step":
			self.step = not self.step
			self.in_history.append("Step mode: " + ("ON" if self.step else "OFF"))
			return True

		if msg == "write":
			self.agent.tree_to_json("tree.json")
			self.in_history.append("Behaviour tree saved to tree.json")
			return True
			
		elif msg.startswith("write "):
			filename = msg[6:]
			self.agent.tree_to_json(filename + ".json")
			self.in_history.append("Behaviour tree saved to " + filename + ".json")
			return True
			
		if msg == "tree":
			self.agent.print_tree()
			return True
			
		if msg == "test combat":
			try:
				open("game.log", "w").close()
				communication_state = json.load(open(os.path.join(config.SPIRECOMM_PATH, "utilities", "combat_example.json")))
				game_state = Game.from_json(communication_state.get("game_state"), communication_state.get("available_commands"))
				game_state.debug_file = "game.log"
				mcts_timeout = 2000 # in ms # eventually set to agent.action_delay * 1000 with debug cmd to adjust
				monte_carlo = mcts(timeLimit=mcts_timeout)

				
				while game_state.current_hp > 0 and game_state.monsters[0].current_hp > 0:
					#actions = game_state.get_possible_actions(debug_file="game.log")
					#game_state = game_state.take_action(random.choice(actions), debug_file="game.log")
					action = monte_carlo.search(initialState=game_state)
					print("MCTS choosing: " + str(action))
					game_state = game_state.takeAction(action)

				print("")		
				self.in_history.append("VICTORY" if game_state.current_hp > 0 else "DEFEAT")
				self.in_history.append("Health left: " + str(game_state.current_hp))
				self.in_history.append("See game.log for details")
				
			except Exception as e:
				print(str(e))
				print(traceback.format_exc())
				self.in_history.append("Error: " + str(e))
				print(traceback.format_exc(), file=self.log, flush=True)

			return True

		if msg == "load":
			msg = "load tree"
			
		if msg.startswith("load "):
			filename = msg[5:]
			try:
				self.in_history.append("Loading " + filename + ".json")
				self.agent.json_to_tree(filename + ".json")
			except Exception as e:
				print(e, file=self.log, flush=True)
				
			return True
			
		if msg.startswith("delay "):
			try:
				self.agent.action_delay = float(msg[6:])
				self.in_history.append("DELAY SET TO " + str(self.agent.action_delay))
				return True
			except Exception as e:
				print(e, file=self.log, flush=True)
			
		if msg.startswith("debug "):
			try:
				self.agent.debug_level = int(msg[6:])
				self.in_history.append("DEBUG SET TO " + str(self.agent.debug_level))
				return True
			except Exception as e:
				print(e, file=self.log, flush=True)
			
		if msg == "clear":
			self.input_text.text = ""
			return True
			
		return False
		
	def randomPolicy(state):
		while not state.isTerminal():
			try:
				action = random.choice(state.getPossibleActions())
			except IndexError:
				raise Exception("Non-terminal state has no possible actions: " + str(state))
			state = state.takeAction(action)
		return state.getReward()





class CommunicationApp(App):

	def __init__(self, coordinator, agent, f):
		super().__init__()
		self.coordinator = coordinator
		self.agent = agent
		self.log = f
		print("Kivy: Init", file=self.log, flush=True)

	def build(self):
		base = Base(self.coordinator, self.agent, self.log)
		Clock.schedule_interval(base.do_communication, 1.0 / 120.0)
		return base

		
def run_agent(f, communication_coordinator):
	# TEST
	print("Agent: preparing profiler test", file=f, flush=True)
	try:
		# import io, cProfile, pstats
		# pr = cProfile.Profile()
		# pr.enable()
		# s = io.StringIO()
		# print("Agent: init profiler test", file=f, flush=True)

		result = communication_coordinator.play_one_game(PlayerClass.IRONCLAD)
		print("Agent: first game ended in {}" "victory" if result else "defeat", file=f, flush=True)
		# print("Agent: finishing profiler test", file=f, flush=True)
		# pr.disable()
		# sortby = 'cumulative'
		# ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
		# ps.print_stats()
		# print(s.getvalue(), file=f, flush=True)
	
	except Exception as e:
		print("Agent thread encountered error:", file=f, flush=True)
		print(e, file=f, flush=True)
		print(traceback.format_exc(), file=f, flush=True)
	
	# return # END TEST

	#Play games forever, cycling through the various classes
	for chosen_class in itertools.cycle(PlayerClass):
		#agent.change_class(chosen_class)
		print("Agent: new game", file=f, flush=True)
		result = communication_coordinator.play_one_game(PlayerClass.IRONCLAD)
		print("Agent: game ended in {}" "victory" if result else "defeat", file=f, flush=True)
		#result = coordinator.play_one_game(chosen_class)

def launch_gui():
	f=open("ai.log","w")
	print("GUI: Init " + str(time.time()), file=f, flush=True)
	agent = SimpleAgent(f)
	print("GUI: Register agent", file=f, flush=True)
	communication_coordinator = coord.Coordinator()
	print("GUI: Register coordinator", file=f, flush=True)
	communication_coordinator.signal_ready()
	print("GUI: Ready", file=f, flush=True)
	communication_coordinator.register_command_error_callback(agent.handle_error)
	communication_coordinator.register_state_change_callback(agent.get_next_action_in_game)
	communication_coordinator.register_out_of_game_callback(agent.get_next_action_out_of_game)
	print("GUI: Registered coordinator actions", file=f, flush=True)
	agent_thread = threading.Thread(target=run_agent, args=(f,communication_coordinator))
	print("Agent thread is " + str(agent_thread), file=f, flush=True)
	agent_thread.daemon = True
	print("Agent: Init", file=f, flush=True)
	agent_thread.start()
	print("Agent: Starting", file=f, flush=True)
	print("GUI: Starting mainloop", file=f, flush=True)
	CommunicationApp(communication_coordinator, agent, f).run()
	
def verifyJSONFolder(directory,kind):
	error = ""
	files = [f for f in os.listdir(directory) if f.endswith(".json")]
	for f in files:
		try:
			loaded = json.load(open(os.path.join(directory,f),"r"))
		except Exception as e:
			lineNum = re.search("line (\d+) ",str(e),0).group(1)
			error += "\nMalformed %s json in %s at line %s"%(kind,f,lineNum)
	return error

if __name__ == "__main__":	
	lf = open("err.log", "w")
	open("game.log", "w").close()
		
	if config.SPIRECOMM_PATH == "C:\\path\\to\\spirecomm":
		err_msg = "\nERROR: Please set the path to spirecomm in spirecomm/config.py\n"
		err_msg += "If you intend to push changes, run this command after editing your path:\n"
		err_msg += "    git update-index --assume-unchanged spirecomm/config.py"
		print(err_msg, file=lf, flush=True)
		print(err_msg)
		exit(1)

	#checks integrity of json files for cards and monsters
	err_msg = ""
	err_msg += verifyJSONFolder(os.path.join(config.SPIRECOMM_PATH,"spirecomm","ai","cards"),"card")
	err_msg += verifyJSONFolder(os.path.join(config.SPIRECOMM_PATH,"spirecomm","ai","monsters"),"monster")

	if err_msg != "":
		print(err_msg, file=lf, flush=True)
		print(err_msg)
		exit(1)
	
	try:
		launch_gui()
	except Exception as e:
		print(traceback.format_exc(), file=lf, flush=True)
