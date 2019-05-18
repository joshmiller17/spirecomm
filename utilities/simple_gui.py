import os
import collections
import itertools
import datetime
import sys
import time
import traceback
import threading

import spirecomm.communication.coordinator as coord
from spirecomm.ai.agent import SimpleAgent
from spirecomm.spire.character import PlayerClass
from spirecomm.ai.agent import SimpleAgent

os.environ["KIVY_NO_CONSOLELOG"] = "1"

from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window


class Base(BoxLayout):

	def __init__(self, coordinator, agent, f):
		super().__init__(orientation='vertical')
		self.coordinator = coordinator
		self.agent = agent
		self.log = f
		self.last_comm = ""
		self.paused = False
		print("Base: Init", file=self.log, flush=True)

		self.input_text = TextInput(size_hint=(1, 10))
		self.input_text.text = ""
		self.input_text.readonly = True
		self.add_widget(self.input_text)

		self.history_text = TextInput(size_hint=(1, 2))
		self.add_widget(self.history_text)

		self.output_text = TextInput(size_hint=(1, 1))
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

		self.max_history_lines = 5
		self.history_lines = collections.deque(maxlen=self.max_history_lines)

		Window.bind(on_key_up=self.key_callback)

	def do_communication(self, dt):
		if self.paused: # FIXME at some point, reconfigure pause to just halt everything maybe?
			return
		new_msg = self.agent.get_next_msg()
		if new_msg != "":
			self.input_text.text += self.agent.get_next_msg() + "\n"
		comm_msg = self.coordinator.view_last_msg()
		if comm_msg != self.last_comm:
			self.input_text.text += comm_msg + "\n"
			self.last_comm = comm_msg
		action_msg = self.coordinator.get_action_played()
		if action_msg is not None:
			self.input_text.text += str(action_msg) + "\n"
		#message = self.coordinator.get_next_raw_message()
		#if message is not None:
		#	self.input_text.text = message + '\n' + self.agent.get_next_msg()
		#self.coordinator.execute_next_action_if_ready()

	def do_pause(self, instance=None):
		self.paused = True
	
	def do_resume(self, instance=None):
		self.paused = False
		
	def send_output(self, instance=None, text=None):
		if text is None:
			text = self.output_text.text
		text = text.strip()
		if not self.handle_debug_cmds(text):
			print(text, end='\n', flush=True)
		self.history_lines.append(text)
		self.history_text.text = "\n".join(self.history_lines)
		self.output_text.text = ""

	def key_callback(self, window, keycode, *args):
		if keycode == 13:
			self.send_output()
			
	# Returns True if message was a debug command to execute,
	# False if we should print out for CommMod
	def handle_debug_cmds(self, msg):
	
		if msg == "threadcheck":
			for thread in threading.enumerate():
				print(thread, file=self.log, flush=True)
				print(thread.isAlive(), file=self.log, flush=True)
			return True
			
		if msg == "resend":
			self.coordinator.re_execute_last_action()
			self.coordinator.receive_game_state_update()
			return True
			
		if msg == "clear":
			self.input_text.text = ""
			return True
			
		return False


class CommunicationApp(App):

	def __init__(self, coordinator, agent, f):
		super().__init__()
		self.coordinator = coordinator
		self.agent = agent
		self.log = f
		print("Kivy: Init", file=self.log, flush=True)

	def build(self):
		base = Base(self.coordinator, self.agent, self.log)
		Clock.schedule_interval(base.do_communication, 1.0 / 60.0)
		return base

		
def run_agent(f, communication_coordinator):
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
	agent_thread.daemon = True
	print("Agent: Init", file=f, flush=True)
	agent_thread.start()
	print("Agent: Starting", file=f, flush=True)
	print("GUI: Starting mainloop", file=f, flush=True)
	CommunicationApp(communication_coordinator, agent, f).run()
	

if __name__ == "__main__":	
	lf = open("err.log", "w")
	try:
		launch_gui()
	except Exception as e:
		print(traceback.format_exc(), file=lf, flush=True)
