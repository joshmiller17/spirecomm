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

MSG_QUEUE = ["Init."]
MAX_HISTORY = 12
last_read = time.time()
TIMEOUT = 10
tk_root = None

class GUI(tk.Frame):

	def __init__(self, master=None):
		super().__init__(master)
		self.master = master
		self.create_widgets()
		read_thread = Thread(target=self.read)
		read_thread.start()

	def create_widgets(self):
		self.txt = tk.Text(self.master,borderwidth=3, relief="sunken")
		self.txt.config(font=("consolas",12), wrap='word', state="disabled")
		self.txt.grid(row=0,column=0,sticky="nsew",padx=2,pady=2)
		self.scroll = tk.Scrollbar(self.master, command=self.txt.yview)
		self.scroll.grid(row=0, column=1, sticky="nwes")
		self.txt['yscrollcommand'] = self.scroll.set

	def read(self, kill=False):
		time.sleep(1)
		if kill:
			time.sleep(2)
			self.master.destroy()
			exit(0)
		global MSG_QUEUE, last_read
		MSG_QUEUE = MSG_QUEUE[-MAX_HISTORY:]
		self.txt.config(state="normal")
		if len(MSG_QUEUE):
			last_read = time.time()
		else:
			self.txt.insert("end","Pong.\n")
		while len(MSG_QUEUE):
			self.txt.insert("end", MSG_QUEUE.pop() + "\n")
		if time.time() - last_read > TIMEOUT:
			self.txt.insert("end", "Timing out. Goodbye.\n")
			self.txt.config(state="disabled")
			self.read(kill=True)
		else:
			self.txt.config(state="disabled")
			self.read()
		
def shutdown():
	global tk_root
	tk_root.destroy()
	exit(1)
		
def run_gui():
	global tk_root
	tk_root = tk.Tk()
	tk_root.title("AI Debug")
	tk_root.protocol("WM_DELETE_WINDOW", shutdown)
	tk_root.grid_rowconfigure(0, weight=1)
	tk_root.grid_columnconfigure(0, weight=1)
	app = GUI(master=tk_root)
	agent_thread = Thread(target=run_agent)
	#agent_thread.start()
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