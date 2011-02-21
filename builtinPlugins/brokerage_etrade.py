from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "E*Trade"
	
	def getUrl(self):
		return "https://ofx.etrade.com/cgi-ofx/etradeofx"
	
	def getOrg(self):
		return "E*TRADE"
	
	def getFid(self):
		return "9999"
	
	def getBrokerId(self):
		return "vanguard.com"
	
	def getNotes(self):
		return []

	def preParseTransaction(self, trans):
		retTrans = False

		# Turn some invbanktrn into deposits
		if trans.keyEqual("trntype", "other") and trans.keyContains("memo", "b2b - transfer from"):
			trans["trntype"] = "dep"

		return retTrans
