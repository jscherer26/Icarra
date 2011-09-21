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

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import appGlobal
import chart

class ChartWidget(QWidget, chart.Chart):
	def __init__(self, parent = None):
		QWidget.__init__(self, parent)
		chart.Chart.__init__(self)
		self.setMinimumSize(300, 200)
	
	@staticmethod
	def totalSeconds(td):
		return td.toordinal() + td.microsecond / 1e6

	def formatYLabel(self, y):
		if self.yAxisType == "dollars":
			if y > 1e12:
				return "$%.1fT" % round(y / 1e12, 1)
			elif y > 1e9:
				return "$%.1fB" % round(y / 1e9, 1)
			elif y > 1e6:
				return "$%.1fM" % round(y / 1e6, 1)
			elif y > 1e3:
				return "$%.1fK" % round(y / 1e3, 1)
			else:
				return "$%.2f" % round(y, 2)
		elif self.yAxisType == "percent":
			return "%.1f%%" % round(100 * y, 1)

	def formatXLabel(self, x):
		if self.xAxisType == "date":
			d = datetime.datetime.fromordinal(int(round(x)))
			if d.year != self.lastYear:
				self.lastYear = d.year
				return d.strftime("%b %y")
			else:
				return d.strftime("%b")

	def stringWidth(self, string, size):
		if size >= 18:
			font = "times new roman"
		else:
			font = "helvetica"

		app = appGlobal.getApp()
		if app.isOSX:
			newFont = QFont(font, size * 1.4)
		else:
			newFont = QFont(font, size)
			if size >= 18:
				newFont.setBold(True)

		metrics = QFontMetrics(newFont)
		return metrics.width(string)

	def maxStringWidth(self, strings, size):
		m = 0
		for s in strings:
			w = self.stringWidth(s, size)
			if w > m:
				m = w
		return m

	def drawString(self, string, x, y, size, align = "left", width = False, bold = False, outline = False):
		if size >= 18:
			font = "times new roman"
		else:
			font = "helvetica"
		
		# Increase size by 20% to account for underhangs
		if align.find("center") > -1:
			x -= self.stringWidth(string, size) / 2
		elif align.find("right") > -1:
			x -= self.stringWidth(string, size) 

		if align.find("middle") > -1:
			y += size / 2
		elif align.find("top") > -1:
			y += size

		# Build font
		if appGlobal.getApp().isOSX:
			newFont = QFont(font, size * 1.4)
		else:
			newFont = QFont(font, size)
			if size >= 18:
				newFont.setBold(True)
		if bold:
			newFont.setBold(True)
		self.painter.setFont(newFont)

		if outline:
			path = QPainterPath()
			path.addText(x, y, newFont, string)
			#painter.setPen(pen)
			#painter.setBrush(brush)
			self.painter.drawPath(path)
		else:
			self.painter.drawText(x, y, string)
	
	def paintEvent(self, event):
		if (len(self.xs) == 0 or len(self.xs[0]) == 0) and len(self.dividendXs) == 0:
			return
		
		painter = QPainter(self)
		self.painter = painter

		self.lastYear = -1
		xyArray = []
		
		# Get min/max x, y
		# If no xs or ys then assume we have dividends
		if len(self.xs) and len(self.xs[0]) > 0:
			minX = self.xs[0][0]
			maxX = self.xs[0][0]
			minY = self.ys[0][0]
			maxY = self.ys[0][0]
			numXs = 0
			for x in self.xs:
				minX = min(minX, min(x))
				maxX = max(maxX, max(x))
				numXs = max(numXs, len(x))
			for y in self.ys:
				minY = min(minY, min(y))
				maxY = max(maxY, max(y))
		else:
			minX = self.dividendXs[0]
			maxX = self.dividendXs[0]
			minY = self.dividendYs[0]
			maxY = self.dividendYs[0]
			numXs = len(self.dividendXs)
		if self.dividendXs:
			numXs = max(numXs, len(self.dividendXs))
			minX = min(minX, min(self.dividendXs))
			maxX = max(maxX, max(self.dividendXs))
			minY = min(minY, min(self.dividendYs))
			maxY = max(maxY, max(self.dividendYs))
		
		if self.zeroYAxis and minY > 0:
			minY = 0
		
		# Add extra if only one Y value
		if minY == maxY:
			if minY == 0:
				maxY = 1
			else:
				if minY > 0:
					minY *= 0.9
				else:
					minY *= 1.1
				if maxY > 0:
					maxY *= 1.1
				else:
					maxY *= 0.9
		
		# Add extra if only one X value
		oneDataPoint = minX == maxX
		if oneDataPoint:
			minX -= datetime.timedelta(1)
			maxX += datetime.timedelta(1)
		
		minX = self.totalSeconds(minX)
		maxX = self.totalSeconds(maxX)
		spanX = maxX - minX
		spanY = maxY - minY

		# Trim prices
		interval = self.pixelsPerPoint * numXs / float(self.chartSpanX)
		if interval < 1.0:
				interval = 1.0

		prices = {}
		xs = []
		ys = []
		
		# Trim data, averaging buckets
		if interval > 1:
			for i in range(len(self.xs)):
				nextX = 0
				nextXFloat = 0.0
				xs.append([])
				ys.append([])
				bucket = []
				for j in range(len(self.xs[i])):
					# If break in data, reset bucket
					if self.ys[i][j] is False:
						bucket = []
					else:
						bucket.append(self.ys[i][j])

					if j == nextX:
						xs[i].append(self.xs[i][j])
						if bucket:
							ys[i].append(sum(bucket) / len(bucket))
							bucket = []
						else:
							# Break in data
							ys[i].append(False)
						nextXFloat += interval
						nextX = int(nextXFloat)
				
				# Add in last point
				xs[i].append(self.xs[i][-1])
				ys[i].append(self.ys[i][-1])
		else:
			xs = self.xs
			ys = self.ys

		axesX = self.chartMinX
		chartWidth = self.chartSpanX
		axesY = self.h - self.chartMinY
		chartHeight = self.chartSpanY

		if chartWidth <= 0 or chartHeight <= 0:
			return
			
		# Draw legend
		if self.legend:
			chartHeight -= self.legendSize + 5

		# Determine height of x labels
		axesY -= self.labelSize + 10
		chartHeight -= self.labelSize + 10
		if self.title:
			chartHeight -= self.titleSize + self.titleMargin
		
		# Determine Y tick marks
		numTicks = round(chartHeight / self.pixelsPerTickY)
		if numTicks < 2:
			numTicks = 2
		tickJump = chartHeight / numTicks # in pixels
		tickJumpData = spanY / numTicks # in Data

		yTicks = []
		yLabels = []
		if self.yAxisType == "percent" and spanY > 0:
			# For percentage start at 0%, then go up
			tick = -minY / spanY * chartHeight
			while tick <= chartHeight + 1e-6:
				yTicks.append(axesY - tick)
				yLabels.append(self.formatYLabel(minY + (tick / chartHeight) * spanY))
				tick += tickJump
			
			# Now go down
			tick = -minY / spanY * chartHeight - tickJump
			while tick >= -1e-6:
				yTicks.append(axesY - tick)
				yLabels.append(self.formatYLabel(minY + (tick / chartHeight) * spanY))
				tick -= tickJump
		else:
			tick = 0
			while tick <= chartHeight + 1e-6:
				yTicks.append(axesY - tick)
				yLabels.append(self.formatYLabel(minY + (tick / chartHeight) * spanY))
				tick += tickJump

		# Determine width of y labels
		yLabelWidth = math.ceil(self.maxStringWidth(yLabels, self.labelSize))
		axesX += yLabelWidth + 10
		chartWidth -= yLabelWidth + 10
		
		# Determine RHS Y values and their width
		rhsValues = []
		rhsLabels = []
		rhsLabelWidth = 0
		for y in ys:
			if len(y) > 0:
				value = y[-1]
				label = self.formatYLabel(value)
				rhsValues.append(value)
				rhsLabels.append(label)
				width = self.stringWidth(label, self.labelSize + 1)
				rhsLabelWidth = max(rhsLabelWidth, width)
		maxLabel = self.formatYLabel(maxY)
		rhsLabelWidth = max(rhsLabelWidth, self.stringWidth(maxLabel, self.labelSize + 1))
		chartWidth -= rhsLabelWidth + 5

		# Determine X tick marks
		numTicks = round(chartWidth / self.pixelsPerTickX)
		if numTicks > numXs:
			numTicks = numXs
		tickJump = chartWidth / numTicks
		tick = 0
		xTicks = []
		xLabels = []
		while tick <= chartWidth + 1e-6:
			xTicks.append(axesX + tick)
			xLabels.append(self.formatXLabel(minX + (tick / chartWidth) * spanX))
			tick += tickJump
		
		# Draw bounding rect
		painter.setPen(QPen(Qt.gray))
		painter.setBrush(QBrush(Qt.white))
		painter.drawRect(0, 0, self.w - 1, self.h - 1)
		
		# Draw X tick marks
		painter.setPen(QPen(QColor(178, 178, 178), 1, Qt.DotLine))
		for x in xTicks:
			painter.drawLine(QLineF(x, axesY, x, axesY - chartHeight))
		painter.setPen(QPen(QColor(127, 127, 127)))
		for x in xTicks:
			painter.drawLine(QLineF(x, axesY, x, axesY + self.tickSize))

		# Draw Y tick marks
		painter.setPen(QPen(QColor(178, 178, 178), 1, Qt.DotLine))
		for y in yTicks:
			painter.drawLine(QLineF(axesX, y, axesX + chartWidth, y))
		painter.setPen(QPen(QColor(127, 127, 127)))
		for y in yTicks:
			painter.drawLine(QLineF(axesX, y, axesX - self.tickSize, y))

		# Draw axes
		painter.drawLine(QLineF(axesX, axesY - chartHeight, axesX, axesY))
		painter.drawLine(QLineF(axesX, axesY, axesX + chartWidth, axesY))
		
		# Draw y labels
		painter.setPen(QPen(QColor(51, 51, 51)))
		for i in range(len(yTicks)):
			tick = yTicks[i]
			label = yLabels[i]
			self.drawString(label, axesX - self.tickSize - 5, tick, self.labelSize, align = "right middle")

		# Draw RHS y labels in reverse
		for i in range(len(rhsLabels) - 1, -1, -1):
			label = rhsLabels[i]
			if spanY > 0:
				y = axesY - (rhsValues[i] - minY) / spanY * chartHeight
			else:
				y = 0
			if self.dashed[i]:
				# Lighten color if dashed
				pen = QPen(QColor(255 * self.colors[i][0], 255 * self.colors[i][1], 255 * self.colors[i][2], 100))
			else:
				pen = QPen(QColor(200 * self.colors[i][0], 200 * self.colors[i][1], 200 * self.colors[i][2]))
			painter.setPen(pen)
			
			# Draw slightly larger because it is colored and otherwise appears smaller
			self.drawString(label, axesX + chartWidth + 5, y, self.labelSize + 1, "middle")

		# Draw x labels
		painter.setPen(QPen(QColor(51, 51, 51)))
		for i in range(len(xTicks)):
			tick = xTicks[i]
			label = xLabels[i]
			self.drawString(label, tick, axesY + 10, self.labelSize, align = "center top")

		# Draw legend
		if self.legend:
			x = axesX + 10
			y = axesY - chartHeight
			if self.title:
				y -= self.titleMargin
			else:
				y -= self.margin / 2
			
			drewLabels = {}
			for i in range(len(self.xs)):
				# Only draw same label twice
				if self.labels[i] in drewLabels:
					continue

				painter.setPen(QPen(QColor(200 * self.colors[i][0], 200 * self.colors[i][1], 200 * self.colors[i][2])))
				painter.setBrush(QBrush(QColor(255 * self.colors[i][0], 255 * self.colors[i][1], 255 * self.colors[i][2])))

				self.drawString(self.labels[i], x + 12, y, self.legendSize)
				w = self.stringWidth(self.labels[i], self.legendSize)

				painter.setPen(QPen(QColor(255 * self.colors[i][0], 255 * self.colors[i][1], 255 * self.colors[i][2])))

				painter.drawRect(x, y - self.legendSize * (0.5 + 0.125), 9, self.legendSize * 0.25)

				drewLabels[self.labels[i]] = True
				x += w + 22
			
		# Draw title
		if self.title:
			painter.setPen(QPen(QColor(51, 51, 51)))
			self.drawString(self.title, axesX + chartWidth / 2, self.margin / 2, self.titleSize, "center top")
		
		painter.setRenderHint(QPainter.Antialiasing)

		# If gradient, draw it first
		if self.doGradient and not oneDataPoint:
			path = QPainterPath()
			gradientPath = QPainterPath()
			moveTo = True
			for j in range(len(xs[0])):
				# Check for break in data, resart lines
				if ys[0][j] is False:
					moveTo = True
					continue

				if spanX > 0:
					x = axesX + (self.totalSeconds(xs[0][j]) - minX) / spanX * (chartWidth + 0)
				else:
					x = axesX
				if spanY > 0:
					y = axesY - (ys[0][j] - minY) / spanY * chartHeight
				else:
					y = axesY

				if moveTo:
					path.moveTo(x, y)
					moveTo = False
				else:
					path.lineTo(x, y)
			
			gradientPath.addPath(path)
			if spanX > 0:
				firstX = axesX + (self.totalSeconds(xs[0][0]) - minX) / spanX * (chartWidth + 0)
			else:
				firstX = axesX
			gradientPath.lineTo(x + 1, y)
			gradientPath.lineTo(x + 1, axesY)
			gradientPath.lineTo(firstX, axesY)
			gradientPath.closeSubpath()

			myGradient = QLinearGradient(QPointF(0, axesY), QPointF(0, axesY - chartHeight))
			myGradient.setColorAt(1, QColor(255 * (2 + 1 * self.colors[0][0]) / 3, 255 * (2 + 1 * self.colors[0][1]) / 3, 255 * (2 + 1 * self.colors[0][2]) / 3, 200))
			myGradient.setColorAt(0, QColor(255 * (1 + 2 * self.colors[0][0]) / 3, 255 * (1 + 2 * self.colors[0][1]) / 3, 255 * (1 + 2 * self.colors[0][2]) / 3, 200))
			gradientPath.setFillRule(Qt.WindingFill)

			painter.setBrush(myGradient)
			painter.setPen(QColor(0, 0, 0, 0))
			painter.drawPath(gradientPath)

			if self.dashed[0]:
				# Lighten color if dashed
				pen = QPen(QColor(255 * self.colors[0][0], 255 * self.colors[0][1], 255 * self.colors[0][2], 100))
			else:
				pen = QPen(QColor(255 * self.colors[0][0], 255 * self.colors[0][1], 255 * self.colors[0][2]))
			pen.setWidth(self.lineWidth)
			painter.setPen(pen)
			painter.setBrush(QBrush())
			painter.drawPath(path)
			
		# Draw lines in reverse
		for i in range(len(xs) - 1, -1, -1):
			# Gradient was drawn first
			if i == 0 and self.doGradient:
				continue
			
			if self.dashed[i]:
				# Lighten color if dashed
				pen = QPen(QColor(255 * self.colors[i][0], 255 * self.colors[i][1], 255 * self.colors[i][2], 100))
			else:
				pen = QPen(QColor(255 * self.colors[i][0], 255 * self.colors[i][1], 255 * self.colors[i][2]))
			pen.setWidth(self.lineWidth)
			painter.setPen(pen)
			painter.setBrush(QBrush())

			path = QPainterPath()
			moveTo = True
			for j in range(len(xs[i])):
				# Check for break in data, resart lines
				if ys[i][j] is False:
					moveTo = True
					continue

				x = axesX + (self.totalSeconds(xs[i][j]) - minX) / spanX * chartWidth
				if spanY > 0:
					y = axesY - (ys[i][j] - minY) / spanY * chartHeight
				else:
					y = axesY

				if moveTo:
					path.moveTo(x, y)
					moveTo = False
				else:
					path.lineTo(x, y)

			painter.drawPath(path)
		
		# Draw a circle if one data point
		# Note that no line will be drawn
		if oneDataPoint:
			for i in range(len(xs) - 1, -1, -1):
				pen = QPen(QColor(255 * self.colors[i][0], 255 * self.colors[i][1], 255 * self.colors[i][2]))
				pen.setWidth(self.lineWidth)
				painter.setPen(pen)

				x = axesX + (self.totalSeconds(xs[i][0]) - minX) / spanX * chartWidth
				if spanY > 0:
					y = axesY - (ys[i][0] - minY) / spanY * chartHeight
				else:
					y = axesY
				painter.drawEllipse(x - 1, y - 1, 3, 3)

		# Draw buys
		if self.buyXs:
			painter.setPen(QPen(QColor(51, 51, 51)))
			painter.setBrush(QBrush(QColor(0, 180, 0)))
			for i in range(len(self.buyXs)):
				x = axesX + (self.totalSeconds(self.buyXs[i]) - minX) / spanX * chartWidth
				y = self.buyYs[i]
				if spanY > 0:
					y = axesY - (self.buyYs[i] - minY) / spanY * chartHeight
				else:
					y = axesY

				painter.drawConvexPolygon(QPolygonF([QPointF(x, y), QPointF(x + self.transactionSize * 2/3, y + self.transactionSize), QPointF(x - self.transactionSize * 2/3, y + self.transactionSize)]))
				
		# Draw sells
		if self.sellXs:
			painter.setPen(QPen(QColor(51, 51, 51)))
			painter.setBrush(QBrush(Qt.red))
			for i in range(len(self.sellXs)):
				x = axesX + (self.totalSeconds(self.sellXs[i]) - minX) / spanX * chartWidth
				y = self.sellYs[i]
				if spanY > 0:
					y = axesY - (self.sellYs[i] - minY) / spanY * chartHeight
				else:
					y = axesY
				
				painter.drawConvexPolygon(QPolygonF([QPointF(x, y), QPointF(x - self.transactionSize * 2/3, y - self.transactionSize), QPointF(x + self.transactionSize * 2/3, y - self.transactionSize)]))

		# Draw splits
		if self.splitXs:
			painter.setPen(QPen(QColor(51, 51, 51)))
			painter.setBrush(QBrush(Qt.gray))
			for i in range(len(self.splitXs)):
				x = axesX + (self.totalSeconds(self.splitXs[i]) - minX) / spanX * chartWidth
				y = self.splitYs[i]
				if spanY > 0:
					y = axesY - (self.splitYs[i] - minY) / spanY * chartHeight
				else:
					y = axesY
				
				painter.drawConvexPolygon(QPolygonF([
					QPointF(x - self.transactionSize / 2, y + self.transactionSize / 2),
					QPointF(x - self.transactionSize / 2, y - self.transactionSize / 2),
					QPointF(x - 2, y - self.transactionSize / 2),
					QPointF(x - 2, y + self.transactionSize / 2)]))
				painter.drawConvexPolygon(QPolygonF([
					QPointF(x + 2, y + self.transactionSize / 2),
					QPointF(x + 2, y - self.transactionSize / 2),
					QPointF(x + self.transactionSize / 2, y - self.transactionSize / 2),
					QPointF(x + self.transactionSize / 2, y + self.transactionSize / 2)]))

		# Draw dividends
		if self.dividendXs:
			for i in range(len(self.dividendXs)):
				x = axesX + (self.totalSeconds(self.dividendXs[i]) - minX) / spanX * chartWidth
				y = self.dividendYs[i]
				if spanY > 0:
					y = axesY - (self.dividendYs[i] - minY) / spanY * chartHeight
				else:
					y = axesY

				painter.setPen(QPen(QColor(0, 120, 0)))
				painter.setBrush(QBrush(QColor(0, 180, 0)))
				self.drawString("$", x, y, self.transactionSize * 0.75, "center middle", bold = True, outline = True)

		# Draw shorts
		if self.shortXs:
			painter.setBrush(QBrush(Qt.red))
			for i in range(len(self.shortXs)):
				x = axesX + (self.totalSeconds(self.shortXs[i]) - minX) / spanX * chartWidth
				y = self.shortYs[i]
				if spanY > 0:
					y = axesY - (self.shortYs[i] - minY) / spanY * chartHeight
				else:
					y = axesY
				
				painter.setPen(QPen(QColor(51, 51, 51)))
				painter.drawConvexPolygon(QPolygonF([QPointF(x, y), QPointF(x - self.transactionSize * 2/3, y - self.transactionSize), QPointF(x + self.transactionSize * 2/3, y - self.transactionSize)]))
				painter.setPen(QPen(Qt.white))
				self.drawString("s", x, y - self.transactionSize * 2 / 3, 9, "center middle")


		# Draw covers
		if self.coverXs:
			painter.setBrush(QBrush(QColor(0, 180, 0)))
			for i in range(len(self.coverXs)):
				x = axesX + (self.totalSeconds(self.coverXs[i]) - minX) / spanX * chartWidth
				y = self.coverYs[i]
				if spanY > 0:
					y = axesY - (self.coverYs[i] - minY) / spanY * chartHeight
				else:
					y = axesY

				painter.setPen(QPen(QColor(51, 51, 51)))
				painter.drawConvexPolygon(QPolygonF([QPointF(x, y), QPointF(x + self.transactionSize * 2/3, y + self.transactionSize), QPointF(x - self.transactionSize * 2/3, y + self.transactionSize)]))
				painter.setPen(QPen(Qt.white))
				self.drawString("c", x, y + self.transactionSize * 2 / 3, 9, "center middle")

		painter.end()
		return
	
	def resizeEvent(self, event):
		w = self.size().width()
		h = self.size().height()

		# Get rid of margin if it is the same size as the data
		margin = self.margin
		if margin * 4 > w:
			margin = 0
		
		self.w = w
		self.h = h
		self.chartMinX = margin
		self.chartMinY = margin
		self.chartSpanX = w - margin * 2
		self.chartSpanY = h - margin * 2
