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

import urllib
import urllib2
import json

from portfolio import *
from statusUpdate import *
from editGrid import *
from plugin import *

import appGlobal
import chart
import tutorial

try:
	import keyring
	haveKeyring = True
except:
	haveKeyring = False

class SynchronizerPassword(QDialog):
	def __init__(self, name, parent = None, badPassword = False, badUsername = False):
		QDialog.__init__(self, parent)
		self.app = appGlobal.getApp()
		self.setWindowTitle("Log in to " + name)
		self.name = name
		
		layout = QVBoxLayout(self)
		
		if badPassword:
			layout.addWidget(QLabel("<b>Incorrect log in for " + name + "</b>"))
		else:
			layout.addWidget(QLabel("<b>Log in to " + name + "</b>"))
		layout.addSpacing(5)

		grid = QGridLayout()
		layout.addLayout(grid)
		
		self.usernameLabel = QLabel("Username: ")
		grid.addWidget(self.usernameLabel, 0, 0)
		self.username = QLineEdit()
		self.username.setMinimumWidth(200)
		grid.addWidget(self.username, 0, 1)

		self.passwordLabel = QLabel("Password: ")
		grid.addWidget(self.passwordLabel, 1, 0)
		self.password = QLineEdit()
		self.password.setEchoMode(QLineEdit.Password)
		grid.addWidget(self.password, 1, 1)
		
		# Check for keyring, add save password checkbox
		if haveKeyring:
			self.savePassword = QCheckBox("Save Password")
			hbox2 = QHBoxLayout()
			layout.addLayout(hbox2)
			hbox2.addWidget(self.savePassword)
			layout.addSpacing(5)

			password = keyring.get_password("Icarra-site-" + name, "password")
			if password:
				self.savePassword.setChecked(True)

		self.username.setFocus()

		# Check for keying, try to load password
		# If found do not show dialog
		if badPassword:
			self.username.setText(badUsername)
			self.password.setFocus()
		elif haveKeyring:
			username = keyring.get_password("Icarra-site-" + name, "username")
			if username:
				self.username.setText(username)

			password = keyring.get_password("Icarra-site-" + name, "password")
			if password:
				self.password.setText(password)
				
		buttons = QHBoxLayout()
		layout.addLayout(buttons)

		buttons.addStretch(1)
		cancel = QPushButton("Cancel")
		buttons.addWidget(cancel)
		self.connect(cancel, SIGNAL("clicked()"), SLOT("reject()"))
		
		ok = QPushButton("OK")
		ok.setDefault(True)
		buttons.addWidget(ok)
		self.connect(ok, SIGNAL("clicked()"), self.onOk)
		
		self.status = self.exec_()
	
	def onOk(self):
		if haveKeyring:
			if self.savePassword.isChecked():
				keyring.set_password("Icarra-site-" + self.name, "username", str(self.username.text()))
				keyring.set_password("Icarra-site-" + self.name, "password", str(self.password.text()))
			else:
				keyring.set_password("Icarra-site-" + self.name, "username", "")
				keyring.set_password("Icarra-site-" + self.name, "password", "")

		self.accept()
		
class Synchronizer:
	def __init__(self, portfolio):
		self.portfolio = portfolio
		self.username = ""
		self.password = ""
		self.name = "???"
		self.aborted = False
		self.syncByIds = False # If we have transaction ids
	
	def getLogin(self, badPassword = False, badUsername = False):
		# Try to get saved password
		if haveKeyring and not badPassword:
			username = keyring.get_password("Icarra-site-" + self.name, "username")
			password = keyring.get_password("Icarra-site-" + self.name, "password")
			if username and password:
				self.username = username
				self.password = password
				return
		
		p = SynchronizerPassword(self.name, badPassword = badPassword, badUsername = badUsername)
		if p.status and p.username.text() and p.password.text():
			self.username = str(p.username.text())
			self.password = str(p.password.text())
		elif not p.status:
			self.aborted = True
	
	def sync(self):
		status = StatusUpdate(appGlobal.getApp().main, closeOnFinish = True)
		status.setStatus("Logging in", 1)

		# Get login info
		self.getLogin()
		if self.aborted:
			status.close()
			return
		
		self.login()
		
		status.setStatus("Checking portfolio", 5)
		
		try:
			# Verify that portfolio is available
			serverPorts = self.getPortfolios()
			if not self.portfolio.name in serverPorts:
				self.addPortfolio()
	
			status.setStatus("Downloading transactions", 10)
			
			serverTransactions = self.getTransactions()
			localTransactions = self.portfolio.getTransactions(getDeleted = True)
			localTransactionsDict = {}
			for t in localTransactions:
				if t.auto:
					continue
				localTransactionsDict[t.uniqueId] = t
			
			# Now consolidate based on ids
			if self.syncByIds:
				# Put serverTransactions in a dictionary by id
				serverDict = {}
				for t2 in serverTransactions:
					# Do not save automatic transactions
					if t2.auto:
						continue
					if t2.uniqueId in serverDict:
						status.addError("Transaction id is not unique for %s" % t2)
						continue
					serverDict[t2.uniqueId] = t2
	
				# Loop over local transactions, check if not there, deleted, or matching
				i = 0
				for t in localTransactions:
					i += 1
					status.setStatus("Synching transactions", 10 + 50 * i / len(localTransactions))
					
					# Skip automatically generated transactions
					if t.auto:
						continue
					
					# Look for transaction in dictionary
					if t.uniqueId in serverDict:
						found = True
						t2 = serverDict[t.uniqueId]
					else:
						found = False
						t2 = False
					
					# Delete if not deleted
					# Add if not found
					# Check for differences
					try:
						if t.deleted:
							# Make sure it's deleted on server
							# Do not add or update deleted transactions
							if t2 and not t2.deleted:
								self.deleteTransaction(t)
						elif not found:
							self.addTransaction(t)
						elif t != t2:
							self.updateTransaction(t)
					except Exception, e:
						status.addException()

				# Loop over server transactions, check if not there, deleted, or matching in local transactions
				modified = False
				i = 0
				for t2 in serverTransactions:
					i += 1
					status.setStatus("Synching transactions", 60 + 40 * i / len(serverTransactions))

					# Skip automatically generated transactions
					if t2.auto:
						continue

					# look for transaction in dictionary
					if t2.uniqueId in localTransactionsDict:
						found = True
						t = localTransactionsDict[t2.uniqueId]
					else:
						found = False
						t = False

					# Delete if not deleted
					# Add if not found
					# Check for differences
					try:
						if t2.deleted:
							# Make sure it's deleted locally
							# Do not add or update deleted transactions
							if t and not t.deleted:
								self.deleteLocalTransaction(t2)
								modified = True
						elif not found:
							self.addLocalTransaction(t2)
							modified = True
						elif t != t2:
							self.updateLocalTransaction(t2)
							modified = True
					except Exception, e:
						status.addException()

					if modified:
						self.portfolio.portPrefs.setDirty(True)

			else:
				raise Exception("sync not supported unless by ids")
		except Exception, e:
			status.addException()
		status.setFinished()

	def addLocalTransaction(self, t):
		t.save(self.portfolio.db)
		self.portfolio.portPrefs.setDirty(True)

	def updateLocalTransaction(self, t):
		t.save(self.portfolio.db)
		self.portfolio.portPrefs.setDirty(True)

	def deleteLocalTransaction(self, t):
		t.setDeleted()
		t.save(self.portfolio.db)
		self.portfolio.portPrefs.setDirty(True)
	
	# Subclass should override
	def login(self):
		pass

	# Subclass should override
	def getPortfolios(self):
		pass
	
	# Subclass should override
	def addPortfolio(self):
		pass
	
	# Subclass should override
	def getTransactions(self):
		pass
	
	# Subclass should override
	def addTransaction(self, transaction):
		print "add transaction", transaction
		pass

	# Subclass should override
	def deleteTransaction(self, transaction):
		print "delete transaction", transaction
		pass

	# Subclass should override
	def updateTransaction(self, transaction):
		print "update transaction", transaction
		pass

class IcarraSynchronizer(Synchronizer):
	def __init__(self, portfolio):
		Synchronizer.__init__(self, portfolio)
		self.name = "Icarra"
		self.syncByIds = True
		self.cookie = False
		self.userId = False
		self.url = "http://www.icarra2.com/cgi-bin/webClientApi.py"
	
	def login(self):
		loggedIn = False
		while not loggedIn and not self.aborted:
			query = urllib.urlencode({"action": "login", "email": self.username, "password": self.password})
			request = urllib2.Request(self.url, query)
			try:
				f = urllib2.urlopen(request)
				result = json.loads(f.read())
				if not result[0]:
					# Bad password
					self.getLogin(badPassword = True, badUsername = self.username)
				else:
					# Logged in!
					loggedIn = True
					self.userId = result[1]["userId"]
					self.cookie = result[1]["cookie"]
			except Exception, e:
				print "could not login:", e
				self.aborted = True

	def getPortfolios(self):
		query = urllib.urlencode({"action": "getPortfolioList", "userId": self.userId, "cookie": self.cookie})
		request = urllib2.Request(self.url, query)
		try:
			f = urllib2.urlopen(request)
			result = json.loads(f.read())
			if not result[0]:
				raise Exception("bad login")
			ret = []
			for p in result[1]["user"]:
				ret.append(p)
			return ret
		except Exception, e:
			print "could not get portfolios:", e
	
	def getTransactions(self):
		query = urllib.urlencode({"action": "getTransactions", "getDeleted": True, "userId": self.userId, "cookie": self.cookie, "name": self.portfolio.name})
		request = urllib2.Request(self.url, query)
		try:
			f = urllib2.urlopen(request)
			result = json.loads(f.read())
			if not result[0]:
				raise Exception("bad login")
			ret = []
			for t in result[1]:
				ret.append(Transaction(
					uniqueId = t["uniqueId"],
					ticker = t["ticker"],
					date = t["date"],
					transactionType = t["type"],
					amount = t["total"],
					shares = t["shares"],
					pricePerShare = t["pricePerShare"],
					fee = t["fee"],
					edited = t["edited"],
					deleted = t["deleted"],
					ticker2 = t["ticker2"],
					subType = t["subType"],
					auto = t["auto"]))
			return ret
		except Exception, e:
			print "could not get transactions:", e

	def addPortfolio(self):
		data = {"action": "addPortfolio", "userId": self.userId, "cookie": self.cookie, "name": self.portfolio.name}
		if self.portfolio.isBenchmark():
			data["type"] = "benchmark"
		elif self.portfolio.isCombined():
			data["type"] = "combined"
		elif self.portfolio.isBrokerage():
			data["type"] = "brokerage"
		query = urllib.urlencode(data)
		request = urllib2.Request(self.url, query)
		try:
			f = urllib2.urlopen(request)
			result = json.loads(f.read())
			if not result[0]:
				raise Exception("bad login")
		except Exception, e:
			print "could not add portfolio:", e

	def addTransaction(self, transaction):
		data = {"action": "newTransaction", "userId": self.userId, "cookie": self.cookie, "name": self.portfolio.name}
		data["uniqueId"] = transaction.uniqueId
		data["ticker"] = transaction.ticker
		data["date"] = transaction.date
		data["type"] = transaction.type
		
		# Add optional parameters if they are true or they are not bools
		data["ticker2"] = transaction.ticker2
		data["shares"] = transaction.shares
		data["pricePerShare"] = transaction.pricePerShare
		data["fee"] = transaction.fee
		data["total"] = transaction.total
		data["subType"] = transaction.subType
		query = urllib.urlencode(data)
		request = urllib2.Request(self.url, query)
		try:
			f = urllib2.urlopen(request)
			result = json.loads(f.read())
			if not result[0]:
				raise Exception("bad login " + result[1])
		except Exception, e:
			print "could not add transaction:", e

	def deleteTransaction(self, transaction):
		data = {"action": "deleteTransaction", "userId": self.userId, "cookie": self.cookie, "name": self.portfolio.name, "uniqueId": transaction.uniqueId}
		query = urllib.urlencode(data)
		request = urllib2.Request(self.url, query)
		f = urllib2.urlopen(request)
		result = json.loads(f.read())
		if not result[0]:
			raise Exception("could not delete transaction %s: %s" % (transaction, result[1]))

	def updateTransaction(self, transaction):
		print "update transaction not implemented", transaction
		pass

class Plugin(PluginBase):
	def name(self):
		return "Sync"

	def icarraVersion(self):
		return (0, 2, 0)

	def version(self):
		return (1, 0, 0)

	def initialize(self):
		pass

	def createWidget(self, parent):
		return SyncWidget(parent)
	
	def finalize(self):
		pass

class SyncWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.app = appGlobal.getApp()

		portfolio = self.app.portfolio
		
		vbox = QVBoxLayout(self)
		vbox.setAlignment(Qt.AlignTop)

		frame = QFrame()
		frame.setFrameStyle(QFrame.Panel)
		frame.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
		frame.setStyleSheet("QFrame { background: white; padding: 10px }")
		vbox.addWidget(frame)

		vbox2 = QVBoxLayout(frame)
		vbox2.setMargin(10)

		sync = self.app.portfolio.portPrefs.getSync()

		self.syncIcarra = QCheckBox("Sync with Icarra")
		self.connect(self.syncIcarra, SIGNAL("clicked()"), self.twiddleIcarra)
		if "icarra" in sync:
			self.syncIcarra.setChecked(True)
		vbox2.addWidget(self.syncIcarra)
		
		self.syncYahoo = QCheckBox("Sync with Yahoo Finance")
		self.connect(self.syncYahoo, SIGNAL("clicked()"), self.twiddleYahoo)
		self.syncYahoo.setDisabled(True)
		if "yahoo" in sync:
			self.syncYahoo.setChecked(True)
		vbox2.addWidget(self.syncYahoo)

		self.syncGoogle = QCheckBox("Sync with Google Finance")
		self.connect(self.syncGoogle, SIGNAL("clicked()"), self.twiddleGoogle)
		self.syncGoogle.setDisabled(True)
		if "google" in sync:
			self.syncGoogle.setChecked(True)
		vbox2.addWidget(self.syncGoogle)

		self.syncMorningstar = QCheckBox("Sync with Morningstar")
		self.connect(self.syncMorningstar, SIGNAL("clicked()"), self.twiddleMorningstar)
		self.syncMorningstar.setDisabled(True)
		if "morningstar" in sync:
			self.syncMorningstar.setChecked(True)
		vbox2.addWidget(self.syncMorningstar)
		vbox2.addSpacing(10)

		self.syncButton = QPushButton("Sync " + portfolio.name)
		self.syncButton.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
		self.connect(self.syncButton, SIGNAL("clicked()"), self.sync)
		vbox2.addWidget(self.syncButton)

		# Set timer for tutorial
		self.tutorialTimer = QTimer()
		self.tutorialTimer.setInterval(500)
		self.tutorialTimer.setSingleShot(True)
		self.connect(self.tutorialTimer, SIGNAL("timeout()"), self.checkTutorial)
		self.tutorialTimer.start()

	def twiddleIcarra(self):
		sync = self.app.portfolio.portPrefs.getSync()
		if self.syncIcarra.isChecked():
			if not "icarra" in sync:
				sync.append("icarra")
		else:
			if "icarra" in sync:
				sync.remove("icarra")
		self.app.portfolio.portPrefs.setSync(",".join(sync))
	
	def twiddleYahoo(self):
		sync = self.app.portfolio.portPrefs.getSync()
		if self.syncYahoo.isChecked():
			if not "yahoo" in sync:
				sync.append("yahoo")
		else:
			if "yahoo" in sync:
				sync.remove("yahoo")
		self.app.portfolio.portPrefs.setSync(",".join(sync))

	def twiddleGoogle(self):
		pass

	def twiddleMorningstar(self):
		pass

	def checkTutorial(self):
		tutorial.check(tutorial.sync)
	
	def sync(self):
		sync = self.app.portfolio.portPrefs.getSync()
		if "icarra" in sync:
			IcarraSynchronizer(self.app.portfolio).sync()
