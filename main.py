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

import tkinter as tk
# os.environ["KIVY_NO_CONSOLELOG"] = "1"

# from kivy.app import App
# from kivy.uix.textinput import TextInput
# from kivy.uix.boxlayout import BoxLayout
# from kivy.uix.button import Button
# from kivy.clock import Clock
# from kivy.core.window import Window

MSG_QUEUE = []

class GUI(tk.Frame):

	def __init__(self, master=None):
		super().__init__(master)
		self.master = master
		self.pack()
		self.create_widgets()
		read_thread = Thread(target=self.read)
		read_thread.start()

	def create_widgets(self):
		self.output = tk.Label(self)
		self.output.configure(text="Init", justify="left")
		self.output.pack(side="top")

	def write(self, message):
		new_msg = self.output.cget("text") + "\n" + message
		self.output.configure(text=new_msg)
		
	def read(self):
		while (len(MSG_QUEUE)):
			msg = MSG_QUEUE.pop()
			self.write(msg)
		time.sleep(1)
		self.read()
		
def run_gui():
	root = tk.Tk()
	app = GUI(master=root)
	agent_thread = Thread(target=run_agent)
	agent_thread.start()
	app.mainloop()
		
def run_agent():
	agent = EvolvingAgent(queue=MSG_QUEUE, chosen_class=PlayerClass.IRONCLAD) # Start with just training on one class
	#agent = SimpleAgent(chosen_class=PlayerClass.THE_SILENT)
	coordinator = coord.Coordinator()
	coordinator.signal_ready()
	coordinator.register_command_error_callback(agent.handle_error)
	coordinator.register_state_change_callback(agent.get_next_action_in_game)
	coordinator.register_out_of_game_callback(agent.get_next_action_out_of_game)

	# Play games forever, cycling through the various classes
	for chosen_class in itertools.cycle(PlayerClass):
		#agent.change_class(chosen_class) # Start with just training on one class
		result = coordinator.play_one_game(chosen_class)

	

if __name__ == "__main__":
	run_gui()