# Copyright (c) 2006-2010, Jesse Liesch
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE IMPLIED
# DISCLAIMED. IN NO EVENT SHALL JESSE LIESCH BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Import transactions.  Can fail due to threading.
imported = False
while not imported:
	try:
		import datetime
		datetime.datetime.strptime("2000", "%Y")
		imported = True
	except Exception, e:
		pass

import locale

def dateDict(date):
	return {"y": date.year, "m": date.month, "d": date.day}

class Transaction:
	# Define transaction type
	deposit = 0
	withdrawal = 1
	expense = 2
	buy = 3
	sell = 4
	split = 5
	dividend = 6
	adjustment = 7
	stockDividend = 8
	dividendReinvest = 9
	spinoff = 10
	transferIn = 11
	transferOut = 12
	short = 13
	cover = 14
	tickerChange = 15
	numTransactionTypes = 16
	
	# Subtypes for dividend
	ordinary = 1
	qualified = 2
	capitalGainShortTerm = 3
	capitalGainLongTerm = 4
	returnOfCapital = 5

	def __init__(self, uniqueId, ticker, date, transactionType, amount = False, shares = False, pricePerShare = False, fee = False, edited = False, deleted = False, ticker2 = False, subType = False, auto = False):
		self.uniqueId = uniqueId
		self.setTicker(ticker)
		self.setTicker2(ticker2)
		self.setAuto(auto)
		if type(date) in [unicode, str]:
			self.date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
		elif type(date) == datetime.datetime:
			self.date = date
		else:
			raise Exception("Transaction date must be datetime type, is " + str(type(date)))
		self.type = transactionType
		self.subType = subType
		self.setTotal(amount)
		if shares and shares != "False":
			self.shares = float(shares)
		else:
			self.shares = False
		if pricePerShare and pricePerShare != "False":
			self.pricePerShare = float(pricePerShare)
		else:
			self.pricePerShare = False
		if fee and fee != "False":
			self.fee = float(fee)
		else:
			self.fee = False
		if edited == "True":
			self.edited = True
		else:
			self.edited = False
		if deleted == "True":
			self.deleted = True
		else:
			self.deleted = False
	
	def __str__(self):
		str = self.formatDate() + " " + self.formatTicker() + " " + self.formatType()
		if self.ticker2:
			str += " ticker2=" + self.formatTicker2()
		if self.shares:
			str += " shares=" + self.formatShares()
		if self.total:
			str += " total=" + self.formatTotal()
		if self.fee:
			str += " fee=" + self.formatFee()
		if self.edited:
			str += " (edited)"
		if self.deleted:
			str += " (deleted)"
		return str
	
	def __cmp__(self, other):
		# Check for false
		if other == False:
			return 1
		
		# First sort by date
		if self.date < other.date:
			return 1
		if self.date > other.date:
			return -1
		
		# Next sort by
		#     Deposit
		#     Buy
		#     Sell
		#     Withdrawal
		myRank = Transaction.getTransactionOrdering(self.type)
		otherRank = Transaction.getTransactionOrdering(other.type)
		if myRank < otherRank:
			return 1
		elif myRank > otherRank:
			return -1
		
		return 0
	
	def setDate(self, date):
		self.date = date

	def setTicker(self, ticker):
		self.ticker = ticker.upper()

	def setTicker2(self, ticker2):
		if ticker2 == "False":
			self.ticker2 = False
		elif type(ticker2) == bool:
			self.ticker2 = bool(ticker2)
		elif isinstance(ticker2, str) or isinstance(ticker2, unicode):
			self.ticker2 = ticker2.upper()
		else:
			self.ticker2 = False

	def setAuto(self, auto):
		if auto == "False":
			self.auto = False
		elif auto == "True":
			self.auto = True
		elif type(auto) == bool:
			self.auto = bool(auto)
		else:
			self.auto = False

	def setType(self, type):
		if isinstance(type, int):
			self.type = type
		else:
			self.type = self.getType(type)
	
	def setSubType(self, subType):
		self.subType = subType

	def setShares(self, shares):
		self.shares = float(shares)
	
	def setPricePerShare(self, pps):
		self.pricePerShare = pps

	def setFee(self, fee):
		self.fee = fee

	def setTotal(self, total):
		if total and total != "False":
			self.total = float(total)
		else:
			self.total = False
	
	def setEdited(self):
		self.edited = True

	def setDeleted(self, deleted = True):
		self.edited = True
		self.deleted = deleted

	@staticmethod
	def ofxDateToSql(date):
		if len(date) >= 14:
			return date[:4] + "-" + date[4:6] + "-" + date[6:8] + " " + date[8:10] + ":" + date[10:12] + ":" + date[12:14]
		elif len(date) == 8:
			return date[:4] + "-" + date[4:6] + "-" + date[6:8] + " 00:00:00"
		else:
			raise Exception("unknown date size")
	
	@staticmethod
	def ameritradeDateToSql(date):
		return date[6:10] + "-" + date[:2] + "-" + date[3:5] + " 00:00:00"
	
	@staticmethod
	def forEdit():
		list = [Transaction.deposit, Transaction.withdrawal, Transaction.buy, Transaction.sell, Transaction.split, Transaction.dividend, Transaction.dividendReinvest, Transaction.expense, Transaction.adjustment, Transaction.stockDividend, Transaction.spinoff, Transaction.tickerChange, Transaction.transferIn, Transaction.transferOut, Transaction.short, Transaction.cover]
		assert(len(list) == Transaction.numTransactionTypes)
		return list
	
	@staticmethod
	def fieldsForTransaction(type):
		if type == Transaction.deposit or type == Transaction.withdrawal:
			return ["date", "fee", "total"]
		elif type == Transaction.expense:
			return ["date", "ticker", "fee"]
		elif type in [Transaction.buy, Transaction.sell, Transaction.dividendReinvest, Transaction.transferIn, Transaction.transferOut]:
			return ["date", "fee", "ticker", "shares", "pricePerShare"]
		elif type == Transaction.split or type == Transaction.dividend:
			return ["date", "fee", "ticker", "total"]
		elif type == Transaction.adjustment:
			return ["date", "ticker", "total"]
		elif type == Transaction.stockDividend:
			return ["date", "fee", "ticker", "shares"]
		elif type == Transaction.spinoff:
			return ["date", "fee", "ticker", "ticker2", "shares"]
		elif type == Transaction.tickerChange:
			return ["date", "fee", "ticker", "ticker2", "shares"]
		else:
			return []

	def formatTicker(self):
		if self.ticker == "__CASH__":
			return "Cash"
		elif self.ticker2:
			return self.ticker + " -> " + self.ticker2
		else:
			return self.ticker
	
	def formatTicker1(self):
		if self.ticker == "__CASH__":
			return "Cash"
		else:
			return self.ticker

	def formatTicker2(self):
		if self.ticker2 == "__CASH__":
			return "Cash"
		else:
			return self.ticker2

	def formatDate(self):
		return str(self.date.month) + "/" + str(self.date.day) + "/" + str(self.date.year)
	
	def dateDict(self):
		return dateDict(self.date)
	
	def getDate(self):
		return self.date
	
	@staticmethod
	def getTypeString(type):
		if type == Transaction.deposit:
			return "Deposit"
		elif type == Transaction.withdrawal:
			return "Withdrawal"
		elif type == Transaction.expense:
			return "Expense"
		elif type == Transaction.buy:
			return "Buy"
		elif type == Transaction.sell:
			return "Sell"
		elif type == Transaction.split:
			return "Split"
		elif type == Transaction.dividend:
			return "Dividend"
		elif type == Transaction.adjustment:
			return "Adjustment"
		elif type == Transaction.stockDividend:
			return "Stock Dividend"
		elif type == Transaction.dividendReinvest:
			return "Dividend Reinvest"
		elif type == Transaction.spinoff:
			return "Spinoff"
		elif type == Transaction.tickerChange:
			return "Ticker Change"
		elif type == Transaction.transferIn:
			return "Transfer In"
		elif type == Transaction.transferOut:
			return "Transfer Out"
		elif type == Transaction.short:
			return "Short"
		elif type == Transaction.cover:
			return "Cover"
		else:
			return "???"
	
	@staticmethod
	def getType(string):
		if string == "Deposit":
			return Transaction.deposit
		elif string == "Withdrawal":
			return Transaction.withdrawal
		elif string == "Expense":
			return Transaction.expense
		elif string == "Buy":
			return Transaction.buy
		elif string == "Sell":
			return Transaction.sell
		elif string == "Split":
			return Transaction.split
		elif string == "Dividend":
			return Transaction.dividend
		elif string == "Adjustment":
			return Transaction.adjustment
		elif string == "Stock Dividend":
			return Transaction.stockDividend
		elif string == "Dividend Reinvest":
			return Transaction.dividendReinvest
		elif string == "Spinoff":
			return Transaction.spinoff
		elif string == "Ticker Change":
			return Transaction.tickerChange
		elif string == "Transfer In":
			return Transaction.transferIn
		elif string == "Transfer Out":
			return Transaction.transferOut
		else:
			return False
	
	@staticmethod
	def getTransactionOrdering(type):
		if type in [Transaction.deposit, Transaction.transferIn]:
			return 0
		elif type in [Transaction.buy, Transaction.dividendReinvest]:
			return 1
		elif type in [Transaction.split, Transaction.dividend, Transaction.spinoff, Transaction.tickerChange]:
			return 2
		elif type in [Transaction.sell]:
			return 99
		elif type in [Transaction.withdrawal, Transaction.transferOut]:
			return 100
		else:
			return 50

	def hasShares(self):
		return "shares" in self.fieldsForTransaction(self.type)

	def hasPricePerShare(self):
		return self.type in [Transaction.buy, Transaction.sell, Transaction.dividendReinvest]
	
	def formatType(self):
		return self.getTypeString(self.type)
	
	def formatShares(self):
		return self.formatFloat(abs(self.shares))
	
	@staticmethod
	def formatFloat(value, commas = False):
		'''
		Format a floating point value without any trailing 0s in the decimal portion
		'''
		if value == 0.0:
			return "0.0"
		if value == False:
			return ""
		
		decimals = 0
		multiply = 1
		while decimals < 6:
			diff = round(value * multiply) - value * multiply
			
			if abs(diff) < 1.0e-6:
				break
			
			decimals += 1
			multiply *= 10
		format = "%%.%df" % decimals
		if commas:
			return locale.format(format, value, True)
		else:
			return format % value

	@staticmethod
	def formatDollar(value):
		'''
		Format a floating point value as a dollar value
		'''

		return "$" + locale.format("%.2f", value, True)

	def formatPricePerShare(self):
		if not self.pricePerShare or self.pricePerShare == "False":
			return ""
		return self.formatDollar(self.pricePerShare)

	def formatFee(self):
		if not self.fee or self.fee == "False":
			return ""
		return "$" + str(self.fee)

	def formatTotal(self):
		if not self.total:
			return ""
		if self.type in [Transaction.split]:
			return self.splitValueToString(self.total)
		else:
			return self.formatDollar(self.total)
	
	@staticmethod
	def splitValueToString(value):
		# Determine split value
		splitVal = "?-?"
		if value == 1:
			splitVal = "1-1"
		if value > 1:
			reversed = False
		else:
			value = 1.0 / value
			reversed = True

		# guess denom from 1-10
		min = 1.0e6
		minDenom = -1
		for denom in range(1, 11):
			num = value * denom
			diff = abs(num - round(num))
			if diff < min * 0.0001:
				minDenom = denom
				min = diff
		if reversed:
			splitVal = "%d-%d" % (minDenom, round(value * minDenom))
		else:
			splitVal = "%d-%d" % (round(value * minDenom), minDenom)

		return splitVal
	
	def save(self, db):
		data = {
			"uniqueId": self.uniqueId,
			"ticker": self.ticker,
			"ticker2": self.ticker2,
			"type": self.type,
			"subType": self.subType,
			"date": self.date,
			"shares": self.shares,
			"pricePerShare": self.pricePerShare,
			"fee": self.fee,
			"total": self.total,
			"edited": self.edited,
			"deleted": self.deleted,
			"auto": self.auto
		};

		# If uniqueId is supplied make it the criteria for update
		# Otherwise use the entire transaction
		if self.uniqueId:
			on = {"uniqueId": self.uniqueId}
		else:
			on = data
		
		return db.insertOrUpdate("transactions", data, on)
	
	# Returns False if no error, string if error
	def checkError(self):
		fields = self.fieldsForTransaction(self.type)

		if self.type in [Transaction.deposit, Transaction.withdrawal]:
			self.ticker = "__CASH__"
	
		error = ""
		if "ticker" in fields:
			if not self.ticker:
				error += "Ticker is required."
		if "shares" in fields:
			if self.shares == 0:
				error += "Shares value is required."
		if "fee" in fields:
			if not self.fee:
				self.fee = 0
		if "total" in fields:
			if self.total == 0:
				error += "Total value is required."

		if error:
			return error
		else:
			return False
