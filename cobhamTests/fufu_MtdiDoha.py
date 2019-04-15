from PyQt5 import QtCore


class FufuMtdi(QtCore.QThread):
    def __init__(self, controller, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.controller = controller
        self._stopFlag = False
