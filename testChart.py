import sys
import os

from PyQt4.QtCore import *

from portfolio import *
from stockData import *
from prefs import *
from chartWidget import *
import appGlobal

prefs = Prefs()

app = QApplication(sys.argv)
app.isOSX = True
appGlobal.setApp(app, os.path.dirname(__file__))
p = Portfolio("Scottrade")

stockData = StockData()

w = ChartWidget()
w.setFixedSize(300, 200)
w.resizeEvent(None)
p.chart(w, stockData, "__COMBINED__", doSplit = True)

img = QPixmap(w.size());
painter = QPainter(img);
w.paintEvent(None, painter)
img.save("test.jpg");
