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
				appGlobal.getApp().toolWidget.model.setTransactions()
					
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
		QDialog.__init__(self, parent)
		self.setWindowTitle("Import Transactions")
		
		self.app = appGlobal.getApp()
		self.ok = False
		self.didImport = False

		layout = QVBoxLayout(self)
		layout.addSpacing(10)

		portfolio = self.app.portfolio
		if not portfolio.brokerage:
			layout.addWidget(QLabel("Set Brokerage and Username in Settings before downloading"))
		elif not portfolio.username:
			layout.addWidget(QLabel("Set Username in Settings before downloading"))

		self.ofx = QRadioButton("Download from " + portfolio.brokerage, self)
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
		layout.addSpacing(10)

		self.file = QRadioButton("Import from file", self)
		self.connect(self.file, SIGNAL("toggled(bool)"), self.radio)
		layout.addWidget(self.file)
		layout.addSpacing(10)

		# Set last import mode
		if not portfolio.brokerage or not portfolio.username:
			self.file.click()
			self.ofx.setDisabled(True)
			self.password.setDisabled(True)
			self.passwordLabel.setDisabled(True)
		elif portfolio.portPrefs.getLastImport() == "file":
			self.file.click()
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
			else:
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
		except Exception, e:
			import traceback
			status.addError('Could not get transactions: %s' % traceback.format_exc())
			status.setFinished()
		
		self.accept()

class NewTransaction(QDialog):
	def __init__(self, parent, transaction = False):
		QDialog.__init__(self, parent)
		
		if transaction:
			self.setWindowTitle('Edit Transaction')
		else:
			self.setWindowTitle('New Transaction')
		self.transaction = transaction

		self.dollarRe = QRegExp("\$?[0-9]*\.?[0-9]*")
		self.splitRe = QRegExp("[0-9]+-[0-9]+")

		vbox = QVBoxLayout(self)
		
		# Widgets
		grid = QGridLayout()
		vbox.addLayout(grid)
		
		self.typeLabel = QLabel("Type:")
		transactionTypes = []
		for t in Transaction.forEdit():
			transactionTypes.append(Transaction.getTypeString(t))
		self.type = QComboBox()
		self.type.addItems(transactionTypes)
		if transaction:
			self.type.setCurrentIndex(transaction.type)
		grid.addWidget(self.typeLabel, 0, 0)
		grid.addWidget(self.type, 0, 1)
		
		self.connect(self.type, SIGNAL("currentIndexChanged(int)"), self.newType)

		self.dateLabel = QLabel("Date:")
		self.date = QDateEdit()
		if transaction:
			dict = dateDict(transaction.date)
			self.date.setDate(QDate(dict["y"], dict["m"], dict["d"]))
		else:
			self.date.setDate(QDate.currentDate())
		self.date.setCalendarPopup(True)
		grid.addWidget(self.dateLabel, 1, 0)
		grid.addWidget(self.date, 1, 1)

		self.tickerLabel = QLabel("Position:")
		self.ticker = QComboBox()
		tickers = appGlobal.getApp().portfolio.getTickers()
		if "__CASH__" in tickers:
			tickers.pop(tickers.index("__CASH__"))
			tickers.insert(0, "Cash")
		self.ticker.addItems(tickers)
		self.ticker.setEditable(True)
		if transaction:
			self.ticker.setEditText(transaction.formatTicker1())
		grid.addWidget(self.tickerLabel, 2, 0)
		grid.addWidget(self.ticker, 2, 1)

		self.ticker2Label = QLabel("New Position:")
		self.ticker2 = QComboBox()
		self.ticker2.addItems(tickers)
		self.ticker2.setEditable(True)
		if transaction and transaction.ticker2:
			self.ticker2.setEditText(transaction.formatTicker2())
		grid.addWidget(self.ticker2Label, 3, 0)
		grid.addWidget(self.ticker2, 3, 1)

		self.sharesLabel = QLabel("Shares:")
		self.shares = QLineEdit()
		self.shares.setValidator(QDoubleValidator(0, 1e9, 12, self.shares))
		if transaction:
			self.shares.setText(transaction.formatShares())
		grid.addWidget(self.sharesLabel, 4, 0)
		grid.addWidget(self.shares, 4, 1)

		self.connect(self.shares, SIGNAL("textChanged(QString)"), self.checkChangeTotal)

		self.pricePerShareLabel = QLabel("$/Share:")
		self.pricePerShare = QLineEdit()
		self.pricePerShare.setValidator(QRegExpValidator(self.dollarRe, self.pricePerShare))
		if transaction:
			self.pricePerShare.setText(transaction.formatPricePerShare())
		grid.addWidget(self.pricePerShareLabel, 5, 0)
		grid.addWidget(self.pricePerShare, 5, 1)

		self.connect(self.pricePerShare, SIGNAL("textChanged(QString)"), self.checkChangeTotal)

		self.feeLabel = QLabel("Fee:")
		self.fee = QLineEdit()
		self.fee.setValidator(QRegExpValidator(self.dollarRe, self.fee))
		if transaction:
			self.fee.setText(transaction.formatFee())
		grid.addWidget(self.feeLabel, 6, 0)
		grid.addWidget(self.fee, 6, 1)

		self.totalLabel = QLabel("Total:")
		self.total = QLineEdit()
		self.total.setValidator(QRegExpValidator(self.dollarRe, self.total))
		grid.addWidget(self.totalLabel, 7, 0)
		grid.addWidget(self.total, 7, 1)

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
			if not type in [Transaction.spinoff, Transaction.tickerChange, Transaction.expense]:
				QMessageBox(QMessageBox.Critical, "Invalid total", "Please enter a proper value for Total").exec_()
				return
		if total and (type == Transaction.sell or type == Transaction.withdrawal or type == Transaction.expense):
			total = -abs(total)
		
		ticker = str(self.ticker.currentText())
		if ticker == "Cash":
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
			fee)
	
		if self.ticker2.currentText():
			t.setTicker2(str(self.ticker2.currentText()))
				
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
			
		def labelTwiddle(label, enabled):
			label.setDisabled(not enabled)
			font = label.font()
			font.setBold(enabled)
			label.setFont(font)
		
		labelTwiddle(self.typeLabel, True)
		labelTwiddle(self.dateLabel, True)
		labelTwiddle(self.feeLabel, True)

		fields = Transaction.fieldsForTransaction(type)
		if "ticker" in fields:
			self.ticker.setDisabled(False)
			labelTwiddle(self.tickerLabel, True)
		else:
			self.ticker.setDisabled(True)
			self.ticker.setEditText("Cash")
			labelTwiddle(self.tickerLabel, False)

		if "ticker2" in fields:
			self.ticker2.setDisabled(False)
			labelTwiddle(self.ticker2Label, True)
		else:
			self.ticker2.setDisabled(True)
			self.ticker2.setEditText("")
			labelTwiddle(self.ticker2Label, False)

		if "shares" in fields:
			self.shares.setDisabled(False)
			labelTwiddle(self.sharesLabel, True)
		else:
			self.shares.setDisabled(True)
			self.shares.setText("")
			labelTwiddle(self.sharesLabel, False)

		if "pricePerShare" in fields:
			self.pricePerShare.setDisabled(False)
			labelTwiddle(self.pricePerShareLabel, True)
		else:
			self.pricePerShare.setDisabled(True)
			self.pricePerShare.setText("")
			labelTwiddle(self.pricePerShareLabel, False)

		if "total" in fields:
			self.total.setDisabled(False)
			labelTwiddle(self.totalLabel, True)
		else:
			self.total.setDisabled(True)
			self.total.setText("")
			labelTwiddle(self.totalLabel, False)
		
		# Check that total is a valid string
		if type == Transaction.split:
			self.total.setValidator(QRegExpValidator(self.splitRe, self.total))
		else:
			self.total.setValidator(QRegExpValidator(self.dollarRe, self.total))
		if self.total.validator().validate(self.total.text(), 0)[0] == QValidator.Invalid:
			self.total.setText('')
	
	def checkChangeTotal(self, ignoreStr = "ignore"):
		shares = self.shares.text()
		pps = self.pricePerShare.text().replace("$", "")
		
		if shares != "" and pps != "":
			total = QString()
			total.setNum(float(shares) * float(pps))
			self.total.setText('$' + total)
		else:
			self.total.setText('')

	def newType(self, index):
		self.enableDisable()

class TransactionModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		
		self.showDeleted = False
		self.ticker = appGlobal.getApp().portfolio.getLastTicker()
		if self.ticker == "False" or self.ticker == "__COMBINED__":
			self.ticker = False

		columns = ["Date", "Position", "Transaction", "Shares", "$/Share", "Fee", "Total"]
		if appGlobal.getApp().prefs.getShowCashInTransactions():
			columns.append("Cash")
		self.setColumns(columns)

		self.setTransactions()
	
	def setTransactions(self):
		app = appGlobal.getApp()
		trans = app.portfolio.getTransactions(deletedOnly = self.showDeleted)
		self.transactions = []
		self.transactionIds = []
		
		# Build cash position if set
		showCash = app.prefs.getShowCashInTransactions()
		if showCash:
			trans.reverse()
			cash = 0
			for t in trans:
				if t.type in [Transaction.deposit, Transaction.sell, Transaction.dividend, Transaction.cover]:
					cash += abs(t.total)
				elif t.type in [Transaction.withdrawal, Transaction.buy, Transaction.expense, Transaction.short]:
					cash -= abs(t.total)
				elif t.type == Transaction.adjustment and t.ticker == "__CASH__":
					cash += t.total
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
		self.tickers = appGlobal.getApp().portfolio.getTickers()
		if "__CASH__" in self.tickers:
			self.tickers.pop(self.tickers.index("__CASH__"))
			self.tickers.insert(0, "Cash")
		self.tickers.insert(0, "All Positions")
		self.tickerBox.addItems(self.tickers)
		lastTicker = appGlobal.getApp().portfolio.getLastTicker()
		if lastTicker == False:
			self.tickerBox.setCurrentIndex(0)
		elif lastTicker == "__CASH__":
			self.tickerBox.setCurrentIndex(1)
		elif lastTicker in self.tickers:
			self.tickerBox.setCurrentIndex(self.tickers.index(lastTicker))
		self.tickerBox.setMaximumWidth(150)
		hor.addWidget(self.tickerBox)

		self.showDeleted = QCheckBox("Show Deleted")
		hor.addWidget(self.showDeleted)
		self.connect(self.showDeleted, SIGNAL("stateChanged(int)"), self.changeShowDeleted)
		
		portfolio = appGlobal.getApp().portfolio

		self.importTransactionButton = QPushButton("Import")
		if not portfolio.isBrokerage():
			self.importTransactionButton.setDisabled(True)
		hor2.addWidget(self.importTransactionButton)
		self.connect(self.importTransactionButton, SIGNAL("clicked()"), self.importTransactions)

		self.newTransactionButton = QPushButton("New")
		if not portfolio.isBrokerage():
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

		self.connect(self.tickerBox, SIGNAL("currentIndexChanged(int)"), self.newTicker)

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
		if self.model.sortOrder == Qt.AscendingOrder:
			row = -row - 1
		id = self.model.transactionIds[row]
		
		# Loop over transactions, edit id, reselect row and finish
		for t in appGlobal.getApp().portfolio.getTransactions():
			if t.uniqueId == id:
				NewTransaction(self, t).exec_()
				self.table.selectRow(row)
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
			appGlobal.getApp().portfolio.setDirty()
			self.model.setTransactions()
	
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
		elif ticker == "Cash":
			self.model.ticker = "__CASH__"
		else:
			self.model.ticker = ticker
		appGlobal.getApp().portfolio.setLastTicker(self.model.ticker)
		self.model.setTransactions()
	
	def selectedRow(self, deselected, selected):
		# Update tool action to allow editing/deleting transactions
		if len(self.table.selectionModel().selectedRows()) > 0 and appGlobal.getApp().portfolio.isBrokerage():
			self.deleteTransactionButton.setDisabled(False)
			self.editTransactionButton.setDisabled(False)
		else:
			self.deleteTransactionButton.setDisabled(True)
			self.editTransactionButton.setDisabled(True)
