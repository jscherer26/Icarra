from brokerage import *

class Brokerage(BrokerageBase):
	def getName(self):
		return "Scottrade"
	
	def getUrl(self):
		return "https://ofxstl.scottsave.com"
	
	def getOrg(self):
		return "Scottrade"
	
	def getFid(self):
		return "777"
	
	def getBrokerId(self):
		return "www.scottrade.com"
	
	def getNotes(self):
		return ["Set Username to your account number", "Automatically imports all transactions"]
	
	def preParseTransaction(self, trans):
		retTrans = False
		
		if trans.keyEqual("trntype", "other") and trans.keyEqual("name", "cash adjustment"):
			# Scottrade cash adjustment
			retTrans = Transaction(
				trans["fitid"],
				"__CASH__",
				Transaction.ofxDateToSql(trans["dtposted"]),
				Transaction.adjustment,
				float(trans["trnamt"]))
		elif trans.keyEqual("trntype", "other") and trans.hasKey("memo") and trans["memo"][:13].upper() == "DEPOSIT CHECK":
			# Scottrade cash adjustment
			retTrans = Transaction(
				trans["fitid"],
				"__CASH__",
				Transaction.ofxDateToSql(trans["dtposted"]),
				Transaction.deposit,
				float(trans["trnamt"]))
		
		return retTrans
