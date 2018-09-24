# import PyQt5.QtGui as qtg
# fdb = qtg.QFontDatabase
import sys,traceback
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtGui import QFontDatabase
from gfonts import gFontsTool
from PyQt5.QtCore import pyqtSignal,pyqtSlot
from io import BytesIO

class bgProcSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.
    Supported signals are:
    finished
        No data
    error
        `tuple` (exctype, value, traceback.format_exc() )
    result
        `object` data returned from processing, anything
    progress
        `int` indicating % progress
    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class bgProc(QtCore.QRunnable):
    '''
    Worker thread
    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.
    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    '''

    def __init__(self, fn, *args, **kwargs):
        super(bgProc, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = bgProcSignals()

        # Add the callback to our kwargs
        # self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

class GFonts(QtWidgets.QMainWindow):
	def __init__(self):
		super(GFonts, self).__init__()
		uic.loadUi('gfonts.ui', self)
		self.fTool = gFontsTool()
		self.threadPool = QtCore.QThreadPool()
		
		self.DDFamily.currentIndexChanged.connect(self.familySelected)
		self.DDWeight.currentIndexChanged.connect(self.weightSelected)

		self.show()
		
		worker = bgProc(self.fTool.getMetadata)
		worker.signals.finished.connect(self.mdLoaded)
		self.threadPool.start(worker)
		
		self.statusBar().showMessage('Loading metadata...')
		
	def mdLoaded(self):
		# metadata loaded handler
		self.DDFamily.addItems(self.fTool.getFamilies())
		self.statusBar().showMessage('Loading metadata... Done')
	
	def familySelected(self,index):
		selName = self.DDFamily.currentText()
		self.DDWeight.clear()
		self.DDWeight.addItems(self.fTool.getWeights(selName))
		
	def weightSelected(self,index):
		selName = self.DDFamily.currentText()
		selWeight = self.DDWeight.currentText()
		worker = bgProc(self.fTool.getCSS,selName,selWeight)
		worker.signals.result.connect(self.cssLoaded)
		self.threadPool.start(worker)
		
		self.statusBar().showMessage('Retrieving CSS')
		
	def cssLoaded(self,css):
		print('CSS',css)
		pcss = self.fTool.getParsedCSS(css)
		au = self.fTool.getFontAllURIs(pcss)
		fancyName = self.fTool.getFontFullNames(pcss.rules)
		sName = self.fTool.selectSimplestName(fancyName)
		
		worker = bgProc(self.fTool.getFontBitStreams,au)
		worker.signals.result.connect(self.bsLoaded)
		self.threadPool.start(worker)
		
		self.statusBar().showMessage('Retrieving font')
		
	def bsLoaded(self,bs):
		self.statusBar().showMessage('Font loaded')
		key = list(bs.keys())[0]
		self.ttf = QtCore.QByteArray()
		bio = QtCore.QBuffer(self.ttf)
		bio.open(QtCore.QIODevice.WriteOnly)
		self.fTool.mergeBitStreams(bs[key],bio)
		self.statusBar().showMessage('Font merged')
		self.fdb = QFontDatabase()
		insertion = self.fdb.addApplicationFontFromData(self.ttf)
		print('Insertion:',insertion)
		if insertion == -1:
			print ('Failed to insert font into database')
		fName = key[0]
		fWeight = key[1]
		print('Converted bitstream to ttf for:',fName,fWeight)
		print('Bitstream keys:',bs.keys())
		if type(fWeight) == str and fWeight[-1] == 'i':
			fWeight = fWeight[:-1]
			italic = True
		else:
			italic = False
			
		styles = self.fdb.styles(fName)
		print('styles',styles)
		print(fWeight,italic)
		for s in styles:
			print('s:',s)
			print('s weight:',self.fdb.weight(fName,s))
			print('s italic:',self.fdb.italic(fName,s))
			if self.fdb.weight(fName,s) == self.fTool.CSS2QtFontWeight(fWeight) and self.fdb.italic(fName,s) == italic:
				thisStyle = s
				break
			else:
				thisStyle = None
		print(thisStyle)
		font = self.fdb.font(fName,thisStyle,40)
		self.SampleText.setFont(font)

if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	window = GFonts()
	sys.exit(app.exec_())