import matplotlib
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog
from database.cobhamdb import CobhamDB

matplotlib.use('Qt5Agg')

class WindowCalibration(QDialog):
    def __init__(self, parent):
        super(WindowCalibration, self).__init__(parent)
        self.parent = parent
        self.appIcon = parent.appIcon
        self.w_calibration = uic.loadUi('forms/calibration.ui')
        self.w_calibration.setWindowTitle('Calibration')
        self.w_calibration.setWindowIcon(self.appIcon)
        self.db = CobhamDB()

        self.w_calibration.start_btn.clicked.connect(self.run_calibration)

        self.w_calibration.exec_()

    def run_calibration(self):
        self.parent.run_controller(type_test='calibration')