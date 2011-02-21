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
from PyQt4.QtWebKit import *

#import webbrowser
import urllib
import re
import feedparser

from editGrid import *
from statusUpdate import *
from plugin import *

class Plugin(PluginBase):
	def name(self):
		return 'News'

	def icarraVersion(self):
		return (0, 2, 0)

	def version(self):
		return (1, 0, 0)

	def initialize(self):
		pass

	def createWidget(self, parent):
		return NewsWidget(parent)
	
	def reRender(self, panel, app):
		pass

	def finalize(self):
		pass

def downloadHtml(url):
	f = urllib.urlopen(url)
	s = f.read()
	f.close()

	# Get rid of script
	while True:
		m = re.search("<script[^>]*>", s)
		if not m:
			break
	
		m2 = re.search("</script[^>]*>", s)
		if not m2:
			break
		
		s = s[:m.span()[0]] + s[m2.span()[1]:]

	# Get rid of noscript
	while True:
		m = re.search("<noscript[^>]*>", s)
		if not m:
			break
	
		m2 = re.search("</noscript[^>]*>", s)
		if not m2:
			break
		
		s = s[:m.span()[0]] + s[m2.span()[1]:]

	# Get rid of everything after .gif? (motley fool)
	#s = re.sub("\.gif\?[^\"]*", ".gif", s)

	return s

class NewsModel(EditGridModel):
	def __init__(self, parent = None, *args): 
		EditGridModel.__init__(self, parent, *args)
		self.ticker = "__COMBINED__"
		
		self.setColumns(["Position", "Date", "Rating", "Title", "Summary"])
	
	def setNews(self):
		if self.ticker == "__COMBINED__":
			ticker = False
		else:
			ticker = self.ticker
		
		news = appGlobal.getApp().stockData.getNews(ticker)
		
		self.map = {}
		row = 0
		data = []
		for n in news:
			self.map[row] = n
			row += 1
			
			newRow = [n["ticker"]]
			name = appGlobal.getApp().stockData.getName(n["ticker"])
			#if name:
			#	grid.getCtrl(row - 1, 0).SetToolTipString(name)

			newRow.append(n["date"])
			if n["rating"]:
				rating = "%+d" % n["rating"]
				ratingColor = "#000000"
			else:
				rating = ""
				ratingColor = "#666666"
			newRow.append(rating)
			newRow.append(n["title"])
			newRow.append(n["summary"])
			#grid.addText(rating, color = ratingColor)
			data.append(newRow)
		
		self.setData(data)

url = "http://www.fool.com/investing/general/2009/08/05/10-stocks-shaking-the-market.aspx?source=eptyholnk303100&logvisit=y&npu=y"
url = "http://biz.yahoo.com/smallcapinvestor/090727/18151.html?.v=1"

class NewsWidget(QWidget):
	def __init__(self, parent):
		QWidget.__init__(self, parent)
		self.model = NewsModel(self)
		
		# Update news for all tickers
		app = appGlobal.getApp()
		self.model.ticker = app.portfolio.getLastTicker()

		layout = QVBoxLayout(self)
		layout.setMargin(0)
		layout.setSpacing(0)
		
		hbox = QHBoxLayout()
		hbox.setMargin(0)
		hbox.setSpacing(10)
		layout.addLayout(hbox)
		
		getNews = QPushButton("Get News")
		hbox.addWidget(getNews)
		self.connect(getNews, SIGNAL("clicked()"), self.onGetNews)

		label = QLabel("Position:")
		hbox.addWidget(label)
		self.tickers = app.portfolio.getTickers()
		if "__CASH__" in self.tickers:
			self.tickers.remove("__CASH__")
		if "__COMBINED__" in self.tickers:
			self.tickers.remove("__COMBINED__")
		self.tickers.insert(0, "All Positions")
		ticker = app.portfolio.getLastTicker()
		
		self.tickerCombo = QComboBox()
		self.tickerCombo.addItems(self.tickers)
		if ticker in self.tickers:
			self.tickerCombo.setCurrentIndex(self.tickers.index(ticker))
		elif ticker == "__COMBINED__":
			self.tickerCombo.setCurrentIndex(0)
		hbox.addWidget(self.tickerCombo)
		self.connect(self.tickerCombo, SIGNAL("currentIndexChanged(int)"), self.newTicker)
		
		hbox.addStretch(1000)

		hbox2 = QHBoxLayout()
		hbox2.setMargin(0)
		hbox2.setSpacing(10)
		layout.addLayout(hbox2)

		self.view = QPushButton("View")
		self.view.setEnabled(False)
		hbox2.addWidget(self.view)
		self.connect(self.view, SIGNAL("clicked()"), self.onView)
		
		self.ratingLabel = QLabel("Rating:")
		choices = ["Critical (+2)", "Important (+1)", "Relevant (+0)", "Not relevant (-1)", "Worthless (-2)"]
		self.ratingCombo = QComboBox()
		self.ratingCombo.addItems(choices)
		self.ratingCombo.setCurrentIndex(2)
		hbox2.addWidget(self.ratingLabel)
		hbox2.addWidget(self.ratingCombo)
		hbox2.addStretch(1000)
		self.ratingLabel.setEnabled(False)
		self.ratingCombo.setEnabled(False)
		self.connect(self.ratingCombo, SIGNAL("currentIndexChanged(int)"), self.newRating)
		
		self.table = EditGrid(self.model)
		self.table.setSortingEnabled(True)
		self.table.horizontalHeader().setResizeMode(0, QHeaderView.ResizeToContents)
		self.table.horizontalHeader().setResizeMode(1, QHeaderView.ResizeToContents)
		self.table.horizontalHeader().setResizeMode(2, QHeaderView.ResizeToContents)
		self.table.horizontalHeader().setResizeMode(3, QHeaderView.Stretch)
		self.table.horizontalHeader().setResizeMode(4, QHeaderView.Stretch)
		self.table.setWordWrap(True)
		self.table.setTextElideMode(Qt.ElideNone)
		layout.addWidget(self.table)

		self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.table.setSelectionMode(QAbstractItemView.SingleSelection)
		self.connect(self.table.selectionModel(), SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.selectedRow)
		
		self.webView = QWebView()
		self.webView.hide()
		self.webView.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
		self.connect(self.webView, SIGNAL("linkClicked (const QUrl&)"), self.adjustLocationUrl)
		self.connect(self.webView, SIGNAL("urlChanged (const QUrl&)"), self.adjustLocationUrl)

		self.locationEdit = QLineEdit()
		self.locationEdit.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, self.locationEdit.sizePolicy().verticalPolicy()))
		self.connect(self.locationEdit, SIGNAL("returnPressed()"), self.changeLocation)

		self.webToolBar = QToolBar()
		self.webToolBar.addAction(self.webView.pageAction(QWebPage.Back))
		self.webToolBar.addAction(self.webView.pageAction(QWebPage.Forward))
		self.webToolBar.addAction(self.webView.pageAction(QWebPage.Reload))
		self.webToolBar.addAction(self.webView.pageAction(QWebPage.Stop))
		self.webToolBar.hide()
		self.webToolBar.addWidget(self.locationEdit)
		
		layout.addWidget(self.webToolBar)
		layout.addWidget(self.webView)
	
		self.model.setNews()
		self.table.resizeRowsToContents()

	def adjustLocationUrl(self, url):
		self.locationEdit.setText(url.toString())
		self.locationEdit.setCursorPosition(0)

 	def changeLocation(self):
		url = QUrl(self.locationEdit.text())
		self.webView.load(url)
		self.webView.setFocus()
 
	def onView(self):
		row = self.table.selectionModel().selectedRows()[0].row()
		
		if self.webView.isHidden():
			url = self.model.map[row]["url"]
			self.locationEdit.setText(url)
			self.locationEdit.setCursorPosition(0)
			self.webView.load(QUrl(url))
			self.table.hide()
			self.webToolBar.show()
			self.webView.show()
			self.view.setText("Hide")
		else:
			self.webView.setContent("")
			self.view.setText("View")
			self.table.show()
			self.webToolBar.hide()
			self.webView.hide()

 	def selectedRow(self, deselected, selected):
		self.view.setEnabled(True)
		self.ratingLabel.setEnabled(True)
		self.ratingCombo.setEnabled(True)
		
		row = self.table.selectionModel().selectedRows()[0].row()
		news = self.model.map[row]
		if news["rating"]:
			if news["rating"] == 2:
				self.ratingCombo.setCurrentIndex(0)
			elif news["rating"] == 1:
				self.ratingCombo.setCurrentIndex(1)
			elif news["rating"] == -1:
				self.ratingCombo.setCurrentIndex(3)
			elif news["rating"] == -2:
				self.ratingCombo.setCurrentIndex(4)
			else:
				self.ratingCombo.setCurrentIndex(2)
		else:
			self.ratingCombo.setCurrentIndex(2)
		
	def newTicker(self, index):
		ticker = self.tickers[index]
		if ticker == "All Positions":
			ticker = "__COMBINED__"
		appGlobal.getApp().portfolio.setLastTicker(ticker)
		self.model.ticker = ticker
		self.model.setNews()
		self.table.resizeRowsToContents()
	
	def newRating(self, index):
		row = self.table.selectionModel().selectedRows()[0].row()
		news = self.model.map[row]
		if index == 0:
			rating = 2
			ratingStr = "+2"
		elif index == 1:
			rating = 1
			ratingStr = "+1"
		elif index == 2:
			rating = 0
			ratingStr = ""
		elif index == 3:
			rating = -1
			ratingStr = "-1"
		elif index == 4:
			rating = -2
			ratingStr = "-2"

		appGlobal.getApp().stockData.setNewsRating(
			news["ticker"],
			news["date"],
			news["url"],
			rating)
		self.model.setNews()

		self.table.selectRow(row)

	def onGetNews(self):
		app = appGlobal.getApp()
		status = StatusUpdate(self, app, closeOnFinish = True)
		status.setStatus("Downloading news")
		
		# Update news for all tickers
		tickers = app.portfolio.getTickers()
		if "__CASH__" in tickers:
			tickers.remove("__CASH__")
		if "__COMBINED__" in tickers:
			tickers.remove("__COMBINED__")
		count = 0
		for ticker in tickers:
			if status.canceled:
				break

			status.setStatus("Downloading news for " + ticker, 100 * count / len(tickers))
			
			d = feedparser.parse("http://finance.yahoo.com/rss/headline?s=" + ticker)
			for e in d.entries:
				d = e.updated_parsed
				date = "%04d-%02d-%02d %02d:%02d:%02d" % (d.tm_year, d.tm_mon, d.tm_mday, d.tm_hour, d.tm_min, d.tm_sec)
	
				# Get link, take from xxx*http if presesnt
				url = e.link
				url = url.replace("%3A", ":")
				h = url.find('*http')
				if h != -1:
					url = url[h + 1:]
	
				app.stockData.addNews(
					ticker,
					date,
					unicode(e.title),
					unicode(e.summary),
					unicode(url))
			count += 1

		self.model.setNews()
		self.table.resizeRowsToContents()
		status.setStatus("Finished downloading news", 100)
