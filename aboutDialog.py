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

import appGlobal
import os

class AboutDialog(QDialog):
	def __init__(self, parent = None, firstTime = False):
		app = appGlobal.getApp()
		QDialog.__init__(self, parent, flags = Qt.WindowStaysOnTopHint)
		self.setFixedSize(400, 260)
		#self.setFixedWidth(400)
		self.setStyleSheet("background: white")
		
		if app.isWindows or app.isLinux:
			frame = QFrame(self)
			frame.setFrameShape(QFrame.Box)
			frame.setLineWidth(1)
			#frame.setFixedSize(400, height)
			frame.setFixedSize(400, 260)
			
			self.sizer = QVBoxLayout(frame)
		else:
			self.sizer = QVBoxLayout(self)
		self.sizer.setMargin(0)
		self.sizer.setSpacing(5)

		pm = QPixmap(os.path.join(appGlobal.getPath(), 'icons/icarra.png'))
		self.img = QLabel()
		self.img.setPixmap(pm)
		self.sizer.addWidget(self.img)
		
		self.sizer.addSpacing(20)
		label = QLabel("Icarra version %d.%d.%d" % (appGlobal.gMajorVersion, appGlobal.gMinorVersion, appGlobal.gRelease))
		label.setStyleSheet("font-weight: bold")
		self.sizer.addWidget(label, alignment = Qt.AlignCenter)
		self.sizer.addWidget(QLabel("<qt>&copy; 2004-2011 Jesse Liesch</qt>", alignment = Qt.AlignCenter))
		self.sizer.addSpacing(20)

		label = QLabel("Developers")
		label.setStyleSheet("font-weight: bold")
		self.sizer.addWidget(label, alignment = Qt.AlignCenter)
		for name in ["Jesse Liesch", "James G Scherer"]:
			self.sizer.addWidget(QLabel(name, alignment = Qt.AlignCenter))
		self.sizer.addSpacing(30)

		# Center
		screen = app.desktop().screenGeometry()
		self.move(screen.center() - self.rect().center())
		
		self.exec_()
