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
import webbrowser

import appGlobal

class NewVersion(QDialog):
	def __init__(self, newMajor, newMinor, newRelease):
		QDialog.__init__(self)
		self.setWindowTitle("Icarra version %d.%d.%d" % (appGlobal.gMajorVersion, appGlobal.gMinorVersion, appGlobal.gRelease))
		self.newMajor = newMajor
		self.newMinor = newMinor
		self.newRelease = newRelease
		
		vbox = QVBoxLayout(self)
		
		vbox.addWidget(QLabel("Icarra version %d.%d.%d is now available." % (newMajor, newMinor, newRelease)))
		vbox.addWidget(QLabel("Would you like to download it?"))
		vbox.addSpacing(15)

		hor = QHBoxLayout()
		hor.addStretch(1000)
		vbox.addLayout(hor)
		
		skip = QPushButton("Skip this version")
		hor.addWidget(skip)
		self.connect(skip, SIGNAL("clicked()"), self.onSkip)

		remind = QPushButton("Remind me later")
		hor.addWidget(remind)
		self.connect(remind, SIGNAL("clicked()"), self.onRemind)

		download = QPushButton("Download")
		download.setDefault(True)
		hor.addWidget(download)
		self.connect(download, SIGNAL("clicked()"), self.onDownload)

		self.exec_()
	
	def onSkip(self):
		appGlobal.getApp().prefs.setIgnoreVersion(self.newMajor, self.newMinor, self.newRelease)
		self.close()
	
	def onRemind(self):
		appGlobal.getApp().prefs.setLastVersionReminder()
		self.close()
	
	def onDownload(self):
		appGlobal.getApp().prefs.setLastVersionReminder()
		webbrowser.open("http://www.icarra2.com/downloads")
		self.close()