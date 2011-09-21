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

import threading

import prefs
import appGlobal

class OfxDebugFrame(QWidget):
	def __init__(self):
		QWidget.__init__(self)
		self.setWindowTitle("OFX Debug")
		self.app = appGlobal.getApp()
		
		vbox = QVBoxLayout(self)
		
		label = QLabel("OFX data will be logged in this window when importing transactions from your financial institution.  Account numbers and passwords will be removed.")
		label.setWordWrap(True)
		vbox.addWidget(label)
		
		self.text = QTextEdit()
		self.text.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
		self.text.setReadOnly(True)
		vbox.addWidget(self.text)
		
		self.show()
	
	def sizeHint(self):
		return QSize(600, 500)
	
	def add(self, ofx, input):
		if input:
			str = "INPUT\n----------\n" + ofx + "\n\n"
		else:
			str =  "OUTPUT\n----------\n" + ofx + "\n\n"
		
		# Print to stdout and to window (if main thread)
		print str
		if threading.currentThread().name == "MainThread":
			if self.text.toPlainText():
				self.text.append("\n" + str)
			else:
				self.text.setText(str)

			self.raise_()
