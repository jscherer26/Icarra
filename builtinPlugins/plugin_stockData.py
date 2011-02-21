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

import copy
import cStringIO
import os
import sys

from editGrid import *
from plugin import *
from portfolio import *

class Plugin(PluginBase):
	def name(self):
		return 'Stock Data'

	def icarraVersion(self):
		return (0, 2, 0)

	def version(self):
		return (1, 0, 0)

	def initialize(self):
		pass

	def createWidget(self, parent):
		return StockDataWidget(parent)
	
	def reRender(self, panel, app):
		pass

	def finalize(self):
		pass

class StockDataModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		self.ticker = False
		self.dividends = False
	
	def setStockData(self):
		if not self.ticker:
			self.setData([])
			return
		
		if self.dividends:
			cols = 3
		else:
			cols = 8
		
		# Create columns
		cols = ["Date"]
		if self.dividends:
			cols.append("Shares")
			cols.append("Value")
			cols.append("Type")
			cols.append("Amount")
			cols.append("Total")
		else:
			cols.append("Shares")
			cols.append("Value")
			cols.append("Open")
			cols.append("High")
			cols.append("Low")
			cols.append("Close")
			cols.append("Volume")
		self.setColumns(cols)
		
		self.priceMap = {}
		self.dividendMap = {}
		self.splitMap = {}
		row = 0
		
		app = appGlobal.getApp()
		positionData = app.portfolio.getPositionHistory(self.ticker)
		stockData = []
		if self.dividends:
			divs = app.stockData.getDividends(self.ticker, desc = True)
			splits = app.stockData.getSplits(self.ticker, desc = True)
			currDiv = 0
			currSplit = 0
			
			while currDiv < len(divs) or currSplit < len(splits):
				if currDiv < len(divs) and (currSplit >= len(splits) or splits[currSplit]["date"] <= divs[currDiv]["date"]):
					d = divs[currDiv]
					newRow = [d["date"]]
					if d["date"] in positionData:
						data = positionData[d["date"]]
						newRow.append(Transaction.formatFloat(data["shares"]))
						newRow.append(Transaction.formatDollar(data["value"]))
					else:
						newRow.append("")
						newRow.append("")
					newRow.append("Dividend")
					newRow.append(Transaction.formatDollar(d["value"]))
					myDiv = app.portfolio.getDividendForDate(self.ticker, d["date"])
					if myDiv:
						newRow.append(myDiv.formatTotal())
					else:
						newRow.append("")
					stockData.append(newRow)
					currDiv += 1
					self.dividendMap[row] = d
					row += 1
				
				# Show splits if date is <= dividend or no dividends left
				if currSplit < len(splits) and (currDiv >= len(divs) or splits[currSplit]["date"] >= divs[currDiv]["date"]):
					s = splits[currSplit]
					newRow = [s["date"]]
					newRow.append("")
					newRow.append("")
					newRow.append("Stock Split")
					newRow.append(Transaction.splitValueToString(s["value"]))
					stockData.append(newRow)
					currSplit += 1
					self.splitMap[row] = s
					row += 1
		else:
			# Get all data
			prices = app.stockData.getPrices(self.ticker, desc = True)
			
			keys = positionData.keys()
			keys.sort()
			keys.reverse()
			currPos = 0
			currPrice = 0
			while currPrice < len(prices):
				p = prices[currPrice]

				newRow = [p["date"]]
				
				# Output missing data
				while currPos < len(keys) and keys[currPos] > p["date"]:
					data = positionData[keys[currPos]]
					row2 = [keys[currPos], Transaction.formatFloat(data["shares"]), Transaction.formatDollar(data["value"])]

					stockData.append(row2)
					row += 1
					currPos += 1
					
				# Check if held on date
				if currPos < len(keys) and keys[currPos] == p["date"]:
					data = positionData[p["date"]]
					newRow.append(Transaction.formatFloat(data["shares"]))
					newRow.append(Transaction.formatDollar(data["value"]))
					currPos += 1
				else:
					newRow.append("")
					newRow.append("")
				newRow.append(Transaction.formatDollar(p["open"]))
				newRow.append(Transaction.formatDollar(p["high"]))
				newRow.append(Transaction.formatDollar(p["low"]))
				newRow.append(Transaction.formatDollar(p["close"]))
				newRow.append(Transaction.formatFloat(p["volume"], commas = True))
				stockData.append(newRow)
				self.priceMap[row] = p

				row += 1
				currPrice += 1
		
			# Output remaining data
			while currPos < len(keys):
				data = positionData[keys[currPos]]
				row2 = [keys[currPos], Transaction.formatFloat(data["shares"]), Transaction.formatDollar(data["value"])]

				stockData.append(row2)
				row += 1
				currPos += 1
		self.setData(stockData)
		
class StockDataWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.model = StockDataModel()
		
		app = appGlobal.getApp()
	
		self.tickersNormal = app.portfolio.getTickers()
		if not self.tickersNormal:
			return
		def getName(ticker):
			name = app.stockData.getName(ticker)
			if name:
				return ticker + " - " + name
			else:
				return ticker
		self.tickers = map(getName, self.tickersNormal)

		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		
		hbox = QHBoxLayout()
		vbox.addLayout(hbox)

		hbox.addWidget(QLabel("Ticker:"))

		ticker = app.portfolio.getLastTicker()
		# Convert __CASH__ to Cash, keep index the same
		if "__CASH__" in self.tickers:
			self.tickers.pop(self.tickers.index("__CASH__"))
		self.tickers.insert(0, "Cash")
		if "__CASH__" in self.tickers:
			self.tickersNormal.pop(self.tickers.index("__CASH__"))
		self.tickersNormal.insert(0, "__CASH__")

		if ticker == "__ALL__":
			if len(self.tickers) > 1:
				ticker = self.tickers[1]
		self.model.ticker = ticker
		self.tickerCombo = QComboBox()
		self.tickerCombo.addItems(self.tickers)
		if ticker in self.tickersNormal:
			self.tickerCombo.setCurrentIndex(self.tickersNormal.index(ticker))
		elif ticker == "__CASH__":
			self.tickerCombo.setCurrentIndex(self.tickers.index("Cash"))
		self.tickerCombo.setMaximumWidth(120)
		hbox.addWidget(self.tickerCombo)
		self.connect(self.tickerCombo, SIGNAL("currentIndexChanged(int)"), self.update)

		hbox.addWidget(QLabel("Icarra Ticker:"))
		
		icarraTicker = app.stockData.getIcarraTicker(ticker)
		self.icarraTicker = QLineEdit()
		self.icarraTicker.setText(icarraTicker)
		self.icarraTicker.setMaximumWidth(120)
		hbox.addWidget(self.icarraTicker)
		self.connect(self.icarraTicker, SIGNAL("textChanged(QString)"), self.icarraTickerChanged)
	
		self.suggestButton = QPushButton("Suggest")
		hbox.addWidget(self.suggestButton)
		self.connect(self.suggestButton, SIGNAL("clicked()"), self.suggest)

		hbox2 = QHBoxLayout()
		vbox.addLayout(hbox2)

		addData = QPushButton("Add data")
		hbox2.addWidget(addData)
		self.connect(addData, SIGNAL("clicked()"), self.new)

		self.editData = QPushButton("Edit data")
		hbox2.addWidget(self.editData)
		self.editData.setEnabled(False)
		self.connect(self.editData, SIGNAL("clicked()"), self.edit)

		self.deleteData = QPushButton("Delete data")
		hbox2.addWidget(self.deleteData)
		self.deleteData.setEnabled(False)
		self.connect(self.deleteData, SIGNAL("clicked()"), self.delete)

		self.dividends = QCheckBox("Dividends")
		hbox2.addWidget(self.dividends)
		self.connect(self.dividends, SIGNAL("stateChanged(int)"), self.newDividends)

		hbox2.addStretch(1000)
		
		hbox.addStretch(1000)
		
		self.table = EditGrid(self.model, sorting = True)
		#self.table.horizontalHeader().setResizeMode(QHeaderView.Stretch)
		self.model.setStockData()
		self.table.resizeColumnsToContents()
		vbox.addWidget(self.table)
		
		self.connect(self.table.selectionModel(), SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.selectedRow)

	def newDividends(self, value):
		self.model.dividends = value == Qt.Checked
		self.model.setStockData()
		self.table.resizeColumnsToContents()

	def icarraTickerChanged(self, newTicker):
		currentTicker = str(self.tickers[self.tickerCombo.currentIndex()])
		appGlobal.getApp().stockData.setIcarraTicker(currentTicker, str(newTicker))
	
	def suggest(self):
		app = appGlobal.getApp()
		suggestions = app.stockData.suggest(self.model.ticker)
		
		if not suggestions:
			return
		
		choices = []
		for s in suggestions:
			choices.append("%s: %s" % (s[0], s[1]))
		(sel, ok) = QInputDialog.getItem(self, "Choose Icarra Ticker", "Choose the most appropriate ticker:", choices, editable = False)
		if ok:
			sel = str(sel)
			# Strip out "ABC: abcdefgz"
			index = sel.find(": ")
			if index != -1:
				sel = sel[0:index]
			app.stockData.setIcarraTicker(self.model.ticker, sel)
			self.icarraTicker.setText(sel)
		
	def update(self, newIndex):
		# Get ticker, check for removal of XXX - YYYYY
		ticker = str(self.tickerCombo.currentText())
		index = ticker.find(" - ")
		if index != -1:
			ticker = ticker[0:index]
		if ticker == "Cash":
			ticker = "__CASH__"
		self.model.ticker = ticker

		app = appGlobal.getApp()
		if ticker != app.portfolio.getLastTicker() and ticker in app.portfolio.getTickers():
			app.portfolio.setLastTicker(ticker)
	
		self.model.setStockData()
		self.table.resizeColumnsToContents()
	
	def selectedRow(self):
		if self.table.selectedRow() in self.model.priceMap:
			self.editData.setEnabled(True)
			self.deleteData.setEnabled(True)
		else:
			self.editData.setEnabled(False)
			self.deleteData.setEnabled(False)

	def new(self):
		n = NewStockData(self)
		res = n.exec_()
		if res == QDialog.Accepted:
			self.model.setStockData()
			self.table.resizeColumnsToContents()
	
	def edit(self):
		app = appGlobal.getApp()

		row = self.table.selectedRow()
		if self.dividends.isChecked():
			if row in self.model.dividendMap:
				div = self.model.dividendMap[row]
				n = NewStockData(self, div, self.model.ticker, "Dividend")
				res = n.exec_()
			elif row in self.model.splitMap:
				split = self.model.splitMap[row]
				n = NewStockData(self, split, self.model.ticker, "Split")
				res = n.exec_()
		else:
			price = self.model.priceMap[row]
			n = NewStockData(self, price, self.model.ticker, "Price")
			res = n.exec_()
		
		if res == QDialog.Accepted:
			self.model.setStockData()
			self.table.selectRow(row)
			self.table.resizeColumnsToContents()
	
	def delete(self):
		app = appGlobal.getApp()
		# Ask for confirmation
		d = QMessageBox(QMessageBox.Question, "Are you sure?", "Are you sure you wish to delete this stock data?", QMessageBox.Ok | QMessageBox.Cancel)
		val = d.exec_()
		if val == QMessageBox.Ok:
			row = self.table.selectedRow()
			if self.dividends.isChecked():
				if row in self.model.dividendMap:
					div = self.model.dividendMap[row]
					app.stockData.db.delete("stockDividends", {"ticker": self.model.ticker, "date": div["date"].strftime("%Y-%m-%d %H:%M:%S")})
				elif row in self.model.splitMap:
					split = self.model.splitMap[row]
					app.stockData.db.delete("stockSplits", {"ticker": self.model.ticker, "date": split["date"].strftime("%Y-%m-%d %H:%M:%S")})
			else:
				price = self.model.priceMap[row]
				app.stockData.db.delete("stockData", {"ticker": self.model.ticker, "date": price["date"].strftime("%Y-%m-%d %H:%M:%S")})

			self.model.setStockData()
			self.table.resizeColumnsToContents()

class NewStockData(QDialog):
	def __init__(self, parent, data = False, ticker = False, dataType = False):
		QDialog.__init__(self, parent)
		if data == False:
			self.setWindowTitle("New Data")
		else:
			self.setWindowTitle("Edit Data")
		self.app = appGlobal.getApp()
		self.data = data
		self.dataType = dataType
		
		self.dollarRe = QRegExp("\$?[0-9]*\.?[0-9]*")
		self.splitRe = QRegExp("[0-9]+-[0-9]+")
		self.intRe = QRegExp("[0-9]*")

		vert = QVBoxLayout(self)
		
		grid = QGridLayout()
		vert.addLayout(grid)

		# Show type combo if not editing
		row = 0

		label = QLabel("Type:")
		self.typeLabel = label
		grid.addWidget(label, 0, 0)

		if data:
			self.typeCombo = QLabel(dataType)
			grid.addWidget(self.typeCombo, 0, 1)
		else:
			self.dataTypes = ["Price", "Dividend", "Split"]
			type = "Price"
			self.typeCombo = QComboBox()
			self.typeCombo.addItems(self.dataTypes)
			self.connect(self.typeCombo, SIGNAL("currentIndexChanged(int)"), self.newType)
			grid.addWidget(self.typeCombo, 0, 1)
			
		row += 1

		# Add ticker, but do not allow editing, only new
		self.tickerLabel = QLabel("Position:")
		grid.addWidget(self.tickerLabel, row, 0)
		self.tickers = self.app.stockData.getTickers()
		if self.tickers:
			if not ticker:
				ticker = self.app.portfolio.getLastTicker()
		else:
			ticker = ""
		if data:
			self.ticker = QLabel(ticker)
		else:
			self.ticker = QComboBox()
			self.ticker.setEditable(True)
			self.ticker.addItems(self.tickers)
			if ticker in self.tickers:
				self.ticker.setCurrentIndex(self.tickers.index(ticker))
		grid.addWidget(self.ticker, row, 1)
		row += 1

		label = QLabel("Date:")
		self.dateLabel = label
		grid.addWidget(label, row, 0)
		self.date = QDateEdit()
		self.date.setCalendarPopup(True)
		if data:
			dict = dateDict(data["date"])
			self.date.setDate(QDate(dict["y"], dict["m"], dict["d"]))
		else:
			self.date.setDate(QDate.currentDate())
		grid.addWidget(self.date, row, 1)
		row += 1

		# Ticker2 could be useful for spinoffs
		#self.ticker2Label = QLabel(self, label = "New Position:")
		#grid.addWidget(self.ticker2Label, row, 0)
		#if tickers:
		#	if transaction and transaction.ticker2:
		#		ticker = transaction.ticker2
		#	else:
		#		ticker = ""
		#else:
		#	ticker = "__ALL__"
		#self.ticker2.addChoices(tickers)
		#grid.addWidget(self.ticker2, row, 1)

		# TODO: set REs
		if dataType == "Price":
			open = str(data["open"])
		else:
			open = ""
		self.openLabel = QLabel("Open:")
		grid.addWidget(self.openLabel, row, 0)
		self.open = QLineEdit()
		self.open.setText(open)
		self.open.setValidator(QRegExpValidator(self.dollarRe, self.open))
		grid.addWidget(self.open, row, 1)
		row += 1
		
		if dataType == "Price":
			high = str(data["high"])
		else:
			high = ""
		self.highLabel = QLabel("High:")
		grid.addWidget(self.highLabel, row, 0)
		self.high = QLineEdit()
		self.high.setText(high)
		self.high.setValidator(QRegExpValidator(self.dollarRe, self.high))
		grid.addWidget(self.high, row, 1)
		row += 1

		if dataType == "Price":
			low = str(data["low"])
		else:
			low = ""
		self.lowLabel = QLabel("Low:")
		grid.addWidget(self.lowLabel, row, 0)
		self.low = QLineEdit()
		self.low.setText(low)
		self.low.setValidator(QRegExpValidator(self.dollarRe, self.low))
		grid.addWidget(self.low, row, 1)
		row += 1

		if dataType == "Price":
			close = str(data["close"])
		else:
			close = ""
		self.closeLabel = QLabel("Close:")
		grid.addWidget(self.closeLabel, row, 0)
		self.close = QLineEdit()
		self.close.setText(close)
		self.close.setValidator(QRegExpValidator(self.dollarRe, self.close))
		grid.addWidget(self.close, row, 1)
		row += 1
	
		if dataType == "Price":
			volume = str(data["volume"])
		else:
			volume = ""
		self.volumeLabel = QLabel("Volume:")
		grid.addWidget(self.volumeLabel, row, 0)
		self.volume = QLineEdit()
		self.volume.setText(volume)
		self.volume.setValidator(QRegExpValidator(self.intRe, self.volume))
		grid.addWidget(self.volume, row, 1)
		row += 1

		if not dataType or dataType == "Dividend" or dataType == "Split":
			self.valueLabel = QLabel("Value:")
			grid.addWidget(self.valueLabel, row, 0)
			self.value = QLineEdit()
			
			if dataType == "Dividend" or dataType == "Split":
				if dataType == "Dividend":
					self.value.setText(str(data["value"]))
					self.value.setValidator(QRegExpValidator(self.dollarRe, self.value))
				else:
					self.value.setText(Transaction.splitValueToString(data["value"]))
					self.value.setValidator(QRegExpValidator(self.splitRe, self.value))
			grid.addWidget(self.value, row, 1)
			row += 1

		# Buttons
		hbox = QHBoxLayout()
		vert.addLayout(hbox)

		ok = QPushButton("Ok")
		hbox.addWidget(ok)
		self.connect(ok, SIGNAL("clicked()"), self.onOk)

		cancel = QPushButton("Cancel")
		hbox.addWidget(cancel)
		self.connect(cancel, SIGNAL("clicked()"), SLOT("reject()"))

		self.enableDisable()
	
	def enableDisable(self):
		def DoLabelEnable(ctrl):
			ctrl.setEnabled(True)
			font = ctrl.font()
			font.setBold(True)
			ctrl.setFont(font)
		
		def DoLabelDisable(ctrl):
			ctrl.setEnabled(False)
			font = ctrl.font()
			font.setBold(False)
			ctrl.setFont(font)

		DoLabelEnable(self.typeLabel)
		DoLabelEnable(self.dateLabel)
		DoLabelEnable(self.tickerLabel)
		
		if self.dataType:
			type = self.dataType
		else:
			type = self.dataTypes[self.typeCombo.currentIndex()]
		if type  == "Price":
			self.open.setEnabled(True)
			self.high.setEnabled(True)
			self.low.setEnabled(True)
			self.close.setEnabled(True)
			self.volume.setEnabled(True)
			if not self.data:
				self.value.setEnabled(False)
				self.value.setText("")
				DoLabelDisable(self.valueLabel)
			DoLabelEnable(self.openLabel)
			DoLabelEnable(self.highLabel)
			DoLabelEnable(self.lowLabel)
			DoLabelEnable(self.closeLabel)
			DoLabelEnable(self.volumeLabel)
		else:
			self.open.setEnabled(False)
			self.open.setText("")
			self.high.setEnabled(False)
			self.high.setText("")
			self.low.setEnabled(False)
			self.low.setText("")
			self.close.setEnabled(False)
			self.close.setText("")
			self.volume.setEnabled(False)
			self.volume.setText("")
			if not self.data:
				self.value.setEnabled(True)
				DoLabelEnable(self.valueLabel)
			DoLabelDisable(self.openLabel)
			DoLabelDisable(self.highLabel)
			DoLabelDisable(self.lowLabel)
			DoLabelDisable(self.closeLabel)
			DoLabelDisable(self.volumeLabel)
			
			# Update validator, set to empty if invalid
			if type == "Dividend":
				self.value.setValidator(QRegExpValidator(self.dollarRe, self.value))
			else:
				self.value.setValidator(QRegExpValidator(self.splitRe, self.value))
			if self.value.validator().validate(self.value.text(), 0)[0] == QValidator.Invalid:
				self.value.setText("")

		
		#if "ticker2" in fields:
		#	self.ticker2.Enable(True)
		#	DoLabelEnable(self.ticker2Label)
		#else:
		#	self.ticker2.Enable(False)
		#	self.ticker2.SetValue("")
		#	DoLabelDisable(self.ticker2Label)
	
	def newType(self, event):
		self.enableDisable()
	
	def onOk(self):
		date = self.date.date()
		date = "%04d-%02d-%02d 00:00:00" % (date.year(), date.month(), date.day())
		dateDatetime = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")

		if self.dataType:
			ticker = str(self.ticker.text())
			type = self.dataType
			dateChanged = dateDatetime != self.data["date"]
		else:
			ticker = str(self.ticker.currentText())
			type = self.dataTypes[self.typeCombo.currentIndex()]
			dateChanged = True
		
		if type == "Price":
			# Check for invalid date
			if dateChanged and self.app.stockData.getPrice(ticker, dateDatetime):
				QMessageBox(QMessageBox.Critical, 'Duplicate Date', 'Stock data already exists on this date').exec_()
				return

			open = str(self.open.text()).strip("$").replace(",", "")
			low = str(self.low.text()).strip("$").replace(",", "")
			high = str(self.high.text()).strip("$").replace(",", "")
			close = str(self.close.text()).strip("$").replace(",", "")
			volume = str(self.volume.text()).replace(",", "")
			
			# Check for bad close
			if close == "" or float(close) == 0:
				QMessageBox(QMessageBox.Critical, 'Invalid Close', 'Please choose a valid closing price').exec_()
				return

			data = {"ticker": ticker,
				"date": date,
				"close": close}
			if open != "":
				data["open"] = open
			if high != "":
				data["high"] = high
			if low != "":
				data["low"] = low
			if volume != "":
				data["volume"] = volume
			
			if self.data:
				# Update existing data
				self.app.stockData.db.update("stockData", data, where =
					{"ticker": ticker, 
					"date": self.data["date"].strftime("%Y-%m-%d %H:%M:%S")})
			else:
				# Insert new data
				self.app.stockData.db.insert("stockData", data)
		elif type == "Dividend" or type == "Split":
			value = str(self.value.text()).strip(",").strip("$")
			
			# Check for invalid date
			if type == "Dividend":
				if dateChanged and self.app.stockData.getDividend(ticker, dateDatetime):
					QMessageBox(QMessageBox.Critical, 'Duplicate Date', 'Dividend data already exists on this date').exec_()
					return
			elif type == "Split":
				totalError = "The total field should be in the form of X-Y where you receive X shares for every Y share you own.  For example 2-1 would double your shares."
				vals = value.split("-")
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
				value = num / den

			# Check for bad value
			if value == "" or float(value) == 0:
				QMessageBox(QMessageBox.Critical, 'Invalid Value', 'Please choose a valid dividend value').exec_()
				return
			
			# Insert or update dividend/split
			data = {"ticker": ticker,
				"date": date,
				"value": value}
			if self.data:
				# Update existing data
				if type == "Dividend":
					self.app.stockData.db.update("stockDividends", data, where =
					{"ticker": ticker, 
					"date": self.data["date"].strftime("%Y-%m-%d %H:%M:%S")})
				else:
					self.app.stockData.db.update("stockSplits", data, where =
					{"ticker": ticker, 
					"date": self.data["date"].strftime("%Y-%m-%d %H:%M:%S")})
			else:
				if type == "Dividend":
					self.app.stockData.db.insert("stockDividends", data)
				else:
					self.app.stockData.db.insert("stockSplits", data)
		
		#if self.ticker2.GetValue():
		#	t.setTicker2(self.ticker2.GetValue())
		
		# If editing, copy over id
		
		self.accept()
