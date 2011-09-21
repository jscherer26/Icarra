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

from statusUpdate import *

class WebBrowser(QWidget):
	def __init__(self, parent = False, downloadImport = False):
		QWidget.__init__(self, parent)

		layout = QVBoxLayout(self)
		layout.setMargin(0)
		layout.setSpacing(0)
		
		self.webView = QWebView(parent)
		self.webView.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
		self.connect(self.webView, SIGNAL("linkClicked (const QUrl&)"), self.linkClicked)
		self.connect(self.webView, SIGNAL("urlChanged (const QUrl&)"), self.urlChanged)
		
		if downloadImport:
			self.webView.page().setForwardUnsupportedContent(True)
			self.connect(self.webView.page(), SIGNAL("downloadRequested(const QNetworkRequest&)"), self.downloadRequested)
			self.connect(self.webView.page(), SIGNAL("unsupportedContent(QNetworkReply*)"), self.unsupportedContent)

		self.locationEdit = QLineEdit()
		self.locationEdit.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, self.locationEdit.sizePolicy().verticalPolicy()))
		self.connect(self.locationEdit, SIGNAL("returnPressed()"), self.changeLocation)

		self.webToolBar = QToolBar()
		self.webToolBar.addAction(self.webView.pageAction(QWebPage.Back))
		self.webToolBar.addAction(self.webView.pageAction(QWebPage.Forward))
		self.webToolBar.addAction(self.webView.pageAction(QWebPage.Reload))
		self.webToolBar.addAction(self.webView.pageAction(QWebPage.Stop))
		self.webToolBar.addWidget(self.locationEdit)
		
		layout.addWidget(self.webToolBar)
		layout.addWidget(self.webView)
	
	def loadUrl(self, url):
		self.locationEdit.setText(url)
		self.locationEdit.setCursorPosition(0)
		self.webView.load(QUrl(url))
	
	def setContent(self, text):
		self.webView.setContent(text)

	def downloadRequested(self, request):
		print request

	def unsupportedContent(self, reply):
		self.downloadedFile = reply
		self.connect(reply, SIGNAL("finished()"), self.contentFinished)
	
	def contentFinished(self):
		status = StatusUpdate(self, numTextLines = 3)
		status.setStatus("Reading file", 10)
		
		data = str(QString(self.downloadedFile.readAll()))

		# Try importing transactions
		appGlobal.getApp().portfolio.updateFromFile(data, appGlobal.getApp(), status)

	def urlChanged(self, url):
		self.locationEdit.setText(url.toString())
		self.locationEdit.setCursorPosition(0)

	def linkClicked(self, url):
		self.locationEdit.setText(url.toString())
		self.locationEdit.setCursorPosition(0)
		self.webView.load(url)
		self.webView.setFocus()

 	def changeLocation(self):
 		urlText = str(self.locationEdit.text())
 		if urlText.find("http://") == -1 and urlText.find("https://") == -1:
 			urlText = "http://" + urlText
 			self.locationEdit.setText(urlText)
		url = QUrl(urlText)
		self.webView.load(url)
		self.webView.setFocus()