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

from portfolio import *

import appGlobal
import autoUpdater
import datetime
import os

class SplashScreenFrame(QDialog):
	def __init__(self, parent = None, firstTime = False):
		app = appGlobal.getApp()
		self.initTime = datetime.datetime.now()
		QDialog.__init__(self, parent, flags = Qt.WindowStaysOnTopHint | Qt.SplashScreen)
		if firstTime:
			height = 300
		else:
			height = 200
		self.setFixedSize(400, height)
		self.setStyleSheet("background: white")
		self.setModal(True)
		self.running = True
		
		if app.isWindows or app.isLinux:
			frame = QFrame(self)
			frame.setFrameShape(QFrame.Box)
			frame.setLineWidth(1)
			frame.setFixedSize(400, height)
			
			self.sizer = QVBoxLayout(frame)
		else:
			self.sizer = QVBoxLayout(self)
		self.sizer.setMargin(0)

		pm = QPixmap(os.path.join(appGlobal.getPath(), 'icons/icarra.png'))
		self.img = QLabel()
		self.img.setPixmap(pm)
		self.sizer.addWidget(self.img)
		
		self.sizer.addStretch(1)
		label = QLabel("Icarra version %d.%d.%d" % (appGlobal.gMajorVersion, appGlobal.gMinorVersion, appGlobal.gRelease))
		label.setStyleSheet("font-weight: bold")
		self.sizer.addWidget(label, alignment = Qt.AlignCenter)
		self.sizer.addWidget(QLabel("<qt>&copy; 2004-2011 Jesse Liesch</qt>", alignment = Qt.AlignCenter))
		self.sizer.addStretch(1)

		# Add first time stuff
		if firstTime:
			label2 = QLabel("Icarra is downloading stock data and configuring itself for use.  Please allow a minute for this operation to complete.  It will only happen once.")
			label2.setFixedWidth(300)
			label2.setWordWrap(True)
			# Labels are too small for some reason
			label2.setFixedHeight(label2.sizeHint().height() * 1.1)
			self.sizer.addSpacing(10)
			self.sizer.addWidget(label2, alignment = Qt.AlignCenter)
			self.sizer.addSpacing(10)

			label3 = QLabel("Note: You must be connected to the internet.")
			label3.setFixedWidth(300)
			label3.setWordWrap(True)
			label3.setFixedHeight(label3.sizeHint().height() * 1.1)
			self.sizer.addWidget(label3, alignment = Qt.AlignCenter)
			self.sizer.addSpacing(10)

			self.progress = QProgressBar()
			self.progress.setFixedWidth(300)
			self.progress.setValue(10)
			self.sizer.addWidget(self.progress, alignment = Qt.AlignCenter)
			self.sizer.addSpacing(20)

			self.sizer.addStretch(1)

		# Center
		screen = app.desktop().screenGeometry()
		self.move(screen.center() - self.rect().center())

  		self.setCursor(Qt.WaitCursor)
		self.show()
		self.raise_()
		app.processEvents()
		self.activateWindow()

		if firstTime:
			status = 0
			self.lastRet = 0
			self.sleptOnce = False
			while status != 95 and self.running:
				# Process events for 500ms
				app.processEvents(QEventLoop.AllEvents, 500)
				status = self.checkStatus()
				self.lastRet = max(status, self.lastRet)
				status = self.lastRet
				if self.progress.value() != status:
					self.progress.setValue(status)


	def checkStatus(self):
		app = appGlobal.getApp()

		# Return 10 by default
		ret = 10

		if appGlobal.getFailConnected():
			self.running = False
			return ret

		# Sleep twice to make sure everything was updated
		# 94 = slept once
		# 95 = slept twice
		if autoUpdater.sleeping():
			if self.sleptOnce:
				return 95
			else:
				self.sleptOnce = True
				autoUpdater.wakeUp()
				return 94
		
		ret = 10 + 84 * autoUpdater.percentDone() / 100
		return ret


