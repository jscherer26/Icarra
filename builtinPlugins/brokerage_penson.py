from brokerage import *

import re

class Brokerage(BrokerageBase):
	def getName(self):
		return "Penson Financial Services"
	
	def getUrl(self):
		return "https://ofx.penson.com"
	
	def getOrg(self):
		return "Penson Financial Services Inc"
	
	def getFid(self):
		return "10780"
	
	def getBrokerId(self):
		return "penson.com"
	
	def getNotes(self):
		return []
	
        def preParseTransaction(self, trans):
		retTrans = False

		# Convert INVBANKTRAN with TRNTYPE=OTHER to deposit if name is CASH JOURNAL: ACH DEPOSIT
		if trans.keyEqual("trntype", "other") and trans.keyEqual("name", "cash journal: ach deposit"):
			retTrans = Transaction(
				trans["fitid"],
				"__CASH__",
				Transaction.ofxDateToSql(trans["dtposted"]),
				Transaction.deposit,
				float(trans["trnamt"]))
		# Convert INVBANKTRAN with TRNTYPE=OTHER to cash interest if name is cash journal: *cr i*
		if trans.keyEqual("trntype", "other") and trans.keyContains("name", "cash journal:") and trans.keyContains("name", "cr i"):
			retTrans = Transaction(
				trans["fitid"],
				"__CASH__",
				Transaction.ofxDateToSql(trans["dtposted"]),
				Transaction.dividend,
				float(trans["trnamt"]))
		# Ignore transfers from cash to margin and vice versa
		if trans.keyEqual("trntype", "other") and trans.keyEqual("name", "cash journal: *from cash*"):
			return True
		if trans.keyEqual("trntype", "other") and trans.keyEqual("name", "cash journal: *to margin*"):
			return True


		return retTrans
