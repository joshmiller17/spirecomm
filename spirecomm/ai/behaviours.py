import py_trees


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
		self.agent.log("[" + str(self.__class__.__name__) + "]: " + msg, debug=debug)

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

# A test-only class, returns the default logic of what the original AI would have done
class TestBehaviour(DefaultBehaviour):
	
	def update(self):
		self.log("tick", debug=6)
		self.agent.cmd_queue.append(self.agent.default_logic(self.agent.blackboard.game))
		return py_trees.common.Status.SUCCESS
	
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
		logStr += self.second + ": " + retStr
		self.log(logStr, debug=6)
		return py_trees.common.Status.SUCCESS if ret else py_trees.common.Status.FAILURE
	
# Like EqualityCheck, but the first value comes from game, second is given at init
class CompareToConstBehaviour(EqualityCheckBehaviour):
	
	def __init__(self, name, agent, attr, static, success=True):
		super(CompareToConstBehaviour, self).__init__(name, agent, attr, static, success)
		self.attr = attr
		self.static = static
		
	def update():
		self.first = getattr(self.agent.blackboard.game, self.attr)
		super().update()
	
# The default ActionBehaviour, implemented by more complex action behaviours like Play
# On update, it appends its action to the queue and returns SUCCESS
class ActionBehaviour(DefaultBehaviour):

	def __init__(self, name, agent, action):
		super(ActionBehaviour, self).__init__(name, agent)
		self.action = action

	def update(self):
		self.agent.cmd_queue.append(self.action)
		return py_trees.common.Status.SUCCESS
		