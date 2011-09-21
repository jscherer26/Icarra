from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "Ameritrade"
	
	def getUrl(self):
		return "https://ofxs.ameritrade.com/cgi-bin/apps/OFX"
	
	def getOrg(self):
		return "ameritrade.com"
	
	def getFid(self):
		return "5024"
	
	def getBrokerId(self):
		return "ameritrade.com"
	
	def getNotes(self):
		return ["Username is case sensitive",
		"Automatically imports 2 years of transactions",
		"Older transactions may be imported from the\nAmeritrade website.  See documentation for more details.",
		"Imported stock split transactions may have incorrect data"]
	
	def massageTransaction(self, trans):
		# Use __CASH__ if ticker is MMDAx (money market)
		if trans.ticker.upper()[0:4] == "MMDA" and len(trans.ticker) > 4:
			trans.ticker = "__CASH__"
		elif trans.ticker.upper() in ["IDA", "ZTD82"]:
			trans.ticker = "__CASH__"
