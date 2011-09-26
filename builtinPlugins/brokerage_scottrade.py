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
		elif trans.keyEqual("trntype", "other") and trans.hasKey("memo") and trans["memo"].startswith("DEPOSIT CHECK"):
			# Scottrade cash adjustment
			retTrans = Transaction(
				trans["fitid"],
				"__CASH__",
				Transaction.ofxDateToSql(trans["dtposted"]),
				Transaction.deposit,
				float(trans["trnamt"]))
		elif trans.keyEqual("type", "income") and trans.hasKey("memo") and trans["memo"].startswith("Tax-exempt Dividend/Spinoff of"):
			# Stock dividend with memo "Tax-exempt Dividend/Spinoff of 12345 shares of TICKER"
			shares = float(trans["memo"].split(' ')[3])
			retTrans = Transaction(
				trans["fitid"],
				trans["ticker"],
				Transaction.ofxDateToSql(trans["dttrade"]),
				Transaction.stockDividend,
				shares = shares)
		
		return retTrans
