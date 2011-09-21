from basis import *

class Twrr:
	"""Implements time weighted returns.  Relies on a basis tracker for shorts/covers."""

	def __init__(self):
		self.day = 1
		self.ticker = False
		self.normFactor = False
		# Shares is a count of shares owned per ticker
		self.shares = {}
		self.prices = {}
		self.basis = Basis()
		self.adjustBasises = {}
		self.dividendFactor = 1.0
		self.adjustment = 0
		self.feeFactor = 1.0
		# Last positive value
		self.lastValue = False 
		self.lastReturn = 1.0

	def beginTransactions(self):
		# cashIn and sharesIn are keyed by ticker
		self.cashIn = {}
		self.sharesIn = {}
		self.cashOut = {}
		self.sharesOut = {}
		self.dividends = 0.0
		self.fees = 0.0

	def endTransactions(self):
		self.day += 1

		# Transaction order:
		# cashIn (if first deposit)
		# adjustBasises
		# dividends
		# cashIn (later deposits)
		# fees
		# cashOut (later deposits)

		# cashIn (if first transaction)
		if not self.normFactor:
			# If no fees or withdrawals then return nothing to do
			if not self.dividends and not self.fees and not self.cashIn and not self.cashOut and not self.adjustBasises:
				return

			sumCashIn = 0.0
			for t in self.sharesIn:
				self.shares[t] = self.sharesIn[t]
				sumCashIn += abs(self.cashIn[t])

				if self.cashIn[t] >= 0:
					# Long
					self.basis.add(t, self.day, self.sharesIn[t], self.cashIn[t] / self.sharesIn[t])
				else:
					# Short
					self.basis.add(t, self.day, -self.sharesIn[t], self.cashIn[t] / self.sharesIn[t])

			if sumCashIn != 0:
				if self.lastReturn == 0:
					# Reset TWRR if returns went to 0
					self.normFactor = abs(sumCashIn)
				else:
					# Returns were not at 0
					# Update normFactor so return is consistent
					self.normFactor = abs(sumCashIn / self.lastReturn)
				#print "sharesIn", self.sharesIn, "cashIn", self.cashIn, "normFactor", self.normFactor
				self.cashIn = {}
				self.sharesIn = {}

				# Starting new, no last value
				self.lastValue = False

		if self.adjustBasises:
			if  not self.normFactor:
				raise Exception("adjust basis but no value for %s" % self.ticker)

			for t in self.adjustBasises:
				basisValue = self.shares[t] * self.prices[t]
				if basisValue == 0:
					raise Exception("adjust basis but not value for %s" % t)

				self.normFactor *= (basisValue - self.adjustBasises[t]) / basisValue
			self.adjustBasises = {}

		# dividends
		cashAddedToday = self.dividends
		if self.dividends:
			# If dividends and fees reduce the dividend cash received by the fees
			if self.fees:
				cashAddedToday -= min(self.dividends, self.fees)

			if self.lastValue > 0:
				self.dividendFactor *= (self.lastValue + self.dividends) / self.lastValue
			elif self.getTotalValue() > 0:
				self.dividendFactor *= float(self.getTotalValue() + self.dividends) / self.getTotalValue()
			else:
				if self.lastValue:
					lastValue = self.lastValue
				else:
					lastValue = 0.0
				raise Exception("Dividend %f but no value for %s vals are %f, %f" % (self.dividends, self.ticker, lastValue, self.getTotalValue()))
		self.dividends = 0.0

		# sharesIn (later deposits)
		tValue = self.getTotalValue()
		if self.cashIn:
			sumCashIn = 0
			for t in self.cashIn:
				# Determine the value of the added shares vs. what is currently here
				if tValue == 0 or not self.normFactor:
					raise Exception("adding more but no value for %s, %f %f" % (self.ticker, tValue, self.normFactor))
	
				if not self.shares:
					raise Exception("cashIn but no shares for %s" % self.ticker)
				sumCashIn += abs(self.cashIn[t])
				cashAddedToday += abs(self.cashIn[t])
				if t in self.shares:
					self.shares[t] += self.sharesIn[t]
				else:
					self.shares[t] = self.sharesIn[t]
					self.prices[t] = self.cashIn[t] / self.sharesIn[t]
				if self.cashIn[t] >= 0:
					# Long
					self.basis.add(t, self.day, self.sharesIn[t], self.cashIn[t] / self.sharesIn[t])
				else:
					# Short
					self.basis.add(t, self.day, -self.sharesIn[t], self.cashIn[t] / self.sharesIn[t])
			#print tValue, sumCashIn, cashAddedToday, self.normFactor, "->",
			self.normFactor *= (tValue + sumCashIn) / tValue
			#print self.normFactor
			#print "sharesIn2", self.sharesIn, "cashIn", self.cashIn, "normFactor", self.normFactor
			self.sharesIn = {}
			self.cashIn = {}

		# fees
		if self.fees:
			if self.ticker == "__CASH__":
				if self.lastValue > 0:
					effCash = self.lastValue + cashAddedToday
					self.feeFactor *= (effCash - self.fees) / effCash
				elif self.getTotalValue() > 0:
					self.feeFactor *= (self.getTotalValue() - self.fees) / self.getTotalValue()
				else:
					raise Exception("Fee %f but no value for %s" % (self.fees, self.ticker))
			else:
				if self.lastValue > 0:
					effCash = self.lastValue + abs(cashAddedToday)
					self.feeFactor *= effCash / (effCash + self.fees)
				elif self.getTotalValue() > 0:
					# Do not include dividends on first day
					effCash = self.getTotalValue()
					self.feeFactor *= effCash / (effCash + self.fees)
				else:
					raise Exception("Fee %f but no value for %s" % (self.fees, self.ticker))
			self.fees = 0.0

		# sharesOut (later deposits)
		for t in self.sharesOut:
			#print "sharesOut", t, self.sharesOut[t], "cashOut", self.cashOut[t]
			if not self.shares:
				raise Exception("cashOut but no shares for %s" % t)
			if not t in self.shares:
				raise Exception("no shares for %s" % t)

			#print "out cashOut", self.cashOut[t], "shares", self.shares, "normFactor", self.normFactor
			if self.cashOut[t] < 0:
				# Short
				basis = self.basis.getBasis(t)
				profit = (basis - self.prices[t]) * -self.shares[t]
				otherValue = 0
				for t2 in self.shares:
					if t2 != t:
						otherValue += abs(self.shares[t2] * self.prices[t2])
				newReturn = (otherValue + profit + basis * -self.shares[t]) / self.normFactor
				self.shares[t] -= self.sharesOut[t]
			else:
				# New return is (new value + cashOut) / (oldValue)
				self.shares[t] -= self.sharesOut[t]
				newReturn = (self.getTotalValue() + abs(self.cashOut[t])) / self.normFactor
			
			self.basis.remove(t, abs(self.sharesOut[t]))

			if self.getTotalValue() == 0:
				self.lastReturn = newReturn
				self.normFactor = False
			else:
				self.normFactor = abs(self.getTotalValue() / newReturn)
			#print "newReturn", newReturn, "normFactor", self.normFactor
		if self.sharesOut:
			self.sharesOut = {}
			self.cashOut = {}

	def addShares(self, ticker, shares, price):
		if shares < 0:
			raise Exception("Shares must be >= 0 for %s" % ticker)
		if price < 0:
			raise Exception("Price must be >= 0 for %s" % ticker)
		if shares == 0:
			return
		if not self.ticker:
			self.ticker = ticker
		if price != 0 or not ticker in self.prices:
			self.prices[ticker] = price
		if not ticker in self.cashIn:
			self.cashIn[ticker] = float(shares) * price
			self.sharesIn[ticker] = float(shares)
		else:
			self.cashIn[ticker] += float(shares) * price
			self.sharesIn[ticker] += float(shares)

	def removeShares(self, ticker, shares, price):
		if shares < 0:
			raise Exception("Shares must be >= 0 for %s" % ticker)
		if price < 0:
			raise Exception("Price must be >= 0 for %s" % ticker)
		if shares == 0:
			return
		if price != 0:
			self.prices[ticker] = price
		if not ticker in self.cashOut:
			self.cashOut[ticker] = float(shares) * price
			self.sharesOut[ticker] = float(shares)
		else:
			self.cashOut[ticker] += float(shares) * price
			self.sharesOut[ticker] += float(shares)

	def removeSharesNoPrice(self, ticker, shares):
		if not ticker in self.prices:
			raise Exception("No price for %s" % ticker)
		self.removeShares(ticker, shares, self.prices[ticker])

	def shortShares(self, ticker, shares, price):
		if shares < 0:
			raise Exception("Shares must be >= 0 for %s" % ticker)
		if price < 0:
			raise Exception("Price must be >= 0 for %s" % ticker)
		if not self.ticker:
			self.ticker = ticker
		if price != 0:
			self.prices[ticker] = price
		# Pass a date of 1
		if not ticker in self.cashIn:
			self.cashIn[ticker] = -float(shares) * price
			self.sharesIn[ticker] = -float(shares)
		else:
			self.cashIn[ticker] -= float(shares) * price
			self.sharesIn[ticker] -= float(shares)

	def coverShares(self, ticker, shares, price):
		if shares < 0:
			raise Exception("Shares must be >= 0 for %s" % ticker)
		if price < 0:
			raise Exception("Price must be >= 0 for %s" % ticker)
		if price != 0:
			self.prices[ticker] = price
		if not ticker in self.cashOut:
			self.cashOut[ticker] = -float(shares) * price
			self.sharesOut[ticker] = -float(shares)
		else:
			self.cashOut[ticker] -= float(shares) * price
			self.sharesOut[ticker] -= float(shares)

	def addDividend(self, amount):
		if amount < 0:
			raise Exception("Amount must be >= 0 for %s" % self.ticker)
		self.dividends += amount

	def addAdjustment(self, amount):
		self.adjustment += amount

	def adjustBasis(self, ticker, amount):
		if amount < 0:
			raise Exception("Amount must be >= 0 for %s" % ticker)
		if not ticker in self.adjustBasises:
			self.adjustBasises[ticker] = amount
		else:
			self.adjustBasises[ticker] += amount

	def addFee(self, amount):
		if amount < 0:
			raise Exception("Amount must be >= 0 for %s" % self.ticker)
		self.fees += amount

	def addDividendReinvest(self, ticker, shares, price):
		if shares < 0:
			raise Exception("Shares must be >= 0 for %s" % ticker)
		if price < 0:
			raise Exception("Price must be >= 0 for %s" % ticker)
		self.addDividend(shares * price)
		self.addShares(ticker, shares, price)

	def setValue(self, ticker, price):
		if price < 0:
			raise Exception("Price must be >= 0 for %s" % ticker)
		self.prices[ticker] = price

	def getTotalValue(self):
		v = 0
		for t in self.shares:
			if self.shares[t] >= 0:
				v += self.shares[t] * self.prices[t]
			else:
				# short
				basis = self.basis.getBasis(t)
				v += self.shares[t] * (self.prices[t] - basis)  + self.basis.getTotalBasis(t)
		return v + self.adjustment

	def getReturnSplit(self):
		if not self.normFactor or self.normFactor == 0:
			return self.lastReturn
		else:
			value = self.getTotalValue()
			self.lastReturn = value / self.normFactor
			if value > 0:
				self.lastValue = value
			return self.lastReturn

	def getReturnDiv(self):
		return self.getReturnSplit() * self.dividendFactor

	def getReturnFee(self):
		return self.getReturnSplit() * self.dividendFactor * self.feeFactor

def checkSplit(r, check):
	if abs(r.getReturnSplit() - check) >= 1.0e-6:
		print "FAIL split:", r, r.getTotalValue(), r.getReturnSplit(), "should be", check

def checkDiv(r, check):
	if abs(r.getReturnDiv() - check) >= 1.0e-6:
		print "FAIL div:", r, r.getTotalValue(), r.getReturnDiv(), "should be", check

def checkFee(r, check):
	if abs(r.getReturnFee() - check) >= 1.0e-6:
		print "FAIL fee:", r, r.getTotalValue(), r.getReturnFee(), "should be", check

def checkTotalValue(r, check):
	if abs(r.getTotalValue() - check) >= 1.0e-6:
		print "FAIL total value:", r, r.getTotalValue(), "should be", check

if __name__ == "__main__":
	print "test1 - basic dividends"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.endTransactions()
	r.setValue("A", 90)
	checkSplit(r, 0.9)
	checkDiv(r, 0.9)
	r.setValue("A", 110)
	checkDiv(r, 1.1)
	r.setValue("A", 120)
	checkDiv(r, 1.2)

	r.beginTransactions()
	r.addDividend(100)
	r.endTransactions()
	checkSplit(r, 1.2)
	checkDiv(r, 1.3)

	print "test2 - remove shares"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.endTransactions()
	checkDiv(r, 1)

	r.beginTransactions()
	r.removeShares("A", 5, 100)
	r.endTransactions()
	checkDiv(r, 1)

	r.beginTransactions()
	r.addShares("A", 5, 100)
	r.endTransactions()
	r.setValue("A", 50)
	checkDiv(r, 0.5)
	r.setValue("A", 100)
	checkDiv(r, 1)

	print "test3 - dividends and appreciation"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.addDividend(100)
	r.endTransactions()
	checkSplit(r, 1)
	checkDiv(r, 1.1)

	r.beginTransactions()
	r.addShares("A", 5, 100)
	r.endTransactions()
	checkDiv(r, 1.1)

	r.beginTransactions()
	r.addDividend(150)
	r.endTransactions()
	r.setValue("A", 200)
	checkSplit(r, 2)
	checkDiv(r, 2.42)
	r.setValue("A", 220)
	checkSplit(r, 2.2)
	checkDiv(r, 2.662)

	print "test4 - dividend reinvestment"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.endTransactions()

	r.beginTransactions()
	r.addDividendReinvest("A", 1, 100)
	r.endTransactions()
	checkSplit(r, 1)
	checkDiv(r, 1.1)

	r.beginTransactions()
	r.addDividendReinvest("A", 1.1, 100)
	r.endTransactions()
	checkSplit(r, 1)
	checkDiv(r, 1.21)

	print "test5 - stocks and options"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.endTransactions()
	checkTotalValue(r, 1000)
	checkSplit(r, 1)

	r.beginTransactions()
	r.addShares("Aopt", 3, 10)
	r.endTransactions()
	checkTotalValue(r, 1030)
	checkSplit(r, 1)

	r.setValue("A", 110)
	checkTotalValue(r, 1130)
	checkSplit(r, 1.0970874)
	r.setValue("Aopt", 5)
	checkTotalValue(r, 1115)
	checkSplit(r, 1.0825243)

	r.beginTransactions()
	r.removeShares("A", 3, 110)
	r.endTransactions()
	checkTotalValue(r, 785)
	checkSplit(r, 1.0825243)
	r.setValue("A", 100)
	checkTotalValue(r, 715)
	checkSplit(r, 0.9859934)

	print "test6 - adds and removes at multiple prices"
	r = Twrr()
	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.addShares("A", 10, 110)
	r.endTransactions()
	checkTotalValue(r, 2200)
	checkSplit(r, 1.047619)

	r.beginTransactions()
	r.removeShares("A", 5, 110)
	r.removeShares("A", 5, 105)
	r.endTransactions()
	checkTotalValue(r, 1050)
	checkSplit(r, 1.0119047)
	# nF should be 1073.863?

	print "test7 - single day buy/sell"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.removeShares("A", 5, 110)
	r.endTransactions()
	checkTotalValue(r, 550)
	checkSplit(r, 1.1)

	r.beginTransactions()
	r.removeShares("A", 5, 110)
	r.endTransactions()
	checkTotalValue(r, 0)
	checkSplit(r, 1.1)
	checkDiv(r, 1.1)
	checkFee(r, 1.1)

	r.beginTransactions()
	r.endTransactions()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.endTransactions()
	checkTotalValue(r, 1000)
	checkSplit(r, 1.1)

	r.beginTransactions()
	r.removeShares("A", 10, 110)
	r.endTransactions()
	checkTotalValue(r, 0)
	checkSplit(r, 1.21)

	print "test8 - fees"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.addFee(100)
	r.endTransactions()
	checkTotalValue(r, 1000)
	checkSplit(r, 1)
	checkDiv(r, 1)
	checkFee(r, 0.9090909)

	r.beginTransactions()
	r.addDividend(100)
	r.addFee(100)
	r.endTransactions()
	checkTotalValue(r, 1000)
	checkSplit(r, 1)
	checkDiv(r, 1.1)
	checkFee(r, 0.9090909)

	print "test9 - adjust basis"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.endTransactions()
	checkSplit(r, 1)

	r.beginTransactions()
	r.adjustBasis("A", 500)
	r.endTransactions()
	r.setValue("A", 50)
	checkSplit(r, 1)
	checkDiv(r, 1)
	checkFee(r, 1)
	checkTotalValue(r, 500)
	r.setValue("A", 60)
	checkTotalValue(r, 600)
	checkSplit(r, 1.2)
	checkDiv(r, 1.2)
	checkFee(r, 1.2)
	r.setValue("A", 50)
	checkTotalValue(r, 500)

	r.beginTransactions()
	r.adjustBasis("A", 400)
	r.endTransactions()
	r.setValue("A", 10)
	checkTotalValue(r, 100)
	checkSplit(r, 1)
	checkDiv(r, 1)
	checkFee(r, 1)

	print "test10 - adjustment"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.addAdjustment(100)
	r.endTransactions()
	checkTotalValue(r, 1100)
	checkSplit(r, 1.1)
	checkDiv(r, 1.1)
	checkFee(r, 1.1)

	r.beginTransactions()
	r.addAdjustment(300)
	r.endTransactions()
	checkTotalValue(r, 1400)
	checkSplit(r, 1.4)
	checkDiv(r, 1.4)
	checkFee(r, 1.4)

	print "test11 - dividend after closed position"
	r = Twrr()

	r.beginTransactions()
	r.addShares("A", 10, 100)
	r.endTransactions()
	checkTotalValue(r, 1000)
	checkSplit(r, 1)
	checkDiv(r, 1)
	checkFee(r, 1)

	r.beginTransactions()
	r.removeShares("A", 10, 100)
	r.endTransactions()
	checkTotalValue(r, 0)
	checkSplit(r, 1)
	checkDiv(r, 1)
	checkFee(r, 1)

	r.beginTransactions()
	r.addDividend(100)
	r.endTransactions()
	checkTotalValue(r, 0)
	checkSplit(r, 1)
	checkDiv(r, 1.1)
	checkFee(r, 1.1)

	print "test12 - basic short"
	r = Twrr()

	r.beginTransactions()
	r.shortShares("A", 10, 100)
	r.endTransactions()
	checkTotalValue(r, 1000)
	r.setValue("A", 90)
	checkSplit(r, 1.1)
	checkDiv(r, 1.1)
	r.setValue("A", 110)
	checkSplit(r, 0.9)

	r.beginTransactions()
	r.coverShares("A", 5, 100)
	r.endTransactions()
	r.setValue("A", 90)
	checkSplit(r, 1.1)
	checkDiv(r, 1.1)
	r.setValue("A", 110)
	checkSplit(r, 0.9)
	r.setValue("A", 200)
	checkSplit(r, 0)
	r.setValue("A", 300)
	checkSplit(r, -1)
	r.setValue("A", 50)
	checkSplit(r, 1.5)
	r.setValue("A", 0)
	checkSplit(r, 2)

	print "test13 - multiple short"
	r = Twrr()

	r.beginTransactions()
	r.shortShares("A", 10, 100)
	r.endTransactions()
	checkTotalValue(r, 1000)

	r.beginTransactions()
	r.shortShares("A", 10, 90)
	r.shortShares("A", 5, 90)
	r.endTransactions()
	checkTotalValue(r, 2450)
	checkSplit(r, 1.1)
	checkDiv(r, 1.1)
	checkFee(r, 1.1)
