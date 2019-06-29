DEBUFFS = [
	"Bias",
	"Confused",
	"Constricted",
	"Dexterity Down",
	"Draw Reduction",
	"Entangled",
	"Frail",
	"Hex",
	"No Draw",
	"No Block",
	"Strength Down",
	"Vulnerable",
	"Weakened", # Weak?
	"Wraith Form"
]

class Power:

	def __init__(self, power_id, name, amount):
		self.power_id = power_id
		self.power_name = name
		self.amount = amount
		self.is_debuff = self.power_name in DEBUFFS

	@classmethod
	def from_json(cls, json_object):
		return cls(json_object["id"], json_object["name"], json_object["amount"])

	def __eq__(self, other):
		return self.power_id == other.power_id and self.amount == other.amount
		
	def __hash__(self):
		return hash(str(self.power_id))