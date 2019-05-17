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
MAX_HISTORY = 12

class GUI(tk.Frame):

	def __init__(self, master=None):
		super().__init__(master)
		self.master = master
		self.create_widgets()
		read_thread = Thread(target=self.read)
		read_thread.start()

	def create_widgets(self):
		self.txt = tk.Text(self.master,borderwidth=3, relief="sunken")
		self.txt.config(font=("consolas",12), wrap='word',state=DISABLED)
		self.txt.grid(row=0,column=0,sticky="nsew",padx=2,pady=2)
		self.scroll = tk.Scrollbar(self.master, command=self.txt.yview)
		self.scroll.grid(row=0, column=1, sticky="nwes")
		self.txt['yscrollcommand'] = self.scroll.set

	def read(self):
		global MSG_QUEUE
		MSG_QUEUE = MSG_QUEUE[-MAX_HISTORY:]
		print("MSG_QUEUE: ")
		print(MSG_QUEUE)
		new_msg = ""
		while len(MSG_QUEUE):
			self.txt.insert(END, MSG_QUEUE.pop())
			self.txt.insert(END, '\n')
		time.sleep(0.5)
		self.read()
		
		
def run_gui():
	root = tk.Tk()
	root.protocol("WM_DELETE_WINDOW", root.quit)
	frame = tk.Frame(root, width=600, height=400)
	frame.pack(fill="both", expand=True)
	frame.grid_propagate(False)
	frame.grid_rowconfigure(0, weight=1)
	frame.grid_columnconfigure(0, weight=1)
	app = GUI(master=frame)
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