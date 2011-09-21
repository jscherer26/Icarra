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

import glob

from portfolio import *
from chartWidget import *
import appGlobal
import prefs
import chart

def run(argv):
	# Disable preferences when running regression
	prefs.prefs = False
	
	# Whether to save results
	commit = False
	
	# Check which portfolios to test, or all
	toTest = {}
	if len(argv) > 2:
		for i in range(2, len(argv)):
			toTest[argv[i]] = True
	
	# Load all .txt files in regression directory
	for filename in glob.glob('regression/*.txt'):
		portfolioName = filename.lstrip('regression').rstrip('.txt').strip('/').strip('\\')
		
		# Check that we should test this one
		if toTest and not portfolioName in toTest:
			continue
		
		# Check for portfolio in regression directory
		regressionPath = "regression/portfolio_%s.db" % portfolioName
		inRegression = os.path.isfile(regressionPath)
		if inRegression:
			portfolio = Portfolio(portfolioName, customDb = regressionPath)
		else:
			portfolio = Portfolio(portfolioName)
		if not commit:
			portfolio.db.beginTransaction()
		portfolio.rebuildPositionHistory(appGlobal.getApp().stockData)
		
		f = open(filename, "r")
		passedAll = True
		for l in f.readlines():
			l = l.strip("\n").strip(" ")
			if not l or l[0] == "#":
				continue

			chunks = l.split(' ')
			query = {}
			values = {}
			for c in chunks:
				data = c.split('=')
				if len(data) != 2:
					print "invalid regression data:", c
								
				key = data[0]
				value = data[1]

				# Turn date into YYYY-MM-DD HH:MM:SS
				if re.match("\d\d\d\d-\d\d-\d\d", value) and len(value) == 10:
					value = value + " 00:00:00"
					
				values[key] = value

				# Add to query
				if key == "ticker" or key == "date":
					query[key] = value
			
			passed = True
			if "chart" in values:
				# Validate chart
				
				period = chart.portfolioInception
				if "period" in values:
					period = values["period"]
					if period == "oneWeek":
						period = chart.oneWeek
					elif period == "oneMonth":
						period = chart.oneMonth
					elif period == "threeMonths":
						period = chart.threeMonths
					elif period == "oneYear":
						period = chart.oneYear
					elif period == "twoYears":
						period = chart.twoYears
					elif period == "threeYears":
						period = chart.threeYears
					elif period == "fiveYears":
						period = chart.fiveYears
					elif period == "tenYears":
						period = chart.tenYears
					elif period == "portfolioInception":
						period = chart.portfolioInception
					else:
						period = chart.positionInception
				myChart = ChartWidget()
				portfolio.drawChart(myChart, appGlobal.getApp().stockData, values["ticker"], chartType = values["chart"], period = period, doSplit = True, doDividend = True, doFee = True, doBenchmark = True)
				for key in values:
					if key in ["ticker", "date", "chart", "period"]:
						continue
					val = values[key]
					
					# Get chartNum from something of the form y[date][label
					match = re.match("y\[(\d\d\d\d-\d\d-\d\d)\]\[([&%\w\s]*)\]", key)
					if not match:
						print "invalid key", key
						continue
					date = Transaction.parseDate(match.group(1) + " 00:00:00")
					label = match.group(2).replace('%20', ' ')
					
					# Get chart index based on label
					try:
						index = myChart.labels.index(label)
					except:
						print "no index for label", label, l
						continue
					
					# Binary search for date
					lower = 0
					upper = len(myChart.xs[index]) - 1
					mid = -1
					while lower < upper:
						mid = (lower + upper) / 2
						if date < myChart.xs[index][mid]:
							upper = mid
						elif date > myChart.xs[index][mid]:
							lower = mid
						else:
							break
					if mid < 0 or myChart.xs[index][mid] != date:
						continue
				
					if key.startswith("y"):
						chartVal = myChart.ys[index][mid]
					else:
						print "unknown key", key
						continue
					
					# Try comparing as floats
					try:
						val = float(val)
						chartVal = float(chartVal)
						if abs(chartVal - val) < 1.0e-6:
							continue
					except:
						pass
					
					# Did not pass
					if passed:
						passed = False
						passedAll = False
						print "FAIL %s: %s" % (portfolioName, l)
					print "    %s: %s should be %s" % (key, chartVal, val)
			else:
				# Validate positionHistory
				result = portfolio.db.select("positionHistory", where = query)
				row = result.fetchone()
				del result
				if row:
					# See where it is different
					for key in values:
						if key == "ticker" or key == "date":
							continue
						try:
							if abs(float(values[key]) - float(row[key])) >= 1.0e-6:
								if passed:
									passed = False
									passedAll = False
									print "FAIL %s: %s" % (portfolioName, l)
								print "    %s: %f should be %f" % (key, float(row[key]), float(values[key]))
						except:
							if passed:
								passedAll = False
								passed = False
								print "FAIL %s: %s" % (portfolioName, l)
							print "   ", key, values[key], "!=", row[key]
				else:
					passedAll = False
					passed = False
					print "FAIL %s no data: %s" % (portfolioName, l)
		
		# Delete position history if the portfolio is in the regression directory
		if inRegression:
			portfolio.db.query("delete from positionHistory")
		
		if not commit:
			portfolio.db.rollbackTransaction()
		portfolio.close()
		
		if passedAll:
			print "pass:", portfolioName
