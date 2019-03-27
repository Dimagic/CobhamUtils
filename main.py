import os
import re
import sys
import threading
import time
import logging

import datetime
from concurrent import futures

from PyQt5 import uic, QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QObject, QSize
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QInputDialog, QTableWidgetItem, QHeaderView, QWidget

from cobhamTests.fufu_MtdiDoha import FufuMtdi
from utils.comPorts import ComPort
from cobhamGui.w_calibration import WindowCalibration
from cobhamGui.w_settings import WindowSettings
from cobhamTests.test_controller import TestController
from database.cobhamdb import CobhamDB


VERSION = '0.4.1'
class EventListener(QtCore.QThread):
    timer_signal = QtCore.pyqtSignal(float)
    def __init__(self, parent):
        QtCore.QThread.__init__(self, parent)
        self.parent = parent

    def run(self, including_parent=True):
        while True:
            if not self.parent.controller_thread is None:
                isRuning = self.parent.controller_thread.isRunning()
                if isRuning:
                    self.parent.w_main.start_test_btn.setText('STOP')
                    delta = datetime.datetime.now().timestamp() - self.parent.controller_thread.startTime
                    self.timer_signal.emit(delta)
                else:
                    self.parent.w_main.start_test_btn.setText('START')

                # self.parent.w_main.start_test_btn.setEnabled(not isRuning)
                self.parent.w_main.calibration_btn.setEnabled(not isRuning)
                self.parent.w_main.menubar.setEnabled(not isRuning)
            time.sleep(.5)

class MainApp(QMainWindow, QObject):
    LOG_FILENAME = './Log/cobham_utils.log'
    logging.basicConfig(filename=LOG_FILENAME, level=logging.ERROR)
    re_ip = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.)){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

    def __init__(self, parent=None):
        # logging.debug('This message should go to the log file')
        # logging.info('So should this')
        # logging.warning('And this, too')

        super(MainApp, self).__init__(parent)
        self.db = CobhamDB()

        self.idobr_type = ''
        self.idobr_asis = ''

        self.wk_dir = os.path.dirname(os.path.realpath('__file__'))
        self.appIcon = QtGui.QIcon("img/cobham_c_64x64.ico")
        self.w_main = uic.loadUi('forms/mainwindow.ui')
        self.w_main.setWindowTitle('CobhamUtils {}'.format(VERSION))
        self.w_main.setWindowIcon(self.appIcon)

        self.login_msg = 'root@AxellShell[root]'
        self.answer = None
        self.controller_thread = None
        self.calibration_thread = None

        self.passImg = QtGui.QPixmap('Img/pass.png').scaled(30, 30)
        self.failImg = QtGui.QPixmap('Img/fail.png').scaled(30, 30)
        self.greenLedMovie = QMovie('Img/greenLed.gif')
        self.blueLedMovie = QMovie('Img/blueLed.gif')
        self.redLedMovie = QMovie('Img/redLed.gif')

        self.w_main.start_test_btn.clicked.connect(self.test)
        self.w_main.selectall_chbox.clicked.connect(self.select_all)
        self.w_main.calibration_btn.clicked.connect(self.calibration)
        self.w_main.menu_Settings.triggered.connect(self.window_settings)
        self.w_main.menu_Quit.triggered.connect(self.w_main.close)
        self.w_main.menu_Quit.setShortcut('Ctrl+Q')

        self.check_com(False)
        self.check_calibration()
        self.fill_test_tab()

        self.w_main.show()

        self.stop_event = threading.Event()
        self.c_thread = EventListener(self)
        self.c_thread.timer_signal.connect(self.set_timer, QtCore.Qt.QueuedConnection)
        self.c_thread.start()

    def fill_test_tab(self):
        self.w_main.tests_tab.setColumnCount(3)
        self.w_main.tests_tab.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.w_main.tests_tab.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.w_main.tests_tab.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.w_main.tests_tab.setHorizontalHeaderLabels(["", "Test name", "Status"])
        # self.w_main.tests_tab.horizontalHeaderItem(0).setToolTip("Column 1 ")
        # self.w_main.tests_tab.horizontalHeaderItem(1).setToolTip("Column 2 ")

        test_dict = self.get_tests_queue(FufuMtdi)
        keys = sorted(list(test_dict.keys()))
        for key in keys:
            rowPosition = self.w_main.tests_tab.rowCount()
            chkBoxItem = QTableWidgetItem()
            chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            chkBoxItem.setCheckState(QtCore.Qt.Checked)

            self.w_main.tests_tab.insertRow(rowPosition)
            self.w_main.tests_tab.setItem(rowPosition, 0, chkBoxItem)
            self.w_main.tests_tab.setItem(rowPosition, 1, QTableWidgetItem(test_dict.get(key)))
            self.w_main.tests_tab.setItem(rowPosition, 2, None)

    def set_test_status(self, rowPosition, status):
        if status:
            result = QTableWidgetItem(QtGui.QIcon(self.passImg), "")
        else:
            result = QTableWidgetItem(QtGui.QIcon(self.failImg), "")
        self.w_main.tests_tab.setItem(rowPosition, 2, result)

    def get_tests_queue(self, object):
        methods = [method_name for method_name in dir(object) if callable(getattr(object, method_name))]
        tests_queue = {}
        for i in methods:
            if 'run_test_' in i:
                try:
                    n = re.search('[\d]+$', i).group(0)
                    tests_queue.update({int(n): i})
                except:
                    self.send_msg('c', 'CobhamUtils', 'Not found queue number in method {}'.format(i), 1)
                    return
        return tests_queue

    def select_all(self):
        state = self.w_main.selectall_chbox.checkState()
        count = self.w_main.tests_tab.rowCount()
        for x in range(0, count):
            self.w_main.tests_tab.item(x, 0).setCheckState(state)

    def check_com(self, val):
        self.w_main.port_lbl.setText(self.db.get_settings_by_name('combo_com'))
        self.w_main.baud_lbl.setText(self.db.get_settings_by_name('combo_baud'))
        self.greenLedMovie.setScaledSize(QSize(13, 13))
        isPortPresent = False
        for i in ComPort.get_port_list():
            if self.db.get_settings_by_name('combo_com') == i[0]:
                isPortPresent = True
        if isPortPresent:
            if val:
                self.w_main.comstat_lbl.setMovie(self.greenLedMovie)
                self.greenLedMovie.start()
            else:
                self.w_main.comstat_lbl.setMovie(self.blueLedMovie)
                self.blueLedMovie.start()
        else:
            self.w_main.comstat_lbl.setMovie(self.redLedMovie)
            self.redLedMovie.start()

    def check_calibration(self):
        try:
            # ToDo: modify check calibration algorithm
            icon = self.passImg
            cal_date = self.db.get_settings_by_name('last_calibr')
            # print(datetime.strptime(cal_date, '%Y-%m-%d'))
            self.w_main.calstat_lbl.setToolTip('Calibration date: {}'.format(cal_date))
            is_calibrated = True
        except:
            icon = self.failImg
            is_calibrated = False
        finally:
            self.w_main.start_test_btn.setEnabled(is_calibrated)
            self.w_main.calstat_lbl.setPixmap(icon)
            return is_calibrated

    def test(self):
        if self.w_main.start_test_btn.text() == 'START':
            self.run_controller(type_test='test')
        else:
            if self.send_msg('i', 'CobhamUtils', 'stop', 2) == QMessageBox.Ok:
                with futures.ThreadPoolExecutor(1) as executor:
                    executor.submit(self.controller_thread.test)
                # self.controller_thread.curr_test.stop_test()



    def calibration(self):
        WindowCalibration(self)
        # Calibration(self)
        # self.run_controller(type_test='calibration')
        # self.check_calibration()

    def run_controller(self, **kwargs):
        self.w_main.art_lbl.setText('')
        self.w_main.rev_lbl.setText('')
        self.w_main.ser_lbl.setText('')
        self.w_main.ip_lbl.setText('')
        self.w_main.list_log.clear()
        count = self.w_main.tests_tab.rowCount()
        for rowPosition in range(0, count):
            self.w_main.tests_tab.setItem(rowPosition, 2, None)

        if kwargs.get('type_test') == 'test':
            val = self.input_msg('Scan SN:')
            if val is None:
                return
            else:
                tmp = val.split('/')
                if len(tmp) != 2:
                    self.send_msg('w', 'Warning', 'Entered incorrect number', 1)
                    return False
                self.idobr_type = tmp[0]
                self.idobr_asis = tmp[1]
                l = len(tmp[0])
                self.w_main.art_lbl.setText(tmp[0][:l-1])
                self.w_main.rev_lbl.setText(tmp[0][l-1:])
                self.w_main.ser_lbl.setText(tmp[1])

        self.controller_thread = TestController(curr_parent=self, type_test=kwargs.get('type_test'))
        self.controller_thread.log_signal.connect(self.send_log, QtCore.Qt.QueuedConnection)
        self.controller_thread.log_signal_arg.connect(self.send_log, QtCore.Qt.QueuedConnection)
        self.controller_thread.timer_signal.connect(self.set_timer, QtCore.Qt.QueuedConnection)
        self.controller_thread.msg_signal.connect(self.send_msg, QtCore.Qt.QueuedConnection)
        self.controller_thread.input_signal.connect(self.input_msg, QtCore.Qt.QueuedConnection)
        self.controller_thread.set_label_signal.connect(self.set_label_text, QtCore.Qt.QueuedConnection)
        self.controller_thread.check_com_signal.connect(self.check_com, QtCore.Qt.QueuedConnection)
        self.controller_thread.test_result_signal.connect(self.set_test_status, QtCore.Qt.QueuedConnection)
        self.controller_thread.start()

    def window_settings(self):
        WindowSettings(self)

    def send_log(self, *args):
        self.w_main.list_log.addItem(args[0])
        if len(args) > 1:
            numrows = len(self.w_main.list_log)
            if args[1] == 1:
                self.w_main.list_log.item(numrows - 1).setForeground(QtCore.Qt.green)
            if args[1] == -1:
                self.w_main.list_log.item(numrows - 1).setForeground(QtCore.Qt.red)
        self.w_main.list_log.scrollToBottom()

    def send_log_same_line(self, *args):
        numrows = len(self.w_main.list_log)
        try:
            print(self.w_main.list_log.currentRow())
        except Exception as e:
            print(e)
        self.w_main.list_log.addItem(args[0])
        self.w_main.list_log.scrollToBottom()

    def set_timer(self, val):
        # val should be in ms
        timer = time.strftime('%M:%S', time.gmtime(val))
        self.w_main.timer_label.setText(str(timer))

    def set_label_text(self, label, value):
        obj = self.w_main.__dict__.get(label)
        obj.setText(value)

    def send_msg(self, icon, msgTitle, msgText, typeQuestion):
        msg = QMessageBox()
        if icon == 'q':
            msg.setIcon(QMessageBox.Question)
        elif icon == 'i':
            msg.setIcon(QMessageBox.Information)
        elif icon == 'w':
            msg.setIcon(QMessageBox.Warning)
        elif icon == 'c':
            msg.setIcon(QMessageBox.Critical)
        msg.setText(msgText)
        msg.setWindowTitle(msgTitle)
        msg.setWindowIcon(self.appIcon)
        if typeQuestion == 1:
            msg.setStandardButtons(QMessageBox.Ok)
        elif typeQuestion == 2:
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        elif typeQuestion == 3:
            msg.setStandardButtons(QMessageBox.Ignore | QMessageBox.Retry | QMessageBox.Cancel)
        self.answer = msg.exec_()
        return self.answer

    def input_msg(self, msg):
        return 'DOBR0292/NUES'
        # input = QInputDialog()
        # input.setWindowIcon(self.appIcon)
        # text, okPressed = input.getText(self, 'Input', msg)
        # print(okPressed)
        # if okPressed and text != '':
        #     return text
        # return None

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QMainWindow()
    prog = MainApp()
    app.exec_()
    sys.exit(0)
