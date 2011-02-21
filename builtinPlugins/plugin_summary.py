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

import datetime

from portfolio import *
from editGrid import *
from plugin import *
from chartWidget import *

class Plugin(PluginBase):
	def name(self):
		return "Summary"

	def icarraVersion(self):
		return (0, 2, 0)

	def version(self):
		return (1, 0, 0)

	def initialize(self):
		pass

	def createWidget(self, parent):
		return PortfolioSummaryWidget(parent)
	
	def reRender(self, panel, app):
		panel.update()

	def finalize(self):
		pass

class PortfolioSummaryModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		self.app = appGlobal.getApp()
	
	def setSummary(self):
		# Create financial statement
		p = self.app.portfolio
		f = p.getPositionFirstLast("__COMBINED__")
		if not f:
			return
		(firstDate, lastDate) = f
		firstOfYear = datetime.datetime(lastDate.year, 1, 1)
		
		# Check if first of year is valid
		# If not use first portfolio date
		pos = p.getPositionOnDate("__COMBINED__", firstOfYear)
		if not pos:
			firstOfYear = firstDate

		inflow = p.sumInflow(firstOfYear, lastDate)
		divs = p.sumDistributions(firstOfYear, lastDate)
		fees = p.sumFees(firstOfYear, lastDate)
		pos = p.getPositionOnDate("__COMBINED__", firstOfYear)
		posYtd = p.getPositionOnDate("__COMBINED__", lastDate)
		
		valueYtd = "$" + locale.format("%.2f", posYtd["value"], True)
		inflowYtd = "$" + locale.format("%.2f", inflow, True)
		returnYtd = locale.format("%.2f", (posYtd["normDividend"] / pos["normDividend"] - 1.0) * 100.0) + "%"
		divsYtd = "$" + locale.format("%.2f", divs, True)
		feesYtd = "$" + locale.format("%.2f", fees, True)
		if fees > 0:
			feesYtd = "-" + feesYtd
		
		rows = []
		def addItem(row, col, text, isNumeric = False, isNegative = False, color = False):
			if col == 0:
				rows.append([])
			rows[row].append(text)

		cols = ["", str(lastDate.year) + " YTD"]

		addItem(0, 0, "Value")
		addItem(0, 1, valueYtd)

		addItem(1, 0, "Inflow")
		addItem(1, 1, inflowYtd)

		addItem(2, 0, "Dividends")
		addItem(2, 1, divsYtd, isNumeric = True)

		addItem(3, 0, "Fees")
		addItem(3, 1, feesYtd, isNumeric = True, isNegative = True)

		addItem(4, 0, "Returns")
		addItem(4, 1, returnYtd, isNumeric = True)
		
		self.setRedGreenRow(2)
		self.setRedGreenRow(3)
		self.setRedGreenRow(4)

		year = lastDate.year - 1
		col = 2
		while 1:
			if p.getSummaryYears() == "thisYear":
				break

			firstOfLastYear = datetime.datetime(year, 1, 1)
			lastYearEndDate = datetime.datetime(year, 12, 31)

			lastPosEnd = p.getPositionOnDate("__COMBINED__", lastYearEndDate)
			
			# No data at end of year
			if not lastPosEnd:
				break

			lastInflowYear = p.sumInflow(firstOfLastYear, lastYearEndDate)
			lastDivsYear = p.sumDistributions(firstOfLastYear, lastYearEndDate)
			lastFeesYear = p.sumFees(firstOfLastYear, lastYearEndDate)
			lastPos = p.getPositionOnDate("__COMBINED__", firstOfLastYear)
					
			lastInflowEnd = "$" + locale.format("%.2f", lastInflowYear, True)
			lastValueEnd = "$" + locale.format("%.2f", lastPosEnd["value"], True)
			if lastPos:
				lastReturnEnd = locale.format("%.2f", (lastPosEnd["normDividend"] / lastPos["normDividend"] - 1.0) * 100.0) + "%"
			else:
				lastReturnEnd = "n/a"
			lastDivsEnd = "$" + locale.format("%.2f", lastDivsYear, True)
			lastFeesEnd = "$" + locale.format("%.2f", lastFeesYear, True)
			if lastFeesYear > 0:
				lastFeesEnd = "-" + lastFeesEnd
			
			cols.append(str(year))
	
			addItem(0, col, lastValueEnd)
			addItem(1, col, lastInflowEnd)
			addItem(2, col, lastDivsEnd, isNumeric = True)
			addItem(3, col, lastFeesEnd, isNumeric = True, isNegative = True)
			addItem(4, col, lastReturnEnd, isNumeric = True)
	
			year -= 1
			col += 1
			
			if p.getSummaryYears() != "allYears":
				break

		self.setColumns(cols)
		self.setData(rows)

class PortfolioSummaryWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.app = appGlobal.getApp()
		
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		vbox.setAlignment(Qt.AlignTop)
		
		self.chartLayout = QHBoxLayout()
		vbox.addLayout(self.chartLayout)
		
		year = datetime.datetime.now() - datetime.timedelta(days = 365)
		month = datetime.datetime.now() - datetime.timedelta(days = 31)
		month = datetime.datetime(month.year, month.month, month.day)

		if self.app.portfolio.isBenchmark():
			benchmark = False
		else:
			benchmark = True

		self.chart1 = ChartWidget()
		self.app.portfolio.chartByType(self.chart1, self.app.portfolio.getSummaryChart1())
		self.chart1.pixelsPerTickY = 30
		self.chart1.pixelsPerTickX = 60
		self.chart1.margin = 10
		self.chart1.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum))
		self.chartLayout.addWidget(self.chart1)
		
		self.chart2 = ChartWidget()
		self.app.portfolio.chartByType(self.chart2, self.app.portfolio.getSummaryChart2())
		self.chart2.pixelsPerTickY = 30
		self.chart2.pixelsPerTickX = 60
		self.chart2.margin = 10
		self.chart2.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum))
		self.chartLayout.addWidget(self.chart2)

		self.model = PortfolioSummaryModel(self)
		self.table = EditGrid(self.model, sorting = False)
		self.table.setRowHeader(True)
		self.table.horizontalHeader().setResizeMode(QHeaderView.Fixed)
		self.table.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
		vbox.addWidget(self.table)
	
	def resizeEvent(self, event):
		w = self.size().width()
		
		self.chart1.setMinimumHeight(w / 3)
		self.chart2.setMinimumHeight(w / 3)

		self.model.setSummary()
		self.table.resizeToMinimum()
		
		# Hack for older versions, forces to resize properly
		if PYQT_VERSION < 0x040700:
			self.hide()
			self.show()

		QWidget.resizeEvent(self, event)

	def resize(self, event):
		self.update()

