import os
import collections
import itertools
import datetime
import sys

import spirecomm.communication.coordinator as coord
from spirecomm.ai.agent import SimpleAgent
from spirecomm.spire.character import PlayerClass
from spirecomm.ai.agent import SimpleAgent

os.environ["KIVY_NO_CONSOLELOG"] = "1"

from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window


class Base(BoxLayout):

	def __init__(self, coordinator, agent):
		super().__init__(orientation='vertical')
		self.coordinator = coordinator
		self.agent = agent

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

		self.max_history_lines = 5
		self.history_lines = collections.deque(maxlen=self.max_history_lines)

		Window.bind(on_key_up=self.key_callback)

	def do_communication(self, dt):
		message = self.coordinator.get_next_raw_message()
		if message is not None:
			self.input_text.text = message + '\n' + self.agent.get_next_msg()
		self.coordinator.execute_next_action_if_ready()

	def send_output(self, instance=None, text=None):
		if text is None:
			text = self.output_text.text
		text = text.strip()
		print(text, end='\n', flush=True)
		self.history_lines.append(text)
		self.history_text.text = "\n".join(self.history_lines)
		self.output_text.text = ""

	def key_callback(self, window, keycode, *args):
		if keycode == 13:
			self.send_output()


class CommunicationApp(App):

	def __init__(self, coordinator, agent):
		super().__init__()
		self.coordinator = coordinator
		self.agent = agent
		

	def build(self):
		base = Base(self.coordinator, self.agent)
		Clock.schedule_interval(base.do_communication, 1.0 / 60.0)
		return base


def launch_gui():
	agent = SimpleAgent()
	communication_coordinator = coord.Coordinator()
	communication_coordinator.signal_ready()
	communication_coordinator.register_command_error_callback(agent.handle_error)
	communication_coordinator.register_state_change_callback(agent.get_next_action_in_game)
	communication_coordinator.register_out_of_game_callback(agent.get_next_action_out_of_game)
	CommunicationApp(communication_coordinator, agent).run()
	
	# Play games forever, cycling through the various classes
	#for chosen_class in itertools.cycle(PlayerClass):
	#	agent.change_class(chosen_class)
	#	result = coordinator.play_one_game(chosen_class)

if __name__ == "__main__":	
	launch_gui()
