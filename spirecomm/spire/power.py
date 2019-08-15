DEBUFFS = [
	"Bias",
	"Confused",
	"Constricted",
	"Dexterity Down",
	"Draw Reduction",
	"Entangled",
	"Frail",
	"Focus Down",
	"Hex",
	"No Draw",
	"No Block",
	"Shackles",
	"Strength Down",
	"Vulnerable",
	"Weakened",
	"Wraith Form"
]

BUFFS = ["Ritual", "Strength", "Dexterity", "Incantation", "Enrage", "Metallicize", "SadisticNature", "Juggernaut", "DoubleTap", "DemonForm", "DarkEmbrace", "Brutality", "Berserk", "Rage", "Feel No Pain", "Flame Barrier", "Corruption", "Combust", "Fire Breathing", "Mayhem"]

class Power:

	def __init__(self, power_id, name, amount):
		self.power_id = power_id # mostly english name, sometimes equal to power_name
		self.power_name = name
		self.amount = amount
		self.is_debuff = self.power_name in DEBUFFS

	@classmethod
	def from_json(cls, json_object):
		return cls(json_object["id"], json_object["name"], json_object["amount"])

	def __str__(self):
		return self.power_name + str(self.amount) # + "<" + str(self.power_id) + "> " 
	
	# note, for __eq__ and hash, changed from id to name because we don't know the ids of the powers when simming
	def __eq__(self, other):
		return self.power_name == other.power_name and self.amount == other.amount
		
	def __hash__(self):
		return hash(str(self.power_name))