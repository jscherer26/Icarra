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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from plugin import *
from editGrid import *
from statusUpdate import *
import appGlobal
import tutorial
import autoUpdater
from icarraWebBrowser import *

global haveKeyring
try:
	import keyring
	haveKeyring = True
except:
	haveKeyring = False

class Plugin(PluginBase):
	def __init__(self):
		PluginBase.__init__(self)
		
	def name(self):
		return "Transactions"
	
	def icarraVersion(self):
		return (0, 0, 0)

	def version(self):
		return (1, 0, 0)

	def createWidget(self, parent):
		return TransactionWidget(parent)

	@staticmethod
	def doImport(parent = None):
		portfolio = appGlobal.getApp().portfolio
		
		d = Import(parent)
		d.exec_()
		if d.didImport:
			portfolio.readFromDb()
			if appGlobal.getApp().tool.name() == "Transactions":
				appGlobal.getApp().toolWidget.rebuildPositions()
				appGlobal.getApp().toolWidget.model.setTransactions()
				appGlobal.getApp().toolWidget.table.resizeColumnsToContents()

class WebImport(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		
		self.setMinimumSize(300, 200)
		self.resize(800, 600)
		
		vert = QVBoxLayout(self)
		vert.setMargin(0)
		
		vert.addWidget(QLabel("Download transaction history from your bank or brokerage website"))

		self.webView = WebBrowser(self, downloadImport = True)
		self.webView.changeUrlCallback = self.newUrl
		self.webView.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
		vert.addWidget(self.webView)
		
		# Check if user has saved a url
		url = appGlobal.getApp().portfolio.portPrefs.getUrl()
		if url:
			self.webView.locationEdit.setText(url)
			self.webView.changeLocation()
		
		self.setStyleSheet("QLabel { padding: 5px }")
		
		self.exec_()
	
	def showEvent(self, showEvent):
		self.webView.locationEdit.setFocus()
	
	@staticmethod
	def newUrl(url):
		# User entered a new url, save
		appGlobal.getApp().portfolio.portPrefs.setUrl(url)

class AccountSelector(QDialog):
	def __init__(self, parent, choices):
		QDialog.__init__(self, parent)
		self.account = ""
		
		vert = QVBoxLayout(self)
		
		label = QLabel("Please choose your account:")
		vert.addWidget(label)
		
		if appGlobal.getApp().isOSX:
			vert.addWidget(QLabel("Shift or Command click to select multiple"))
		else:
			vert.addWidget(QLabel("Shift or Control click to select multiple"))
		
		# Make sure choices is a list
		if type(choices) != type([]):
			choices = [choices]
		self.choices = choices

		self.choicesList = QListView()
		self.choicesList.setModel(QStringListModel(choices))
		self.choicesList.setEditTriggers(QAbstractItemView.NoEditTriggers)
		self.choicesList.setSelectionMode(QAbstractItemView.ExtendedSelection)
		vert.addWidget(self.choicesList)
		
		buttons = QHBoxLayout()
		buttons.setAlignment(Qt.AlignRight)
		buttons.addStretch(1000)
		vert.addLayout(buttons)

		self.cancel = QPushButton("Cancel")
		self.cancel.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
		buttons.addWidget(self.cancel)
		self.connect(self.cancel, SIGNAL("clicked()"), SLOT("reject()"))
		
		self.ok = QPushButton("OK")
		self.ok.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
		self.ok.setDefault(True)
		buttons.addWidget(self.ok)
		self.connect(self.ok, SIGNAL("clicked()"), self.onOk)

		self.exec_()
	
	def onOk(self):
		indexes = self.choicesList.selectedIndexes()
		accounts = []
		for index in indexes:
			accounts.append(self.choices[index.row()])
		if len(accounts) > 1:
			self.account = ",".join(accounts)
		elif len(accounts) == 1:
			self.account = accounts[0]
		else:
			QMessageBox(QMessageBox.Information, "Please choose", "Please choose at least one account.").exec_()
			return
		self.accept()

class Import(QDialog):
	def __init__(self, parent = None):
		global haveKeyring
		QDialog.__init__(self, parent)
		self.setWindowTitle("Import Transactions")
		
		self.app = appGlobal.getApp()
		self.ok = False
		self.didImport = False

		layout = QVBoxLayout(self)
		layout.addSpacing(10)

		portfolio = self.app.portfolio
		if not portfolio.brokerage:
			layout.addWidget(QLabel("Set Brokerage and Username\nin Settings tool before downloading"))
			layout.addSpacing(10)
			radioStr = "Download from brokerage"
		elif not portfolio.username:
			layout.addWidget(QLabel("Set Username in Settings before downloading"))
			radioStr = "Download from " + portfolio.brokerage
		else:
			radioStr = "Download from " + portfolio.brokerage

		self.ofx = QRadioButton(radioStr, self)
		self.connect(self.ofx, SIGNAL("toggled(bool)"), self.radio)
		layout.addWidget(self.ofx)
		
		hbox = QHBoxLayout()
		hbox.addSpacing(20)
		layout.addLayout(hbox)
		
		self.passwordLabel = QLabel("Password: ")
		hbox.addWidget(self.passwordLabel)
		self.password = QLineEdit()
		self.password.setEchoMode(QLineEdit.Password)
		hbox.addWidget(self.password)
		
		# Check for keying, try to load password
		if haveKeyring and portfolio.username:
			self.savePassword = QCheckBox("Save Password")
			hbox2 = QHBoxLayout()
			hbox2.addSpacing(20)
			layout.addLayout(hbox2)
			hbox2.addWidget(self.savePassword)
			layout.addSpacing(10)

			try:
				password = keyring.get_password("Icarra-ofx-" + portfolio.name, portfolio.username)
				if password:
					self.password.setText(password)
					self.savePassword.setChecked(True)
			except:
				haveKeyring = False
				self.password.setDisabled(True)
				self.savePassword.setDisabled(True)

		self.file = QRadioButton("Import from file", self)
		self.connect(self.file, SIGNAL("toggled(bool)"), self.radio)
		layout.addWidget(self.file)
		layout.addSpacing(10)

		self.web = QRadioButton("Download from web", self)
		self.connect(self.file, SIGNAL("toggled(bool)"), self.radio)
		layout.addWidget(self.web)
		layout.addSpacing(10)

		# Set last import mode
		if portfolio.portPrefs.getLastImport() == "file":
			self.file.click()
		elif portfolio.portPrefs.getLastImport() == "web":
			self.web.click()
		elif not portfolio.brokerage or not portfolio.username:
			self.file.click()
			self.ofx.setDisabled(True)
			self.password.setDisabled(True)
			self.passwordLabel.setStyleSheet("color: gray")
		else:
			self.ofx.click()
			self.password.setFocus()
			
		buttons = QHBoxLayout()
		layout.addLayout(buttons)

		cancel = QPushButton("Cancel")
		buttons.addWidget(cancel)
		self.connect(cancel, SIGNAL("clicked()"), SLOT("reject()"))
		
		ok = QPushButton("Ok")
		ok.setDefault(True)
		buttons.addWidget(ok)
		self.connect(ok, SIGNAL("clicked()"), self.onOk)
		
	def radio(self, state):
		if self.ofx.isChecked():
			self.password.setDisabled(False)
			self.passwordLabel.setDisabled(False)
		else:
			self.password.setDisabled(True)
			self.passwordLabel.setDisabled(True)
	
	def onOk(self):
		portfolio = self.app.portfolio
		brokerage = self.app.plugins.getBrokerage(portfolio.brokerage)
		status = False
		try:
			if self.ofx.isChecked():
				status = StatusUpdate(self, cancelable = True, numTextLines = 3)
				status.setStatus("Logging in to " + portfolio.brokerage, 5)

				# Import from ofx
				self.app.portfolio.portPrefs.setLastImport("ofx")
				username = str(portfolio.username)
				password = str(self.password.text())
				account = portfolio.account
				
				if password == "":
					status.setStatus("Login not successful: Please enter a password", 100)
					return
				
				if portfolio.account == "" or portfolio.account == "(optional)" or not portfolio.account or portfolio.account == "None":
					status.setStatus("Retrieving account information", 10)
					(success, account) = getAccount(username, password, brokerage)
					if not success:
						status.setStatus("Login not successful: Could not get account: " + account, 100)
						return
					
					# If multiple accounts are chosen, bring up a selector dialog
					if type(account) == type([]):
						accountSelector = AccountSelector(status, account)
						account = accountSelector.account
						
						if account:
							portfolio.account = account
							self.app.prefs.updatePortfolio(portfolio.name, portfolio.brokerage, portfolio.username, account)
					else:
						# Single account
						portfolio.account = account
						self.app.prefs.updatePortfolio(portfolio.name, portfolio.brokerage, portfolio.username, account)

				# If still no account, abort
				if portfolio.account == "" or not portfolio.account or portfolio.account == "None":
					status.setStatus("Login not successful: Could not get account.", 100)
					return
				
				ofx = getOfx(username, password, brokerage, account, status)
				if ofx == "did not get account":
					status.setStatus("Sorry, we could not read your account information.", 100)
					return
				elif ofx == "could not connect":
					status.setStatus("We could not connect to %s.  Please check your internet connection." % portfolio.brokerage, 100)
					return
				elif ofx == "":
					status.setStatus("We could not download OFX data.  Please run with OFX Debug enabled.", 100)
					return
				elif ofx == "Invalid login":
					status.setStatus("Login not successful: Please check that your username and password are correct.", 100)
					return
				else:
					portfolio.updateFromFile(ofx, self.app, status)
					self.didImport = True
					
					if haveKeyring:
						if self.savePassword.isChecked():
							keyring.set_password("Icarra-ofx-" + portfolio.name, username, password)
						else:
							keyring.set_password("Icarra-ofx-" + portfolio.name, username, "")
			elif self.file.isChecked():
				# Import from file
				self.app.portfolio.portPrefs.setLastImport("file")
				fd = QFileDialog(caption = "Choose file to import...")
				fd.setAcceptMode(QFileDialog.AcceptOpen)
				res = fd.exec_()
				if res == QDialog.Accepted:
					status = StatusUpdate(self, numTextLines = 3)
					status.setStatus("Reading file", 10)

					for filename in fd.selectedFiles():
						f = open(filename, "r")
						data = f.read()

						portfolio.updateFromFile(data, self.app, status)
					self.didImport = True
			else:
				# Import from web
				self.accept()
				self.app.portfolio.portPrefs.setLastImport("web")
				w = WebImport(appGlobal.getApp().main)
				self.didImport = True
		except Exception, e:
			import traceback
			if status is False:
				status = StatusUpdate(self)
			status.addError('Could not get transactions: %s' % traceback.format_exc())
			status.setFinished()
		
		self.accept()

class NewTransaction(QDialog):
	def __init__(self, parent, transaction = False):
		QDialog.__init__(self, parent)
		portfolio = appGlobal.getApp().portfolio
		
		if transaction:
			self.setWindowTitle('Edit Transaction')
		else:
			self.setWindowTitle('New Transaction')
		self.transaction = transaction

		self.dollarRe = QRegExp("(\$|-|\$-|-\$)?[0-9]*\.?[0-9]*")
		self.splitRe = QRegExp("[0-9]+-[0-9]+")

		vbox = QVBoxLayout(self)
		
		# Widgets
		grid = QGridLayout()
		vbox.addLayout(grid)
		
		self.typeLabel = QLabel("<b>Type:</b>")
		transactionTypes = []
		if portfolio.isBrokerage():
			forEdit = Transaction.forEdit()
		else:
			forEdit = Transaction.forEditBank()
		for t in forEdit:
			transactionTypes.append(Transaction.getTypeString(t))
		self.type = QComboBox()
		self.type.addItems(transactionTypes)
		if transaction:
			self.type.setCurrentIndex(forEdit.index(transaction.type))
		grid.addWidget(self.typeLabel, 0, 0)
		grid.addWidget(self.type, 0, 1)
		
		self.connect(self.type, SIGNAL("currentIndexChanged(int)"), self.newType)

		optionHBox = QHBoxLayout(margin = 0)
		self.isPut = QRadioButton("Put")
		optionHBox.addWidget(self.isPut)
		self.isCall = QRadioButton("Call")
		optionHBox.addWidget(self.isCall)
		optionHBox.addStretch(1000)
		grid.addLayout(optionHBox, 1, 1)
		
		# Set options if necessary
		if transaction:
			if transaction.type in [Transaction.buyToOpen, Transaction.sellToClose, Transaction.sellToOpen, Transaction.buyToClose, Transaction.exercise, Transaction.assign]:
				if transaction.subType == Transaction.optionPut:
					self.isPut.setChecked(True)
				elif transaction.subType == Transaction.optionCall:
					self.isCall.setChecked(True)
		
		self.connect(self.isPut, SIGNAL("toggled(bool)"), self.changeStockPutCall)
		self.connect(self.isCall, SIGNAL("toggled(bool)"), self.changeStockPutCall)

		self.dateLabel = QLabel("<b>Date:</b>")
		self.date = QDateEdit()
		if transaction:
			dict = dateDict(transaction.date)
			self.date.setDate(QDate(dict["y"], dict["m"], dict["d"]))
		else:
			self.date.setDate(QDate.currentDate())
		self.date.setCalendarPopup(True)
		grid.addWidget(self.dateLabel, 2, 0)
		grid.addWidget(self.date, 2, 1)
		
		tickers = portfolio.getTickers(includeAllocation = True)
		if "__CASH__" in tickers:
			tickers.pop(tickers.index("__CASH__"))
			tickers.insert(0, "Cash Balance")
		completer = QCompleter(tickers)
		# Does not work with Qt.CaseInsensitive
		# completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
		completer.setCaseSensitivity(Qt.CaseInsensitive)

		self.tickerLabel = QLabel("<b>Position:</b>")
		self.ticker = QLineEdit()
		self.ticker.setCompleter(completer)
		if transaction:
			self.ticker.setText(transaction.formatTicker1())
		grid.addWidget(self.tickerLabel, 3, 0)
		grid.addWidget(self.ticker, 3, 1)

		self.strikeLabel = QLabel("<b>Strike:</b>")
		self.strike = QLineEdit()
		self.strike.setValidator(QRegExpValidator(self.dollarRe, self.strike))
		if transaction:
			self.strike.setText(transaction.formatStrike())
		grid.addWidget(self.strikeLabel, 4, 0)
		grid.addWidget(self.strike, 4, 1)

		self.expireLabel = QLabel("<b>Expire:</b>")
		self.expire = QDateEdit()
		if transaction and transaction.optionExpire:
			dict = dateDict(transaction.optionExpire)
			self.expire.setDate(QDate(dict["y"], dict["m"], dict["d"]))
		else:
			self.expire.setDate(QDate.currentDate())
		self.expire.setCalendarPopup(True)
		grid.addWidget(self.expireLabel, 5, 0)
		grid.addWidget(self.expire, 5, 1)

		self.ticker2Label = QLabel("<b>New Position:</b>")
		self.ticker2 = QLineEdit()
		self.ticker2.setCompleter(completer)
		if transaction and transaction.ticker2:
			self.ticker2.setText(transaction.formatTicker2())
		grid.addWidget(self.ticker2Label, 6, 0)
		grid.addWidget(self.ticker2, 6, 1)

		self.sharesLabel = QLabel("<b>Shares:</b>")
		self.shares = QLineEdit()
		self.shares.setValidator(QDoubleValidator(0, 1e9, 12, self.shares))
		if transaction:
			self.shares.setText(transaction.formatShares())
		grid.addWidget(self.sharesLabel, 7, 0)
		grid.addWidget(self.shares, 7, 1)

		self.connect(self.shares, SIGNAL("textChanged(QString)"), self.checkChangeTotal)

		self.pricePerShareLabel = QLabel("<b>$/Share:</b>")
		self.pricePerShare = QLineEdit()
		self.pricePerShare.setValidator(QRegExpValidator(self.dollarRe, self.pricePerShare))
		if transaction:
			self.pricePerShare.setText(transaction.formatPricePerShare())
		grid.addWidget(self.pricePerShareLabel, 8, 0)
		grid.addWidget(self.pricePerShare, 8, 1)

		self.connect(self.pricePerShare, SIGNAL("textChanged(QString)"), self.checkChangeTotal)

		self.feeLabel = QLabel("<b>Fee:</b>")
		self.fee = QLineEdit()
		self.fee.setValidator(QRegExpValidator(self.dollarRe, self.fee))
		if transaction:
			self.fee.setText(transaction.formatFee())
		grid.addWidget(self.feeLabel, 9, 0)
		grid.addWidget(self.fee, 9, 1)

		self.connect(self.fee, SIGNAL("textChanged(QString)"), self.checkChangeTotal)

		self.totalLabel = QLabel("<b>Total:</b>")
		self.total = QLineEdit()
		self.total.setValidator(QRegExpValidator(self.dollarRe, self.total))
		grid.addWidget(self.totalLabel, 10, 0)
		grid.addWidget(self.total, 10, 1)

		# Buttons
		hbox = QHBoxLayout()
		vbox.addLayout(hbox)

		cancel = QPushButton("Cancel")
		hbox.addWidget(cancel)
		self.connect(cancel, SIGNAL("clicked()"), SLOT("reject()"))
		
		ok = QPushButton("Ok")
		ok.setDefault(True)
		hbox.addWidget(ok)
		self.connect(ok, SIGNAL("clicked()"), self.ok)

		self.enableDisable()
	
		# Add total last incase it was removed
		if transaction:
			if transaction.total:
				self.total.setText(transaction.formatTotal())
			else:
				self.checkChangeTotal()

	def changeStockPutCall(self, state):
		self.enableDisable()

	def ok(self):
		date = self.date.date()
		date = "%04d-%02d-%02d 00:00:00" % (date.year(), date.month(), date.day())

		type = Transaction.forEdit()[self.type.currentIndex()]

		total = str(self.total.text()).strip("$").replace(",", "")
		if total:
			if type == Transaction.split:
				totalError = "The total field should be in the form of X-Y where you receive X shares for every Y share you own.  For example 2-1 would double your shares."
				vals = total.split("-")
				if len(vals) != 2:
					QMessageBox(QMessageBox.Critical, "Invalid split", totalError).exec_()
					return
				(num, den) = vals
				try:
					num = abs(float(num))
					den = abs(float(den))
				except Exception, e:
					QMessageBox(QMessageBox.Critical, "Invalid split", totalError).exec_()
					return
				if den < 1.0e-6:
					QMessageBox(QMessageBox.Critical, "Invalid split", "Split denominator must not be 0").exec_()
					return
				total = num / den
			else:
				total = float(total)
		else:
			# Spinoffs, ticker changes and expenses do not have total
			validTotal = True
			if type in [Transaction.spinoff, Transaction.tickerChange, Transaction.expense, Transaction.sellToOpen, Transaction.buyToClose, Transaction.exercise, Transaction.assign, Transaction.stockDividend, Transaction.transferIn, Transaction.transferOut]:
				pass
			elif not type in [Transaction.spinoff, Transaction.tickerChange, Transaction.expense, Transaction.sellToOpen, Transaction.buyToClose, Transaction.exercise, Transaction.assign, Transaction.stockDividend]:
				validTotal = False
			
			if not validTotal:
				QMessageBox(QMessageBox.Critical, "Invalid total", "Please enter a proper value for Total").exec_()
				return
		if total and (type == Transaction.sell or type == Transaction.buyToClose or type == Transaction.withdrawal or type == Transaction.expense):
			total = -abs(total)
		
		# Decide when to use __CASH__ position
		if type in [Transaction.deposit, Transaction.withdrawal]:
			ticker = "__CASH__"
		else:
			ticker = str(self.ticker.text())		
			if ticker == "Cash Balance":
				ticker = "__CASH__"
		
		fee = str(self.fee.text()).strip("$").replace(",", "")
		if fee:
			fee = float(fee)
			
		shares = str(self.shares.text())
		if shares:
			shares = float(shares)

		pricePerShare = str(self.pricePerShare.text()).strip("$").replace(",", "")
		if pricePerShare:
			pricePerShare = float(pricePerShare)
		
		# No subType or options by default
		subType = False
		optionExpire = False
		optionStrike = False
		
		# Check for options
		if type in [Transaction.buyToOpen, Transaction.sellToClose, Transaction.sellToOpen, Transaction.buyToClose, Transaction.exercise, Transaction.assign]:
			optionStrike = str(self.strike.text()).strip("$").replace(",", "")
			if optionStrike:
				optionStrike = float(optionStrike)
			
			if self.isPut.isChecked():
				subType = Transaction.optionPut
			elif self.isCall.isChecked():
				subType = Transaction.optionCall
			else:
				raise Exception("unknown option option")
			
			optionExpire = self.expire.date()
			optionExpire = "%04d-%02d-%02d 00:00:00" % (optionExpire.year(), optionExpire.month(), optionExpire.day())

		# We pass.  Now update transaction or create a new one.
		if self.transaction:
			id = self.transaction.uniqueId
		else:
			id = "__" + appGlobal.getApp().portfolio.portPrefs.getTransactionId() + "__"
		t = Transaction(
			str(id),
			ticker,
			date,
			type,
			total,
			shares,
			pricePerShare,
			fee,
			subType = subType,
			optionExpire = optionExpire,
			optionStrike = optionStrike)
	
		if self.ticker2.text():
			t.setTicker2(str(self.ticker2.text()))
				
		error = t.checkError()
		if not error:
			p = appGlobal.getApp().portfolio
			t.setEdited()
			t.save(p.db)
			p.portPrefs.setDirty(True)
			p.readFromDb()
			
			# Redraw transactions
			if appGlobal.getApp().tool.name() == "Transactions":
				appGlobal.getApp().toolWidget.model.setTransactions()

			# Accept insert/update
			self.accept()
		else:
			QMessageBox(QMessageBox.Critical, "New Transaction", "Please correct the following errors: " + error, QMessageBox.Ok).exec_()
	
	def enableDisable(self):
		type = Transaction.forEdit()[self.type.currentIndex()]
		if type >= Transaction.numTransactionTypes:
			return
					
		self.setUpdatesEnabled(False)

		fields = Transaction.fieldsForTransaction(type)
		if "ticker" in fields:
			self.ticker.setVisible(True)
			self.tickerLabel.setVisible(True)
		else:
			self.ticker.setVisible(False)
			self.tickerLabel.setVisible(False)
			self.ticker.setText("")

		if "ticker2" in fields:
			self.ticker2.setVisible(True)
			self.ticker2Label.setVisible(True)
		else:
			self.ticker2.setText("")
			self.ticker2.setVisible(False)
			self.ticker2Label.setVisible(False)

		if "shares" in fields:
			self.shares.setVisible(True)
			self.sharesLabel.setVisible(True)
		else:
			self.shares.setVisible(False)
			self.sharesLabel.setVisible(False)
			self.shares.setText("")

		if "pricePerShare" in fields:
			self.pricePerShare.setVisible(True)
			self.pricePerShareLabel.setVisible(True)
		else:
			self.pricePerShare.setVisible(False)
			self.pricePerShareLabel.setVisible(False)
			self.pricePerShare.setText("")

		if "total" in fields:
			self.total.setVisible(True)
			self.totalLabel.setVisible(True)
			self.total.setDisabled(False)
			self.totalLabel.setDisabled(False)
		elif "-total" in fields:
			self.total.setVisible(False)
			self.totalLabel.setVisible(False)
		else:
			self.total.setVisible(True)
			self.totalLabel.setVisible(True)
			self.total.setDisabled(True)
			self.totalLabel.setDisabled(True)
			self.total.setText("")
			self.checkChangeTotal()
		
		# Enable/disable put, call for options
		if type in [Transaction.buyToOpen, Transaction.sellToClose, Transaction.buyToClose, Transaction.sellToOpen, Transaction.exercise, Transaction.assign]:
			self.isPut.setVisible(True)
			self.isCall.setVisible(True)
			self.strike.setVisible(True)
			self.strikeLabel.setVisible(True)
			self.expire.setVisible(True)
			self.expireLabel.setVisible(True)
			if not self.isPut.isChecked() and not self.isCall.isChecked():
				self.isPut.setChecked(True)
		else:
			self.isPut.setVisible(False)
			self.isCall.setVisible(False)
			self.strike.setVisible(False)
			self.strikeLabel.setVisible(False)
			self.expire.setVisible(False)
			self.expireLabel.setVisible(False)
		
		# Check that total is a valid string
		if type == Transaction.split:
			self.total.setValidator(QRegExpValidator(self.splitRe, self.total))
		else:
			self.total.setValidator(QRegExpValidator(self.dollarRe, self.total))
		if self.total.validator().validate(self.total.text(), 0)[0] == QValidator.Invalid:
			self.total.setText('')
		
		# Resize
		appGlobal.getApp().processEvents()
		self.resize(self.sizeHint())
		self.setUpdatesEnabled(True)
		self.repaint()
	
	def checkChangeTotal(self, ignoreStr = "ignore"):
		shares = self.shares.text()
		pps = self.pricePerShare.text().replace("$", "").replace(",", "")
		fee = self.fee.text().replace("$", "").replace(",", "")
		
		# If short, no total
		type = Transaction.forEdit()[self.type.currentIndex()]
		if type == Transaction.short:
			if fee:
				self.total.setText(str(-float(fee)))
			else:
				self.total.setText("")
		elif type == Transaction.cover:
			# Covers do not set automatically
			pass
		elif shares != "" and pps != "":
			try:
				newTotal = float(shares) * float(pps)
				if fee != "":
					if type in [Transaction.sellToOpen, Transaction.sell, Transaction.sellToClose]:
						newTotal -= float(fee)
					else:
						newTotal += float(fee)
				self.total.setText(Transaction.formatDollar(newTotal))
			except:
				# Bad float value most likely
				self.total.setText("")
		else:
			self.total.setText("")

	def newType(self, index):
		self.enableDisable()

class TransactionModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		
		self.showDeleted = False
		self.ticker = appGlobal.getApp().portfolio.getLastTicker()
		if self.ticker == "False" or self.ticker == "__COMBINED__":
			self.ticker = False

		self.setTransactions()
	
		columns = ["Date", "Position", "Transaction", "Shares", "$/Share", "Fee", "Total"]
		if appGlobal.getApp().prefs.getShowCashInTransactions():
			columns.append("Cash Balance")
		self.setColumns(columns)

	def setTransactions(self):
		app = appGlobal.getApp()
		app.portfolio.readFromDb()
		trans = app.portfolio.getTransactions(deletedOnly = self.showDeleted)
		self.transactions = []
		self.transactionIds = []
		
		# Build cash position if set
		showCash = app.prefs.getShowCashInTransactions()
		if showCash:
			trans.reverse()
			cash = 0
			for t in trans:
				cash += t.getCashMod()
				t.computedCashValue = cash
			trans.reverse()

		for t in trans:
			if not self.ticker or t.ticker == self.ticker or t.ticker2 == self.ticker:
				self.transactionIds.append(t.uniqueId)

				row = [t.getDate(), t.formatTicker(), t.formatType()]
				if t.type in [Transaction.deposit, Transaction.withdrawal, Transaction.dividend, Transaction.adjustment, Transaction.expense, Transaction.split]:
					row.append("")
				else:
					row.append(t.formatShares())
				row.append(t.formatPricePerShare())
				row.append(t.formatFee())
				row.append(t.formatTotal())
				if showCash:
					row.append(Transaction.formatDollar(t.computedCashValue))

				self.transactions.append(row)

		self.setData(self.transactions)

class TransactionWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.model = TransactionModel(self)
		
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		
		hor = QHBoxLayout()
		hor.setMargin(0)
		vbox.addLayout(hor)

		hor2 = QHBoxLayout()
		hor2.setMargin(0)
		vbox.addLayout(hor2)
		
		self.positionLabel = QLabel("Position:")
		hor.addWidget(self.positionLabel)
		
		self.tickerBox = QComboBox()
		self.rebuildPositions()
		self.tickerBox.setMaximumWidth(150)
		hor.addWidget(self.tickerBox)

		self.showDeleted = QCheckBox("Show Deleted")
		hor.addWidget(self.showDeleted)
		self.connect(self.showDeleted, SIGNAL("stateChanged(int)"), self.changeShowDeleted)
		
		portfolio = appGlobal.getApp().portfolio

		self.importTransactionButton = QPushButton("Import")
		if not portfolio.isBrokerage() and not portfolio.isBank():
			self.importTransactionButton.setDisabled(True)
		hor2.addWidget(self.importTransactionButton)
		self.connect(self.importTransactionButton, SIGNAL("clicked()"), self.importTransactions)

		self.newTransactionButton = QPushButton("New")
		if not portfolio.isBrokerage() and not portfolio.isBank():
			self.newTransactionButton.setDisabled(True)
		hor2.addWidget(self.newTransactionButton)
		self.connect(self.newTransactionButton, SIGNAL("clicked()"), self.newTransaction)
		
		self.editTransactionButton = QPushButton("Edit")
		self.editTransactionButton.setDisabled(True)
		hor2.addWidget(self.editTransactionButton)
		self.connect(self.editTransactionButton, SIGNAL("clicked()"), self.editTransaction)

		self.deleteTransactionButton = QPushButton("Delete")
		self.deleteTransactionButton.setDisabled(True)
		hor2.addWidget(self.deleteTransactionButton)
		hor2.addStretch(1)
		self.connect(self.deleteTransactionButton, SIGNAL("clicked()"), self.deleteTransaction)
		
		if portfolio.isBenchmark():
			vbox.addWidget(QLabel("Note: Benchmark components may be changed in the Allocation tool"))
		elif portfolio.isCombined():
			vbox.addWidget(QLabel("Note: Combined components may be changed in the Settings tool"))

		hor.addStretch(1000)

		self.table = EditGrid(self.model, sorting = True)
		self.table.resizeColumnsToContents()
		#self.table.horizontalHeader().setResizeMode(QHeaderView.Stretch)
		#self.table.setShowGrid(False)
		vbox.addWidget(self.table)

		self.connect(self.table.selectionModel(), SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.selectedRow)

		# Set timer for tutorial
		if portfolio.isBrokerage() and portfolio.name != "Sample Portfolio":
			self.tutorialTimer = QTimer()
			self.tutorialTimer.setInterval(500)
			self.tutorialTimer.setSingleShot(True)
			self.connect(self.tutorialTimer, SIGNAL("timeout()"), self.checkTutorial)
			self.tutorialTimer.start()
	
	def rebuildPositions(self):
		# Temporarily unsubscribe while we change the ticker box
		self.disconnect(self.tickerBox, SIGNAL("currentIndexChanged(int)"), self.newTicker)
		self.tickerBox.clear()
		
		app = appGlobal.getApp()
		self.tickers = app.portfolio.getTickers()
		lastTicker = app.portfolio.getLastTicker()
		if "__CASH__" in self.tickers:
			self.tickers.pop(self.tickers.index("__CASH__"))
			self.tickers.insert(0, "Cash Balance")
		self.tickers.insert(0, "All Positions")
		self.tickerBox.addItems(self.tickers)
		if lastTicker == False:
			self.tickerBox.setCurrentIndex(0)
		elif lastTicker == "__CASH__":
			self.tickerBox.setCurrentIndex(1)
		elif lastTicker in self.tickers:
			self.tickerBox.setCurrentIndex(self.tickers.index(lastTicker))
		
		# Changing the combo box may change the last ticker, set it back
		self.connect(self.tickerBox, SIGNAL("currentIndexChanged(int)"), self.newTicker)
	
	def checkTutorial(self):
		tutorial.check(tutorial.transactions)

	def importTransactions(self):
		Plugin.doImport()

	def newTransaction(self):
		NewTransaction(self).exec_()

	def editTransaction(self):
		# Get transaction id
		row = self.table.selectedRow()
		if row == -1:
			return
		id = self.model.transactionIds[row]
		
		# Loop over transactions, edit id, reselect row and finish
		for t in appGlobal.getApp().portfolio.getTransactions():
			if t.uniqueId == id:
				NewTransaction(self, t).exec_()
				
				# Find the row for our transaction id, it may have changed
				i = 0
				for thisId in self.model.transactionIds:
					if thisId == id:
						self.table.selectRow(i)
						break
					i += 1
				break
			
	def deleteTransaction(self):
		# Get transaction id
		row = self.table.selectedRow()
		if row == -1:
			return
		id = self.model.transactionIds[row]
		
		found = False
		for t in appGlobal.getApp().portfolio.getTransactions(getDeleted = True):
			if t.uniqueId == id:
				found = True
				break
		if not found:
			return

		# Ask for confirmation, then delete
		if t.deleted:
			res = QMessageBox(QMessageBox.Critical, "Undelete Transaction", "Are you sure you wish to undelete this transaction?", QMessageBox.Cancel | QMessageBox.Ok).exec_()
		else:
			res = QMessageBox(QMessageBox.Critical, "Delete Transaction", "Are you sure you wish to delete this transaction?", QMessageBox.Cancel | QMessageBox.Ok).exec_()
		if res == QMessageBox.Ok:
			if t.deleted:
				t.setDeleted(False)
			else:
				t.setDeleted()
			t.save(appGlobal.getApp().portfolio.db)
			appGlobal.getApp().portfolio.portPrefs.setDirty(True)
			appGlobal.getApp().portfolio.readFromDb()
			self.model.setTransactions()
			autoUpdater.wakeUp()
	
	def changeShowDeleted(self, newValue):
		if newValue == Qt.Checked:
			self.model.showDeleted = True
			self.deleteTransactionButton.setText("Undelete Transaction")
		else:
			self.model.showDeleted = False
			self.deleteTransactionButton.setText("Delete Transaction")
		self.model.setTransactions()
	
	def newTicker(self, index):
		if index >= len(self.tickers):
			return
		
		ticker = self.tickers[index]
		if ticker == "All Positions":
			self.model.ticker = False
		elif ticker == "Cash Balance":
			self.model.ticker = "__CASH__"
		else:
			self.model.ticker = ticker
		appGlobal.getApp().portfolio.setLastTicker(self.model.ticker)
		self.model.setTransactions()
	
	def selectedRow(self, deselected, selected):
		# Update tool action to allow editing/deleting transactions
		if len(self.table.selectionModel().selectedRows()) > 0 and (appGlobal.getApp().portfolio.isBrokerage() or appGlobal.getApp().portfolio.isBank()):
			self.deleteTransactionButton.setDisabled(False)
			self.editTransactionButton.setDisabled(False)
		else:
			self.deleteTransactionButton.setDisabled(True)
			self.editTransactionButton.setDisabled(True)
