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
	# Options
	exercise = 16
	assign = 17
	buyToOpen = 18
	sellToClose = 19
	sellToOpen = 20
	buyToClose = 21
	expire = 22
	numTransactionTypes = 23
	
	# Subtypes for dividend
	ordinary = 1
	qualified = 2
	capitalGainShortTerm = 3
	capitalGainLongTerm = 4
	returnOfCapital = 5
	taxExempt = 6
	
	# Subtypes for option
	# Applies to buy, sell, short, buyToClose
	optionPut = 1
	optionCall = 2

	def __init__(self, uniqueId, ticker, date, transactionType, amount = False, shares = False, pricePerShare = False, fee = False, edited = False, deleted = False, ticker2 = False, subType = False, optionStrike = False, optionExpire = False, auto = False):
		# Icarra desktop app ids are in the form __N__ where N is unique (eg, __3__, __7__)
		# Icarra ids that have been synched with the server are in the form __SN__ where N is a unique number (eg, __S3__, __S7__)
		# Other ids may be supplied by the brokerage and are assumed to be unique
		if type(uniqueId) != bool:
			self.uniqueId = str(uniqueId)
		else:
			self.uniqueId = uniqueId
		self.setTicker(ticker)
		self.setTicker2(ticker2)
		self.setAuto(auto)
		if type(date) in [unicode, str]:
			self.date = Transaction.parseDate(date)
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
		
		if optionStrike and optionStrike != "False":
			self.optionStrike = float(optionStrike)
		else:
			self.optionStrike = False
		
		if optionExpire and optionExpire != "False":
			if type(optionExpire) in [unicode, str]:
				self.optionExpire = Transaction.parseDate(optionExpire)
			elif type(optionExpire) == datetime.datetime:
				self.optionExpire = optionExpire
			else:
				raise Exception("Transaction optionExpire must be datetime type, is " + str(type(optionExpire)))
		else:
			self.optionExpire = False
		
		if edited == "True" or (type(edited) == bool and edited):
			self.edited = True
		else:
			self.edited = False
		if deleted == "True" or (type(deleted) == bool and deleted):
			self.deleted = True
		else:
			self.deleted = False
	
	def __eq__(self, t2):
		if self and not t2:
			return False
		def compField(a, b):
			return a == b or (not a and not b) or (not a and b == "False") or (a == "False" and not b)
		return compField(self.ticker, t2.ticker) and compField(self.date, t2.date) and compField(self.type, t2.type) and compField(self.total, t2.total) and compField(self.shares, t2.shares) and compField(self.pricePerShare, t2.pricePerShare) and compField(self.fee, t2.fee) and compField(self.ticker2, t2.ticker2) and compField(self.subType, t2.subType)
	
	def __ne__(self, t2):
		return not self.__eq__(t2)
	
	def __str__(self):
		str = ""
		if self.uniqueId:
			str += "id=" + self.uniqueId + " "
		str += self.formatDate() + " " + self.formatTicker() + " " + self.formatType()
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
		if self.auto:
			str += " (auto)"
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
	
	def __hash__(self):
		# Basic hash function by datetime (integer) and transaction type
		return hash((self.date, self.type))
	
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
		self.subType = int(subType)

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
		self.edited = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

	def setDeleted(self, deleted = True):
		self.edited = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		self.deleted = deleted
	
	@staticmethod
	def parseDate(date):
		'Return a datetime object for a date in the form "%Y-%m-%d %H:%M:%S"'
		try:
			return datetime.datetime(int(date[0:4]), int(date[5:7]), int(date[8:10]),
				int(date[11:13]), int(date[14:16]), int(date[17:19]))
		except Exception, e:
			return datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")

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
		# MM-DD-YYYY (or with slashes)
		return date[6:10] + "-" + date[:2] + "-" + date[3:5] + " 00:00:00"
	
	@staticmethod
	def optionsHouseDateToSql(date):
		# YYYY-MM-DD (or with slashes)
		return date[0:4] + "-" + date[5:7] + "-" + date[8:10] + " 00:00:00"

	@staticmethod
	def forEdit():
		list = [Transaction.deposit, Transaction.withdrawal, Transaction.buy, Transaction.sell, Transaction.short, Transaction.cover, Transaction.split, Transaction.dividend, Transaction.dividendReinvest, Transaction.expense, Transaction.adjustment, Transaction.stockDividend, Transaction.spinoff, Transaction.tickerChange, Transaction.transferIn, Transaction.transferOut, Transaction.buyToOpen, Transaction.sellToClose, Transaction.sellToOpen, Transaction.buyToClose, Transaction.exercise, Transaction.assign, Transaction.expire]
		assert(len(list) == Transaction.numTransactionTypes)
		return list
	
	@staticmethod
	def forEditBank():
		list = [Transaction.deposit, Transaction.withdrawal, Transaction.buy, Transaction.sell, Transaction.dividend, Transaction.dividendReinvest, Transaction.expense, Transaction.adjustment]
		return list

	@staticmethod
	def fieldsForTransaction(type, subType = False):
		if type == Transaction.deposit or type == Transaction.withdrawal:
			return ["date", "fee", "total"]
		elif type == Transaction.expense:
			return ["date", "ticker", "fee", "-total"]
		elif type in [Transaction.buy, Transaction.sell, Transaction.short]:
			return ["date", "fee", "ticker", "shares", "pricePerShare"]
		elif type == Transaction.cover:
			return ["date", "fee", "ticker", "shares", "pricePerShare", "total"]
		elif type in [Transaction.buyToOpen, Transaction.sellToClose, Transaction.sellToOpen, Transaction.buyToClose]:
			return ["date", "fee", "ticker", "shares", "pricePerShare", "total", "strike", "expire"]
		elif type in [Transaction.dividendReinvest, Transaction.transferIn, Transaction.transferOut]:
			return ["date", "fee", "ticker", "shares", "pricePerShare"]
		elif type == Transaction.split or type == Transaction.dividend:
			return ["date", "fee", "ticker", "total"]
		elif type == Transaction.adjustment:
			return ["date", "ticker", "total"]
		elif type == Transaction.stockDividend:
			return ["date", "fee", "ticker", "shares", "-total"]
		elif type == Transaction.spinoff:
			return ["date", "fee", "ticker", "ticker2", "shares", "pricePerShare"]
		elif type == Transaction.tickerChange:
			return ["date", "fee", "ticker", "ticker2", "shares", "-total"]
		elif type == Transaction.exercise or type == Transaction.assign:
			return ["date", "fee", "ticker", "shares", "option", "-total"]
		elif type == Transaction.expire:
			return ["date", "fee", "ticker", "shares", "option"]
		else:
			return []

	def formatTicker(self):
		if self.ticker == "__CASH__":
			return "Cash Balance"
		elif self.ticker2:
			return self.ticker + " -> " + self.ticker2
		elif self.isOption():
			ret = self.ticker
			ret += " " + self.optionExpire.strftime("%b-%y")
			ret += " " + self.formatDollar(self.optionStrike)
			if self.subType == Transaction.optionPut:
				ret += " put"
			elif self.subType == Transaction.optionCall:
				ret += " call"
			else:
				ret += "???"
			return ret
		else:
			return self.ticker
	
	def formatTicker1(self):
		if self.ticker == "__CASH__":
			return "Cash Balance"
		else:
			return self.ticker

	def formatTicker2(self):
		if self.ticker2 == "__CASH__":
			return "Cash Balance"
		else:
			return self.ticker2

	def formatDate(self):
		return str(self.date.month) + "/" + str(self.date.day) + "/" + str(self.date.year)
	
	def dateDict(self):
		return dateDict(self.date)
	
	def getDate(self):
		return self.date
	
	# Return how much this transaction modifies the cash position
	# Returns 0 if it does not change cash
	def getCashMod(self):
		if self.type in [Transaction.deposit, Transaction.dividend]:
			return abs(self.total)
		elif self.type in [Transaction.sell, Transaction.sellToClose, Transaction.sellToOpen, Transaction.short, Transaction.buyToClose, Transaction.cover]:
			return self.getTotal()
		elif self.type in [Transaction.withdrawal, Transaction.buy, Transaction.buyToOpen]:
			return -abs(self.total)
		elif self.type == Transaction.expense:
			if self.total:
				return -abs(self.total)
			else:
				return -abs(self.fee)
		elif self.type == Transaction.adjustment and self.ticker == "__CASH__":
			return self.total

		return 0
	
	def getIrrFee(self, ticker):
		'Returns the fee IRR for this transaction'
		if self.ticker == "__CASH__":
			if self.type == Transaction.dividend:
				# Cash dividends increase value on their own, do not include here
				val = 0
			else:
				val = self.getCashMod()
			val += self.getFee()
			return val
		else:
			# IRR for stocks
			if self.type == Transaction.dividend:
				# Include dividends
				return -self.getTotal()
			elif self.type == Transaction.spinoff:
				# Spinoff is withdrawal if we are the original ticker
				# Deposit if we are the spinoff ticker
				if ticker == self.ticker:
					return -self.getTotal()
				else:
					return self.getTotal()
			elif self.type == Transaction.dividendReinvest:
				# Do not include dividend reinvest since new shares are included in value
				return self.getFee()
			elif self.type == Transaction.transferIn:
				return self.getTotal()
			elif self.type == Transaction.transferOut:
				return -self.getTotal()
			elif self.type == Transaction.short:
				if not self.pricePerShare or not self.shares:
					return 0
				return self.pricePerShare * self.shares + self.getFee()
			else:
				# Base IRR on cash mod
				return -self.getCashMod()
	
	def getIrrDiv(self, ticker):
		'Returns the dividend IRR for this transaction (getIrrFee ignoring fees)'
		if self.ticker == "__CASH__":
			return self.getIrrFee(ticker) - self.getFee()
		else:
			if self.type == Transaction.expense:
				return 0
			val = self.getIrrFee(ticker) - self.getFee()
			return val

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
		elif type == Transaction.short:
			return "Short"
		elif type == Transaction.cover:
			return "Cover"
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
		elif type == Transaction.buyToOpen:
			return "Options: Buy to Open"
		elif type == Transaction.sellToClose:
			return "Options: Sell to Close"
		elif type == Transaction.sellToOpen:
			return "Options: Sell to Open"
		elif type == Transaction.buyToClose:
			return "Options: Buy to Close"
		elif type == Transaction.exercise:
			return "Options: Exercised"
		elif type == Transaction.assign:
			return "Options: Assigned"
		elif type == Transaction.expire:
			return "Options: Expired"
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
		elif string == "Short":
			return Transaction.short
		elif string == "Cover":
			return Transaction.cover
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
		elif string == "Options: Buy to Open":
			return Transaction.buyToOpen
		elif string == "Options: Sell to Close":
			return Transaction.sellToClose
		elif string == "Options: Sell to Open":
			return Transaction.sellToOpen
		elif string == "Options: Buy to Close":
			return Transaction.buyToClose
		elif string == "Options: Exercised":
			return Transaction.exercise
		elif string == "Options: Assigned":
			return Transaction.assign
		elif string == "Options: Expired":
			return Transaction.expire
		else:
			return False
	
	@staticmethod
	def getTransactionOrdering(type):
		if type in [Transaction.deposit, Transaction.transferIn]:
			return 0
		elif type in [Transaction.buy, Transaction.short, Transaction.dividendReinvest, Transaction.buyToOpen, Transaction.sellToOpen]:
			return 1
		elif type in [Transaction.split, Transaction.dividend, Transaction.spinoff, Transaction.tickerChange]:
			return 2
		elif type in [Transaction.sell, Transaction.cover, Transaction.buyToClose, Transaction.sellToClose]:
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
		# Check for options
		if self.isOption():
			return self.getTypeString(self.type).replace("Options: ", "")
		elif self.type == Transaction.dividend:
			if self.subType == Transaction.returnOfCapital:
				return "Return of Capital"
			elif self.subType == Transaction.capitalGainShortTerm:
				return "Short Term Capital Gain"
			elif self.subType == Transaction.capitalGainLongTerm:
				return "Long Term Capital Gain"
			return self.getTypeString(self.type)
		else:
			return self.getTypeString(self.type)
	
	def formatShares(self):
		return self.formatFloat(abs(self.shares))
	
	@staticmethod
	def formatFloat(value, commas = False):
		'''
		Format a floating point value without any trailing 0s in the decimal portion
		'''
		if value == 0.0:
			return "0"
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

		return "$" + Transaction.formatFloat(value, commas = True)

	def formatPricePerShare(self):
		if not self.pricePerShare or self.pricePerShare == "False":
			return ""
		return self.formatDollar(self.pricePerShare)
	
	def getShares(self):
		if self.shares:
			return abs(self.shares)
		else:
			return 0
	
	def getFee(self):
		if self.type == Transaction.expense:
			if self.total:
				return abs(self.total)
			else:
				return abs(self.fee)
		elif self.fee:
			return abs(self.fee)
		else:
			return 0

	def formatFee(self):
		if not self.fee or self.fee == "False":
			return ""
		return "$" + str(self.fee)
	
	def getTotal(self):
		if not self.total:
			return 0
		
		# Compute for buys/sells
		if self.type in [Transaction.buy, Transaction.transferIn]:
			if self.pricePerShare and self.shares:
				return -abs(self.pricePerShare * self.shares) - self.getFee()
			return -abs(self.total)
		elif self.type in [Transaction.sell, Transaction.transferOut]:
			if self.pricePerShare and self.shares:
				return abs(self.pricePerShare * self.shares) - self.getFee()
			return abs(self.total)
		elif self.type in [Transaction.deposit, Transaction.dividend]:
			return abs(self.total)
		elif self.type in [Transaction.withdrawal]:
			return -abs(self.total)
		
		return self.total

	def getTotalIgnoreFee(self):
		return self.getTotal() + self.getFee()

	def formatTotal(self):
		if not self.total:
			return ""
		elif self.type in [Transaction.split]:
			return self.splitValueToString(self.total)
		elif self.type in [Transaction.sell, Transaction.deposit, Transaction.dividend]:
			# Always positive
			return self.formatDollar(abs(self.total))
		elif self.type in [Transaction.buy, Transaction.withdrawal, Transaction.expense]:
			# Always negative
			return self.formatDollar(-abs(self.total))
		else:
			return self.formatDollar(self.total)
	
	def formatStrike(self):
		if not self.optionStrike or self.optionStrike == "False":
			return ""
		return self.formatDollar(self.optionStrike)

	def formatExpire(self):
		if not self.optionExpire or self.optionExpire == "False":
			return ""
		return "%d/%d/%d" % (self.optionExpire.month, self.optionExpire.day, self.optionExpire.year)

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
	
	def isOption(self):
		return self.type in [Transaction.buyToOpen, Transaction.sellToClose, Transaction.sellToOpen, Transaction.buyToClose, Transaction.assign, Transaction.exercise, Transaction.expire]
	
	def isBankSpending(self):
		return self.type == Transaction.withdrawal and self.ticker != "__CASH__"
	
	def getSaveData(self):
		return {
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
			"optionStrike": self.optionStrike,
			"optionExpire": self.optionExpire,
			"edited": self.edited,
			"deleted": self.deleted,
			"auto": self.auto
		}
	
	def save(self, db):
		data = self.getSaveData()

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
