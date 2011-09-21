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

import locale
import appGlobal
import re

from editGrid import *
from transaction import *
from plugin import *

class Plugin(PluginBase):
	def name(self):
		return 'Allocation'

	def icarraVersion(self):
		return (0, 2, 0)

	def version(self):
		return (1, 0, 0)
	
	def forBank(self):
		return False

	def initialize(self):
		pass

	def createWidget(self, parent):
		return AllocationWidget(parent)
	
	def reRender(self, panel, app):
		pass

	def finalize(self):
		pass

def safeFloat(val):
	val = val.replace("$", "").replace(",", "").replace("%", "")
	p = re.compile("[^0-9.]")
	val = p.sub("", val)
	if val:
		return float(val)
	else:
		return ""

class AddAllocationPanel(QDialog):
	def __init__(self, parent = None):
		QDialog.__init__(self, parent)
		self.app = appGlobal.getApp()
		self.added = False
		self.setWindowTitle("Add To Allocation")
		
		vert = QVBoxLayout(self)
		grid = QGridLayout()
		vert.addLayout(grid)

		self.name = QLineEdit()
		self.name.setText("New Position")
		grid.addWidget(QLabel("Position:"), 0, 0)
		grid.addWidget(self.name, 0, 1)
		self.name.setFocus()
		self.name.setSelection(0, 200) # Select all

		# Buttons
		hbox = QHBoxLayout()
		vert.addLayout(hbox)

		cancel = QPushButton("Cancel")
		hbox.addWidget(cancel)
		self.connect(cancel, SIGNAL("clicked()"), SLOT("reject()"))
		
		ok = QPushButton("Ok")
		ok.setDefault(True)
		hbox.addWidget(ok)
		self.connect(ok, SIGNAL("clicked()"), self.onOk)

		self.exec_()
	
	def onOk(self):
		self.added = True
		
		self.app.portfolio.saveAllocation("", str(self.name.text()).upper(), 0.0)
		self.close()

class DeleteAllocationPanel(QDialog):
	def __init__(self, ticker):
		QDialog.__init__(self, None)
		self.app = appGlobal.getApp()
		self.deleted = False
		self.ticker = ticker
		self.setWindowTitle("Delete From Allocation")
		
		vert = QVBoxLayout(self)
		label = QLabel("Are you sure you wish to delete %s from your portfolio's allocation?" % ticker);
		label.setWordWrap(True)
		label.setMaximumWidth(300)
		vert.addWidget(label)

		# Buttons
		hbox = QHBoxLayout()
		vert.addLayout(hbox)
		
		hbox.addStretch(1000)

		cancel = QPushButton("Cancel")
		hbox.addWidget(cancel)
		self.connect(cancel, SIGNAL("clicked()"), SLOT("reject()"))
		
		ok = QPushButton("Ok")
		ok.setDefault(True)
		hbox.addWidget(ok)
		self.connect(ok, SIGNAL("clicked()"), self.onOk)
		
		self.exec_()
	
	def onOk(self):
		self.deleted = True
		
		self.app.portfolio.saveAllocation(self.ticker, False)
		self.close()

class AllocationModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		self.app = appGlobal.getApp()
		
		self.ticker = appGlobal.getApp().portfolio.getLastTicker()
		if appGlobal.getApp().portfolio.isBrokerage():
			self.setColumns(["Position", "Target %", "Current %", "Current $", "Difference %", "Difference $", "Shares"])
		else:
			self.setColumns(["Position", "Target %", "Current %", "Current $", "Difference %", "Difference $"])
		self.setRedGreenColumn(4)
		self.setRedGreenColumn(5)
		self.setAllocation()
	
	def setAllocation(self, reset = True):
		allocation = self.app.portfolio.getAllocation()
		positions = self.app.portfolio.getPositions(current = True)

		total = 0.0
		for p in positions:
			if p != "__COMBINED__" and p != "__BENCHMARK__" and positions[p]["value"] > 0.0:
				total += positions[p]["value"]
		self.total = total
				
		allTickers = {}
		for t in positions:
			allTickers[t] = True
		for t in allocation:
			allTickers[t] = True
		if "__COMBINED__" in allTickers:
			del allTickers["__COMBINED__"]
		allTickers = sorted(allTickers)
		self.allTickers = allTickers
		
		sumPercent = 0.0
		row = 1
		data = []
		for ticker in allTickers:
			if ticker == "__COMBINED__" or ticker == "__BENCHMARK__":
				continue
			
			# Default everything to n/a
			current = "n/a"
			currentDollar = "n/a"
			differencePercent = "n/a"
			differenceDollar = "n/a"
			dollarStr = "n/a"
			sign = ""
			currentRow = []

			if ticker in positions:
				if total > 0:
					current = positions[ticker]["value"] / total * 100.0
				else:
					current = 0
				currentDollar = "$" + locale.format("%.2f", positions[ticker]["value"], True)
				
				if not ticker in allocation:
					allocation[ticker] = 0.0
				
				# Try to delete everything with a 0 allocation
				if allocation[ticker] == 0.0:
					self.app.portfolio.saveAllocation(ticker, False)

				sumPercent += allocation[ticker]
				differencePercent = current - allocation[ticker]
				differenceDollar = positions[ticker]["value"] - total * allocation[ticker] / 100.0
				dollarStr = locale.format("%.2f", abs(differenceDollar), True)
				if differenceDollar > 0:
					sign = "+"
				elif differenceDollar < 0:
					sign = "-"
				else:
					sign = ""
			
			currentRow.append(ticker)
			#grid.addWidget(QLabel(ticker), row, 0)
			name = self.app.stockData.getName(ticker)
			#if name:
			#	grid.getCtrl(row, 0).SetToolTipString(name)
			
			if ticker in allocation:
				currentRow.append("%s" % allocation[ticker])
			else:
				currentRow.append("")
			#grid.addWidget(self.editors[ticker], row, 1)
			
			if current != "n/a":
				#grid.addWidget(QLabel("%.2f%%" % current), row, 2)
				currentRow.append("%.2f%%" % current)
			
			if currentDollar != "n/a":
				label = QLabel(currentDollar)
				#grid.addWidget(label, row, 3)
				currentRow.append(currentDollar)

			if differencePercent != "n/a":
				label = QLabel("%+.2f%%" % differencePercent)
				palette = label.palette()
				if differencePercent >= 0:
					palette.setColor(label.foregroundRole(), self.app.positiveColor)
				else:
					palette.setColor(label.foregroundRole(), self.app.negativeColor)
				palette.setColor(label.backgroundRole(), self.app.alternateRowColor)
				label.setPalette(palette)
				#grid.addWidget(label, row, 4)
				currentRow.append("%+.2f%%" % differencePercent)

			if dollarStr != "n/a":				
				label = QLabel("$%s%s" % (sign, dollarStr))
				palette = label.palette()
				if differencePercent >= 0:
					palette.setColor(label.foregroundRole(), self.app.positiveColor)
				else:
					palette.setColor(label.foregroundRole(), self.app.negativeColor)
				label.setPalette(palette)
				#grid.addWidget(label, row, 5)
				currentRow.append("$%s%s" % (sign, dollarStr))
			
			# If this is a brokerage and it has valid history
			if self.app.portfolio.isBrokerage() and "__CASH__" in positions:
				# Get last stock data
				date = self.app.stockData.getLastDate(ticker)
				if date:
					value = self.app.stockData.getPrice(ticker, date)
					if value and differenceDollar != "n/a":
						cash = positions["__CASH__"]["value"]
						if cash > 0 and differenceDollar < -cash:
							differenceDollar = -cash
						shares = differenceDollar / value["close"]
						if shares > 0:
							currentRow.append("Sell %.2f" % shares)
						elif shares < 0:
							# Buy up to cash amount of shares if we can't totally rebalance
							# Or buy rebalancing amount plus remaining balance
							if differenceDollar > -cash:
								currentRow.append("Buy %.2f to %.2f" % (abs(shares), cash / value["close"]))
							else:
								currentRow.append("Buy %.2f" % abs(shares))
						else:
							currentRow.append("")
						currentRow.append(shares)
				else:
					currentRow.append("")

			#if sign == "+":
			#	color = self.app.positiveTextColor
			#elif sign == "-":
			#	color = self.app.negativeTextColor
			#else:
			#	color = False

			row += 1
			data.append(currentRow)

		currentRow = ["Total"]
		currentRow.append("%.2f%%" % sumPercent)
		currentRow.append("100.0%")
		currentRow.append("$" + locale.format("%.2f", total, True))
		currentRow.append("")
		currentRow.append("")
		currentRow.append("")
		data.append(currentRow)

		self.setData(data, reset)
			
	def dataChanged(self, editor, index):
		ticker = self.myData[index.row()][0]
		value = safeFloat(str(editor.text()))
		
		# Delete allocation if empty, else set
		p = self.app.portfolio
		if value == "":
			p.saveAllocation(ticker, "")
		else:
			p.saveAllocation(ticker, ticker, value)
		
		# Update data
		self.setAllocation(False)
		left = self.createIndex(index.row(), 3)
		right = self.createIndex(index.row(), self.columnCount() - 1)
		self.emit(SIGNAL('dataChanged(const QModelIndex &, const QModelIndex &)'), left, right)

class AllocationWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.model = AllocationModel()
		self.app = appGlobal.getApp()
		
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		vbox.setAlignment(Qt.AlignTop)
		
		horiz = QHBoxLayout()
		vbox.addLayout(horiz)
		
		self.add = QPushButton("Add Position")
		horiz.addWidget(self.add)
		self.connect(self.add, SIGNAL("clicked()"), self.addPosition)
		
		self.delete = QPushButton("Delete Position")
		self.delete.setEnabled(False)
		horiz.addWidget(self.delete)
		self.connect(self.delete, SIGNAL("clicked()"), self.deletePosition)
		
		horiz.addStretch(1000)
		
		self.table = EditGrid(self.model)
		# Set edit columns for allocation for all but last row
		for i in range(self.model.rowCount() - 1):
			self.table.setEdit(i, 1)
			editor = self.table.getEdit(i, 1)
			editor.setValidator(QDoubleValidator(0, 1e9, 12, editor))

		self.table.resizeRowsToContents()
		vbox.addWidget(self.table)
		
		self.connect(self.table.selectionModel(), SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.selectedRow)
	
	def addPosition(self):
		add = AddAllocationPanel(self)
		
		if add.added:
			self.model.setAllocation()
			for i in range(self.model.rowCount() - 1):
				self.table.setEdit(i, 1)
			self.table.resizeRowsToContents()
		
	def deletePosition(self):
		row = self.table.selectedRow()
		delete = DeleteAllocationPanel(self.model.myData[row][0])
		
		if delete.deleted:
			self.model.setAllocation()
			for i in range(self.model.rowCount() - 1):
				self.table.setEdit(i, 1)
			self.table.resizeRowsToContents()

	def selectedRow(self, deselected, selected):
		# Update tool action to allow editing/deleting transactions
		if len(self.table.selectionModel().selectedRows()) > 0:
			self.delete.setEnabled(True)
		else:
			self.delete.setEnabled(False)
