import appGlobal

from transaction import *

class Basis:
	"""Implements a basis tracker.  Ticker can be a simple stock ticker or a tuple for tracking options.  An options tuple is (ticker, Transaction.optionCall | Transaction.optionPut, strike, expire)"""

	# tickers[ticker][pricePerShare] = (datePurchased, quantity)
	# The (datePurchased, quantity) tuple should be removed once quantity goes to 0
	def __init__(self):
		self.tickers = {}

	def add(self, ticker, datePurchased, quantity, pricePerShare):
		if not ticker in self.tickers:
			self.tickers[ticker] = {}
		if not pricePerShare in self.tickers[ticker]:
			self.tickers[ticker][pricePerShare] = []
		self.tickers[ticker][pricePerShare].append((datePurchased, quantity))

	def remove(self, ticker, quantity):
		if not ticker in self.tickers:
			print "no basis for", ticker, quantity
			return
		# Keep looping until we have removed all quantity
		while quantity > 1.0e-6:
			# Find minimum date
			minDate = False
			for ts in self.tickers[ticker].itervalues():
				for t in ts:
					if minDate is False or t[0] < minDate:
						minDate = t[0]
			if minDate is False:
				print "no dates for", ticker
				return

			# Remove shares from minimum dates
			removed = 0
			i = 0
			for (pricePerShare, ts) in self.tickers[ticker].items():
				for t in ts:
					if t[0] != minDate:
						continue
					if t[1] <= quantity:
						# Remove completely
						removed += t[1]
						quantity -= t[1]
						self.tickers[ticker][pricePerShare].remove(t)
						if len(self.tickers[ticker][pricePerShare]) == 0:
							del self.tickers[ticker][pricePerShare]
						if len(self.tickers[ticker]) == 0:
							del self.tickers[ticker]
							if quantity > 1.0e-6:
								app = appGlobal.getApp()
								if app and app.statusUpdate:
									app.statusUpdate.addMessage("Left over quantity %s %f" % (ticker, quantity))
								return
					else:
						# Remove some shares
						removed += quantity
						self.tickers[ticker][pricePerShare][i] = (t[0], t[1] - quantity)
						quantity = 0
						i += 1

			# Makes ure something was removed
			if removed == 0:
				print "Could not finish basis for", ticker
				break

	def getShares(self, ticker):
		if not ticker in self.tickers:
			return 0
		count = 0
		for ts in self.tickers[ticker].itervalues():
			for t in ts:
				count += t[1]
		return count

	def getBasis(self, ticker):
		"""Get the basis per share for a stock or option"""
		if not ticker in self.tickers:
			return 0
		count = 0
		sum = 0
		for (pricePerShare, ts) in self.tickers[ticker].items():
			for t in ts:
				count += t[1]
				sum += t[1] * pricePerShare
		if count > 0:
			return float(sum) / count
		else:
			return 0

	def getTotalBasis(self, ticker = False):
		"""Get the total basis for a ticker.  This includes stocks and options.  Pass ticker as False to get the basis for all stocks and options."""
		sum = 0
		for t in self.tickers:
			# Check for ticker or for option
			if ticker and t != ticker and not (isinstance(t, tuple) and t[0] == ticker):
				continue
			for (pricePerShare, ts) in self.tickers[t].items():
				for t in ts:
					sum += t[1] * pricePerShare
		return sum

if __name__ == "__main__":
	print "test 1 - basic add remove"
	b = Basis()
	b.add("A", "2011-01-01", 10, 20)
	b.add("A", "2011-01-02", 10, 20)
	b.add("A", "2011-01-03", 5, 21)
	assert(b.getShares("A") == 25)
	assert(b.getBasis("A") == 20.2)
	assert(b.getTotalBasis("A") == 505)
	b.remove("A", 5)
	assert(b.getShares("A") == 20)
	assert(b.getBasis("A") == 20.25)
	assert(b.getTotalBasis("A") == 405)
	b.remove("A", 15)
	assert(b.getShares("A") == 5)
	assert(b.getBasis("A") == 21)
	assert(b.getTotalBasis("A") == 105)
	b.remove("A", 4)
	assert(b.getShares("A") == 1)
	assert(b.getBasis("A") == 21)
	assert(b.getTotalBasis("A") == 21)
	b.remove("A", 1)
	assert(b.getShares("A") == 0)
	assert(b.getBasis("A") == 0)
	assert(b.getTotalBasis("A") == 0)
	assert(len(b.tickers) == 0)

	print "test 2 - multiple tickers"
	b = Basis()
	b.add("A", "2011-01-01", 10, 20)
	b.add("B", "2011-01-02", 10, 20)
	assert(b.getShares("A") == 10)
	assert(b.getBasis("A") == 20)
	assert(b.getTotalBasis("A") == 200)
	assert(b.getShares("B") == 10)
	assert(b.getBasis("B") == 20)
	assert(b.getTotalBasis("B") == 200)
	b.remove("A", 5)
	assert(b.getShares("A") == 5)
	assert(b.getBasis("A") == 20)
	assert(b.getTotalBasis("A") == 100)
	b.remove("B", 10)
	assert(b.getShares("B") == 0)
	assert(b.getBasis("B") == 0)
	assert(b.getTotalBasis("B") == 0)
	b.remove("A", 5)
	assert(b.getShares("A") == 0)
	assert(b.getBasis("A") == 0)
	assert(b.getTotalBasis("A") == 0)

	print "test 3 - options"
	b = Basis()
	optionTuple1 = ("A", Transaction.optionPut, 25, "2011-01-21")
	optionTuple2 = ("A", Transaction.optionCall, 22, "2011-01-21")
	optionTuple3 = ("B", Transaction.optionCall, 29, "2011-02-21")
	b.add(optionTuple1, "2011-01-01", 10, 20)
	assert(b.getShares(optionTuple1) == 10)
	assert(b.getBasis(optionTuple1) == 20)
	assert(b.getTotalBasis(optionTuple1) == 200)
	b.add(optionTuple1, "2011-01-01", 6, 30)
	assert(b.getShares(optionTuple1) == 16)
	assert(b.getBasis(optionTuple1) == 23.75)
	assert(b.getTotalBasis(optionTuple1) == 380)
	b.add(optionTuple2, "2011-01-03", 10, 40)
	assert(b.getShares(optionTuple2) == 10)
	assert(b.getBasis(optionTuple2) == 40)
	assert(b.getTotalBasis(optionTuple2) == 400)
	assert(b.getTotalBasis("A") == 780)
	b.add(optionTuple3, "2011-01-05", 50, 2)
	assert(b.getShares(optionTuple3) == 50)
	assert(b.getBasis(optionTuple3) == 2)
	assert(b.getTotalBasis(optionTuple3) == 100)
	assert(b.getTotalBasis("A") == 780)
	assert(b.getTotalBasis("B") == 100)
	assert(b.getTotalBasis("C") == 0)

	print "test 4 - stocks and options"
	b = Basis()
	b.add(optionTuple1, "2011-01-01", 10, 20)
	assert(b.getShares(optionTuple1) == 10)
	assert(b.getBasis(optionTuple1) == 20)
	assert(b.getTotalBasis(optionTuple1) == 200)
	b.add("A", "2011-01-01", 10, 65)
	assert(b.getShares("A") == 10)
	assert(b.getBasis("A") == 65)
	assert(b.getTotalBasis("A") == 850)
	b.remove(optionTuple1, 10)
	assert(b.getBasis(optionTuple1) == 0)
	assert(b.getTotalBasis("A") == 650)
	b.remove("A", 10)
	assert(b.getTotalBasis("A") == 0)
	assert(b.getBasis("A") == 0)
	assert(b.getTotalBasis("A") == 0)
	assert(len(b.tickers) == 0)
