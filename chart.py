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

import math
import datetime

import appGlobal

oneYearVsBenchmark = 1
oneYearVsBenchmarkCash = 2
threeMonthsVsBenchmark = 3
threeMonthsVsBenchmarkCash = 4
inceptionVsBenchmark = 5
inceptionVsBenchmarkCash = 6
oneMonthMovers = 7
threeMonthMovers = 8
oneYearMovers = 9
oneMonthSpending = 10
threeMonthSpending = 11
oneYearSpending = 12
inceptionSpending = 13

oneWeek = 1
oneMonth = 2
threeMonths = 3
oneYear = 4
twoYears = 5
threeYears = 6
fiveYears = 7
tenYears = 8
positionInception = 9
portfolioInception = 10

# Base class for charting
def getSummaryChartTypes(portfolio):
	if portfolio.isBank():
		# Note: vs benchmark is automatically removed when charting
		return {threeMonthsVsBenchmarkCash: "Three Months ($)",
			oneYearVsBenchmarkCash: "One Year ($)",
			inceptionVsBenchmarkCash: "Since Inception ($)",
			oneMonthSpending: "One month spending",
			threeMonthSpending: "Three months spending",
			oneYearSpending: "One year spending",
			inceptionSpending: "Spending since inception"}
	else:
		return {threeMonthsVsBenchmarkCash: "Three Months vs. Benchmark ($)",
			threeMonthsVsBenchmark: "Three Months vs. Benchmark (%)",
			oneYearVsBenchmarkCash: "One Year vs. Benchmark ($)",
			oneYearVsBenchmark: "One Year vs. Benchmark (%)",
			inceptionVsBenchmarkCash: "Since Inception vs. Benchmark ($)",
			inceptionVsBenchmark: "Since Inception vs. Benchmark (%)",
			oneMonthMovers: "One Month Movers",
			threeMonthMovers: "Three Month Movers",
			oneYearMovers: "One Year Movers"}

def getChartTypes(portfolio):
	if portfolio.isBank():
		return ["Value", "Spending", "Monthly Spending"]
	else:
		return ["Value", "Profit", "Performance", "Transactions"]

class Chart():
	def __init__(self, parent = None):
		self.reset()
	
	def reset(self):
		self.xs = []
		self.ys = []
		self.buyXs = []
		self.buyYs = []
		self.sellXs = []
		self.sellYs = []
		self.splitXs = []
		self.splitYs = []
		self.dividendXs = []
		self.dividendYs = []
		self.dividendValues = []
		self.shortXs = []
		self.shortYs = []
		self.coverXs = []
		self.coverYs = []
		self.labels = []
		self.colors = []
		self.dashed = []

		# Display parameters
		self.margin = 20
		self.titleMargin = 10
		self.lineWidth = 2.5
		self.labelSize = 8
		self.legendSize = 9
		self.transactionSize = 16
		self.title = False
		self.titleSize = 18
		self.pixelsPerTickX = 80
		self.pixelsPerTickY = 80
		self.tickSize = 5
		self.pixelsPerPoint = 1
		self.legend = False
		self.zeroYAxis = False
		self.xAxisType = "date"
		self.yAxisType = "dollars"
		self.doGradient = False

	def addXY(self, x, y, label = False, color = (0.0, 0.8, 0.0), dashed = False):
		self.xs.append(x)
		self.ys.append(y)
		self.labels.append(label)
		self.colors.append(color)
		self.dashed.append(dashed)
	
	def addBuys(self, buyX, buyY):
		self.buyXs = buyX
		self.buyYs = buyY

	def addSells(self, sellX, sellY):
		self.sellXs = sellX
		self.sellYs = sellY

	def addSplits(self, splitX, splitY):
		self.splitXs = splitX
		self.splitYs = splitY

	def addDividends(self, dividendX, dividendY, dividendValues):
		self.dividendXs = dividendX
		self.dividendYs = dividendY
		self.dividendValues = dividendValues

	def addShorts(self, shortX, shortY):
		self.shortXs = shortX
		self.shortYs = shortY

	def addCovers(self, coverX, coverY):
		self.coverXs = coverX
		self.coverYs = coverY


