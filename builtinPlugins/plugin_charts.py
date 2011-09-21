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

import sys
import math
import datetime

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from prefs import *
from plugin import *
from portfolio import *
from chartWidget import *

class Plugin(PluginBase):
	def name(self):
		return 'Charts'

	def icarraVersion(self):
		return (0, 2, 0)

	def version(self):
		return (1, 0, 0)

	def initialize(self):
		pass

	def createWidget(self, parent):
		return ChartsWidget(parent)
	
	def reRender(self, panel, app):
		panel.update()

	def finalize(self):
		pass

class ChartsWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.app = appGlobal.getApp()
		
		vbox = QVBoxLayout(self)
		vbox.setMargin(0)
		vbox.setAlignment(Qt.AlignTop)
		
		# No portfolio data
		p = self.app.portfolio
		#if not p or not p.getTickers():
		#	return

		# Check for ticker to display
		tickers = p.getTickers()
		if tickers:
			if "__COMBINED__" not in tickers:
				tickers.append("__COMBINED__")
			firstTicker = tickers[0]
			last = p.getLastTicker()
			for t in tickers:
				if t == last:
					firstTicker = t
					break
			if firstTicker != last:
				p.setLastTicker(firstTicker)
		else:
			firstTicker = ""

		horiz = QHBoxLayout()
		vbox.addLayout(horiz)

		horiz2 = QHBoxLayout()
		vbox.addLayout(horiz2)

		self.tickersNormal = tickers
		def getName(ticker):
			name = self.app.stockData.getName(ticker)
			if name:
				return ticker + " - " + name
			else:
				return ticker
		self.tickers = map(getName, self.tickersNormal)

		if "__CASH__" in self.tickers:
			self.tickers.pop(self.tickers.index("__CASH__"))
			self.tickers.insert(0, "Cash")
			self.tickersNormal.pop(self.tickersNormal.index("__CASH__"))
			self.tickersNormal.insert(0, "__CASH__")
		if "__COMBINED__" in self.tickers:
			self.tickers.pop(self.tickers.index("__COMBINED__"))
			self.tickers.insert(0, "Combined")
			self.tickersNormal.pop(self.tickersNormal.index("__COMBINED__"))
			self.tickersNormal.insert(0, "__COMBINED__")

		horiz.addWidget(QLabel("Position:"))

		self.combo = QComboBox()
		self.combo.addItems(self.tickers)
		lastTicker = self.app.portfolio.getLastTicker()
		if lastTicker == False:
			self.combo.setCurrentIndex(0)
		elif lastTicker == "__CASH__":
			self.combo.setCurrentIndex(1)
		elif lastTicker in self.tickersNormal:
			self.combo.setCurrentIndex(self.tickersNormal.index(lastTicker))
		self.combo.setMaximumWidth(120)
		horiz.addWidget(self.combo)
		self.connect(self.combo, SIGNAL("currentIndexChanged(int)"), self.newTicker)
	
		horiz.addWidget(QLabel("Period:"))

		self.periods = ["One Week", "One Month", "Three Months", "One Year", "Two Years", "Three Years", "Five Years", "Ten Years", "Position Inception", "Portfolio Inception"]
		value = p.portPrefs.getPositionPeriod()
		self.period = QComboBox()
		self.period.addItems(self.periods)
		if value in self.periods:
			self.period.setCurrentIndex(self.periods.index(value))
		else:
			self.period.setCurrentIndex(self.periods.index("Portfolio Inception"))
		horiz.addWidget(self.period)

		horiz2.addWidget(QLabel("Type:"))
		self.chartType = QComboBox()
		self.chartTypes = chart.getChartTypes(p)
		self.chartType.addItems(self.chartTypes)
		type = p.portPrefs.getChartType()
		if type in self.chartTypes:
			self.chartType.setCurrentIndex(self.chartTypes.index(type))
		horiz2.addWidget(self.chartType)

		self.splitCheckbox = QCheckBox("Price")
		self.splitCheckbox.setChecked(p.portPrefs.getPositionIncSplits())
		horiz2.addWidget(self.splitCheckbox)

		self.dividendCheckbox = QCheckBox("Dividends")
		self.dividendCheckbox.setChecked(p.portPrefs.getPositionIncDividends())
		horiz2.addWidget(self.dividendCheckbox)

		self.feeCheckbox = QCheckBox("Fees")
		self.feeCheckbox.setChecked(p.portPrefs.getPositionIncFees())
		horiz2.addWidget(self.feeCheckbox)

		self.benchmarkCheckbox = QCheckBox("Benchmark")
		horiz2.addWidget(self.benchmarkCheckbox)

		# Update checkboxes based on chart type
		self.newType(False)

		horiz.addStretch(1000)
		horiz2.addStretch(1000)

		# Connect signals after newType is called (updates checkboxes)
		self.connect(self.period, SIGNAL("currentIndexChanged(int)"), self.newPeriod)
		self.connect(self.chartType, SIGNAL("currentIndexChanged(int)"), self.newType)
		self.connect(self.splitCheckbox, SIGNAL("stateChanged(int)"), self.toggleSplit)
		self.connect(self.dividendCheckbox, SIGNAL("stateChanged(int)"), self.toggleDividend)
		self.connect(self.feeCheckbox, SIGNAL("stateChanged(int)"), self.toggleFee)
		self.connect(self.benchmarkCheckbox, SIGNAL("stateChanged(int)"), self.toggleBenchmark)

		# Create price data
		self.chart = ChartWidget()
		self.chart.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
		vbox.addWidget(self.chart)
		
		self.redrawChart()

	def redrawChart(self):
		p = self.app.portfolio
		
		period = self.periods[self.period.currentIndex()]
		if period == "One Week":
			startDate = chart.oneWeek
		elif period == "One Month":
			startDate = chart.oneMonth
		elif period == "Three Months":
			startDate = chart.threeMonths
		elif period == "One Year":
			startDate = chart.oneYear
		elif period == "Two Years":
			startDate = chart.twoYears
		elif period == "Three Years":
			startDate = chart.threeYears
		elif period == "Five Years":
			startDate = chart.fiveYears
		elif period == "Ten Years":
			startDate = chart.tenYears
		elif period == "Portfolio Inception":
			startDate = chart.portfolioInception
		else:
			startDate = chart.positionInception
		
		# need to unconvert for some reason
		selection = p.getLastTicker().encode("utf-8")

		chartType = self.chartTypes[self.chartType.currentIndex()].lower()
		
		p.drawChart(
			self.chart,
			self.app.stockData,
			p.getLastTicker(),
			startDate,
			doGradient = True,
			chartType = chartType,
			doSplit = self.splitCheckbox.isChecked(),
			doDividend = self.dividendCheckbox.isChecked(),
			doFee = self.feeCheckbox.isChecked(),
			doBenchmark = self.benchmarkCheckbox.isChecked())
		self.chart.legend = True
		self.chart.labelSize = 11
		self.chart.legendSize = 10
		self.chart.pixelsPerTickY = 60
		
		# Force redraw
		self.chart.update()
	
	def toggleSplit(self, event):
		self.app.portfolio.portPrefs.setPositionIncSplits(self.splitCheckbox.isChecked())
		self.redrawChart()

	def toggleDividend(self, event):
		self.app.portfolio.portPrefs.setPositionIncDividends(self.dividendCheckbox.isChecked())
		self.redrawChart()
		
	def toggleFee(self, event):
		self.app.portfolio.portPrefs.setPositionIncFees(self.feeCheckbox.isChecked())
		self.redrawChart()

	def toggleBenchmark(self, event):
		self.app.portfolio.portPrefs.setPositionIncBenchmark(self.benchmarkCheckbox.isChecked())
		self.redrawChart()

	def newTicker(self, event):
		ticker = self.tickers[self.combo.currentIndex()]
		index = ticker.find(" - ")
		if index != -1:
			ticker = ticker[0:index]
		if ticker == "Combined":
			ticker = "__COMBINED__"
		if ticker == "Cash":
			ticker = "__CASH__"
		self.app.portfolio.setLastTicker(ticker)

		self.redrawChart()

	def newType(self, event):
		type = self.chartTypes[self.chartType.currentIndex()]
		self.app.portfolio.portPrefs.setChartType(type)

		if type == "Value" or type == "Transactions":
			self.splitCheckbox.setDisabled(True)
			self.dividendCheckbox.setDisabled(True)
			self.feeCheckbox.setDisabled(True)
		else:
			self.splitCheckbox.setEnabled(True)
			self.dividendCheckbox.setEnabled(True)
			self.feeCheckbox.setEnabled(True)

		if self.app.portfolio.isBenchmark():
			self.benchmarkCheckbox.setEnabled(False)
		elif self.app.portfolio.isBank():
			self.benchmarkCheckbox.setEnabled(False)
			self.splitCheckbox.setEnabled(False)
			self.dividendCheckbox.setEnabled(False)
			self.feeCheckbox.setEnabled(False)
		else:
			self.benchmarkCheckbox.setChecked(self.app.portfolio.portPrefs.getPositionIncBenchmark())

		if not event is False:
			self.redrawChart()

	def newPeriod(self, event):
		period = self.periods[self.period.currentIndex()]
		self.app.portfolio.portPrefs.setPositionPeriod(period)

		self.redrawChart()

