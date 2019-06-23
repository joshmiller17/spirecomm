import py_trees
import json

from spirecomm.communication.action import *

# This is the Template class from which all StS Behaviours inherit
# It also includes the original comments for what should go in each method
class DefaultBehaviour(py_trees.behaviour.Behaviour):
	def __init__(self, name, agent):
		"""
		Minimal one-time initialisation. A good rule of thumb is
		to only include the initialisation relevant for being able
		to insert this behaviour in a tree for offline rendering to
		dot graphs.

		Other one-time initialisation requirements should be met via
		the setup() method.
		"""
		super(DefaultBehaviour, self).__init__(name)
		self.agent = agent
		
	def log(self, msg, debug=4):
		self.agent.log(str(self.name) + " [" + str(self.__class__.__name__) + "]: " + msg, debug=debug)

	def setup(self):
		"""
		When is this called?
		  This function should be either manually called by your program
		  to setup this behaviour alone, or more commonly, via
		  :meth:`~py_trees.behaviour.Behaviour.setup_with_descendants`
		  or :meth:`~py_trees.trees.BehaviourTree.setup`, both of which
		  will iterate over this behaviour, it's children (it's children's
		  children ...) calling :meth:`~py_trees.behaviour.Behaviour.setup`
		  on each in turn.

		  If you have vital initialisation necessary to the success
		  execution of your behaviour, put a guard in your
		  :meth:`~py_trees.behaviour.Behaviour.initialise` method
		  to protect against entry without having been setup.

		What to do here?
		  Delayed one-time initialisation that would otherwise interfere
		  with offline rendering of this behaviour in a tree to dot graph
		  or validation of the behaviour's configuration.

		  Good examples include:

		  - Hardware or driver initialisation
		  - Middleware initialisation (e.g. ROS pubs/subs/services)
		  - A parallel checking for a valid policy configuration after
			children have been added or removed

		"""
		pass

	def initialise(self):
		"""
		When is this called?
		  The first time your behaviour is ticked and anytime the
		  status is not RUNNING thereafter.

		What to do here?
		  Any initialisation you need before putting your behaviour
		  to work.
		"""
		pass

	def update(self):
		"""
		When is this called?
		  Every time your behaviour is ticked.

		What to do here?
		  - Triggering, checking, monitoring. Anything...but do not block!
		  - Set a feedback message
		  - return a py_trees.common.Status.[RUNNING, SUCCESS, FAILURE]
		"""
		return py_trees.common.Status.SUCCESS

	def terminate(self, new_status):
		"""
		When is this called?
		   Whenever your behaviour switches to a non-running state.
			- SUCCESS || FAILURE : your behaviour's work cycle has finished
			- INVALID : a higher priority branch has interrupted, or shutting down
		"""
		pass

#like Sequence, but with a to_json method
class SequenceBehaviour(py_trees.composites.Sequence):

	def to_json(self):
		attrDict = {}
		attrDict["name"] = self.name
		attrDict["class"] = "SequenceBehaviour"
		attrDict["children"] = [c.to_json() for c in self.iterate(direct_descendants=True) if c != self]
		return attrDict

	@classmethod
	def fromDict(cls,d,agent):
		ret = cls(d["name"])
		for child in d["children"]:
			childClass = child["class"]
			ret.add_child(classMap[childClass].fromDict(child,agent))
		return ret

#like Selector, but with a to_json method
class SelectorBehaviour(py_trees.composites.Selector):

	def to_json(self):
		attrDict = {}
		attrDict["name"] = self.name
		attrDict["class"] = "SelectorBehaviour"
		attrDict["children"] = [c.to_json() for c in self.iterate(direct_descendants=True) if c != self]
		return attrDict

	@classmethod
	def fromDict(cls,d,agent):
		ret = cls(d["name"])
		for child in d["children"]:
			childClass = child["class"]
			ret.add_child(classMap[childClass].fromDict(child,agent))
		return ret

# A test-only class, returns the default logic of what the original AI would have done
class TestBehaviour(DefaultBehaviour):
	
	def update(self):
		self.log("tick", debug=6)
		self.agent.cmd_queue.append(self.agent.default_logic(self.agent.blackboard.game))
		return py_trees.common.Status.SUCCESS

	def to_json(self):
		attrDict = {}
		attrDict["name"] = self.name
		attrDict["class"] = "TestBehaviour"
		attrDict["children"] = [c.to_json() for c in self.iterate(direct_descendants=True) if c != self]
		return attrDict

	@classmethod
	def fromDict(cls,d,agent):
		ret = cls(d["name"],agent)
		for child in d["children"]:
			childClass = child["class"]
			ret.add_child(classMap[childClass].fromDict(child,agent))
		return ret
		
# Temporary behaviour, remove when behaviour tree is more fully realized
# calls a custom function to handle complex logic for us
class CustomBehaviour(DefaultBehaviour):

	def __init__(self, name, agent, function):
		super(CustomBehaviour, self).__init__(name, agent)
		self.function = function
		
	def update(self):
		self.agent.cmd_queue.append(getattr(self.agent, self.function)())
		return py_trees.common.Status.SUCCESS
	
	def to_json(self):
		attrDict = {}
		attrDict["name"] = self.name
		attrDict["class"] = "CustomBehaviour"
		attrDict["function"] = self.function
		attrDict["children"] = [c.to_json() for c in self.iterate(direct_descendants=True) if c != self]
		return attrDict

	@classmethod
	def fromDict(cls,d,agent):
		ret = cls(d["name"],agent,d["function"])
		for child in d["children"]:
			childClass = child["class"]
			ret.add_child(classMap[childClass].fromDict(child,agent))
		return ret
	
# Returns success iff a blackboard.game boolean is true
# To invert this logic, set success=False: behaviour will then return true iff bool is false
class BoolCheckBehaviour(DefaultBehaviour):

	def __init__(self, name, agent, boolean, success=True):
		super(BoolCheckBehaviour, self).__init__(name, agent)
		self.boolean = boolean
		self.success = success
	
	def update(self):
		value = getattr(self.agent.blackboard.game, self.boolean)
		ret = value if self.success else not value # invert bool if that's what we want to check
		retStr = "SUCCESS" if ret else "FAILURE"
		self.log(str(self.boolean) + " is " + str(value) + ": " + retStr, debug=6)
		return py_trees.common.Status.SUCCESS if ret else py_trees.common.Status.FAILURE

	def to_json(self):
		attrDict = {}
		attrDict["name"] = self.name
		attrDict["class"] = "BoolCheckBehaviour"
		attrDict["boolean"] = self.boolean
		attrDict["success"] = self.success
		attrDict["children"] = [c.to_json() for c in self.iterate(direct_descendants=True) if c != self]
		return attrDict

	@classmethod
	def fromDict(cls,d,agent):
		ret = cls(d["name"],agent,d["boolean"],d["success"])
		for child in d["children"]:
			childClass = child["class"]
			ret.add_child(classMap[childClass].fromDict(child,agent))
		return ret
		
# Returns success iff values are equal
# To invert this logic, set success=False: behaviour will then return true iff values are not equal
class EqualityCheckBehaviour(BoolCheckBehaviour):

	def __init__(self, name, agent, first, second, success=True):
		super(EqualityCheckBehaviour, self).__init__(name, agent, first, success)
		self.first = first
		self.second = second
	
	def update(self):
		value = True if self.first == self.second else False
		ret = value if self.success else not value # invert bool if that's what we want to check
		retStr = "SUCCESS" if ret else "FAILURE"
		logStr = str(self.first) + " "
		if value:
			logStr += "== "
		else:
			logStr += "!= "
		logStr += str(self.second) + ": " + retStr
		self.log(logStr, debug=6)
		return py_trees.common.Status.SUCCESS if ret else py_trees.common.Status.FAILURE

	def to_json(self):
		attrDict = {}
		attrDict["name"] = self.name
		attrDict["class"] = "EqualityCheckBehaviour"
		attrDict["first"] = self.first
		attrDict["second"] = self.second
		attrDict["success"] = self.success
		attrDict["children"] = [c.to_json() for c in self.iterate(direct_descendants=True) if c != self]
		return attrDict

	@classmethod
	def fromDict(cls,d,agent):
		ret = cls(d["name"],agent,d["first"],d["second"],d["success"])
		for child in d["children"]:
			childClass = child["class"]
			ret.add_child(classMap[childClass].fromDict(child,agent))
		return ret
	
# Like EqualityCheck, but the first value comes from game, second is given at init
class CompareToConstBehaviour(EqualityCheckBehaviour):
	
	def __init__(self, name, agent, attr, static, success=True):
		super(CompareToConstBehaviour, self).__init__(name, agent, attr, static, success)
		self.attr = attr
		self.static = static
		
	def update(self):
		self.first = getattr(self.agent.blackboard.game, self.attr)
		return super().update()

	def to_json(self):
		attrDict = {}
		attrDict["name"] = self.name
		attrDict["class"] = "CompareToConstBehaviour"
		attrDict["attr"] = self.attr
		attrDict["static"] = str(self.static)
		attrDict["success"] = self.success
		attrDict["children"] = [c.to_json() for c in self.iterate(direct_descendants=True) if c != self]
		return attrDict

	@classmethod
	def fromDict(cls,d,agent):
		ret = cls(d["name"],agent,d["attr"],d["static"],d["success"])
		for child in d["children"]:
			childClass = child["class"]
			ret.add_child(classMap[childClass].fromDict(child,agent))
		return ret

	
# The default ActionBehaviour, implemented by more complex action behaviours like Play
# On update, it appends its action to the queue and returns SUCCESS
class ActionBehaviour(DefaultBehaviour):

	def __init__(self, name, agent, action, params=[]):
		super(ActionBehaviour, self).__init__(name, agent)
		self.action = action
		self.params = params

	def update(self):
		action_class = globals()[self.action]
		command = action_class(*self.params)
		self.agent.cmd_queue.append(command)
		return py_trees.common.Status.SUCCESS

	def to_json(self):
		attrDict = {}
		attrDict["name"] = self.name
		attrDict["class"] = "ActionBehaviour"
		attrDict["action"] = self.action
		attrDict["params"] = self.params
		attrDict["children"] = [c.to_json() for c in self.iterate(direct_descendants=True) if c != self]
		return attrDict
	
	@classmethod
	def fromDict(cls,d,agent):
		ret = cls(d["name"],agent,d["action"],d["params"])
		for child in d["children"]:
			childClass = child["class"]
			ret.add_child(classMap[childClass].fromDict(child,agent))
		return ret
		
		
		
classMap = {"SequenceBehaviour":SequenceBehaviour, \
			"SelectorBehaviour":SelectorBehaviour, \
			"TestBehaviour":TestBehaviour,\
			"BoolCheckBehaviour":BoolCheckBehaviour, \
			"EqualityCheckBehaviour":EqualityCheckBehaviour, \
			"EqualityCheckBehaviour":EqualityCheckBehaviour, \
			"CompareToConstBehaviour":CompareToConstBehaviour, \
			"ActionBehaviour":ActionBehaviour}
