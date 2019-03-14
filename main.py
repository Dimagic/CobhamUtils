import logging
import re
import sys

import time

import os
from PyQt5 import uic, QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QInputDialog

from cobhamGui.w_settings import WindowSettings
from cobhamTests.test_controller import TestController


VERSION = '0.2'
LOG_FILENAME = './Log/cobham_utils.log'

class MainApp(QMainWindow, QObject):
    re_ip = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.)){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

    def __init__(self, parent=None):
        logging.basicConfig(filename=LOG_FILENAME, level=logging.ERROR)
        # logging.debug('This message should go to the log file')
        # logging.info('So should this')
        # logging.warning('And this, too')

        super(MainApp, self).__init__(parent)
        self.idobr_type = ''
        self.idobr_asis = ''

        self.wk_dir = os.path.dirname(os.path.realpath('__file__'))
        self.appIcon = QtGui.QIcon("img/cobham_c_64x64.ico")
        self.w_main = uic.loadUi('forms/mainwindow.ui')
        self.w_main.setWindowTitle('CobhamUtils')
        self.w_main.setWindowIcon(self.appIcon)

        self.login_msg = 'root@AxellShell[root]'
        self.answer = None
        self.myThread = None
        self.calibration_thread = None

        self.w_main.button_test.clicked.connect(self.test)
        self.w_main.calibration_btn.clicked.connect(self.calibration)
        # self.w_main.pushCommand.clicked.connect(self.send_com_command)
        self.w_main.menu_Settings.triggered.connect(self.window_settings)
        self.w_main.menu_Quit.triggered.connect(self.w_main.close)
        self.w_main.menu_Quit.setShortcut('Ctrl+Q')

        self.w_main.show()

    def test(self):
        self.run_controller(type_test='test')

    def calibration(self):
        self.run_controller(type_test='calibration')

    def run_controller(self, **kwargs):
        self.w_main.art_lbl.setText('')
        self.w_main.rev_lbl.setText('')
        self.w_main.ser_lbl.setText('')
        self.w_main.ip_lbl.setText('')
        self.w_main.list_log.clear()
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

        self.myThread = TestController(curr_parent=self, type_test=kwargs.get('type_test'))
        self.myThread.log_signal.connect(self.send_log, QtCore.Qt.QueuedConnection)
        self.myThread.log_signal_arg.connect(self.send_log, QtCore.Qt.QueuedConnection)
        self.myThread.timer_signal.connect(self.set_timer, QtCore.Qt.QueuedConnection)
        self.myThread.msg_signal.connect(self.send_msg, QtCore.Qt.QueuedConnection)
        self.myThread.input_signal.connect(self.input_msg, QtCore.Qt.QueuedConnection)
        self.myThread.set_label_signal.connect(self.set_label_text, QtCore.Qt.QueuedConnection)
        self.myThread.start()

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
