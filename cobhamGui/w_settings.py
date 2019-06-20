import inspect

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QDialog, QComboBox, QLineEdit, QFileDialog, QRadioButton

from database.cobhamdb import CobhamDB
from utils.cfg_parser import Config
from utils.comPorts import ComPort
from utils.instruments import Instruments


class WindowSettings(QDialog):
    def __init__(self, parent):
        super(WindowSettings, self).__init__(parent)
        self.parent = parent
        self.appIcon = parent.appIcon
        self.w_settings = uic.loadUi('forms/settings.ui')
        self.w_settings.setWindowTitle('Settings')
        self.w_settings.setWindowIcon(self.appIcon)

        self.listInstr = None
        ip_validator = QRegExpValidator(QRegExp(parent.re_ip))
        self.w_settings.ip.setValidator(ip_validator)
        self.w_settings.mask.setValidator(ip_validator)

        self.w_settings.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.is_pressed_ok)
        self.w_settings.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.is_pressed_cancel)
        self.w_settings.storm_path_btn.clicked.connect(self.select_storm_path)
        self.w_settings.export_btn.clicked.connect(self.export_settings)
        self.w_settings.import_btn.clicked.connect(self.import_settings)

        self.w_settings.combo_gen.currentTextChanged.connect(self.is_generator_changed)
        self.w_settings.combo_sa.currentTextChanged.connect(self.is_analyzer_changed)

        self.db = CobhamDB()
        self.fill_com_ports()
        self.fill_instruments()
        self.load_settings()
        # self.w_settings.exec_()
        self.w_settings.show()

    def is_pressed_ok(self):
        self.save_settings()
        self.w_settings.close()

    def is_pressed_cancel(self):
        self.w_settings.close()

    '''
    Get available COM ports
    '''
    def fill_com_ports(self):
        com_ports = ComPort()
        for i in com_ports.get_port_list():
            self.w_settings.combo_com.addItem(i[0])
        for i in com_ports.get_baud_list():
            self.w_settings.combo_baud.addItem(str(i))

    def fill_instruments(self):
        instr = Instruments(parent=self.parent)
        self.listInstr = instr.getListInstrument()
        instr.rm.close()
        self.w_settings.combo_gen.addItem('', '')
        self.w_settings.combo_sa.addItem('', '')
        for key in self.listInstr.keys():
            self.w_settings.combo_gen.addItem(self.listInstr.get(key))
            self.w_settings.combo_sa.addItem(self.listInstr.get(key))



    def load_settings(self):
        self.gui_write(self.db.get_all_data('settings'))

    def save_settings(self):
        for_query = {}
        values = self.gui_read()
        for _v in values.keys():
            print(_v)
            for_query.update({_v: values.get(_v)[0]})
        self.db.save_settings(for_query)
        self.parent.check_com(False)
        self.parent.check_calibration()
        self.w_settings.close()

    def verify_settings(self):
        return False


    ''''
    Write to the gui values from data base
    '''
    def gui_write(self, for_write):
        struct = self.gui_read()
        for _v in for_write.keys():
            _v = _v.lower()
            try:
                obj = struct.get(_v)[2]
                if obj.__class__ is QComboBox:
                    index = obj.findText(for_write.get(_v), QtCore.Qt.MatchFixedString)
                    if index != -1:
                        obj.setCurrentIndex(index)
                    else:
                        obj.addItem('')
                        obj.setCurrentIndex(obj.count()-1)
                if obj.__class__ is QLineEdit:
                    obj.setText(for_write.get(_v))
                if obj.__class__ is QRadioButton:
                    if for_write.get(_v).lower() == '1':
                        obj.setChecked(True)
            except Exception as e:
                raise e
        self.parent.check_com(False)


    '''
    Fill dictionary with checked values
    '''
    def gui_read(self):
        for_return = {}
        struct = inspect.getmembers(self.w_settings, lambda a:not(inspect.isroutine(a)))
        for i in struct:
            try:
                if i[1].__class__ is QComboBox:
                    for_return.update({i[0]: [i[1].currentText(), i[1].__class__.__name__, i[1]]})
                if i[1].__class__ is QLineEdit:
                    for_return.update({i[0]: [i[1].text(), i[1].__class__.__name__, i[1]]})
                if i[1].__class__ is QRadioButton:
                    n = 1 if i[1].isChecked() else 0
                    for_return.update({i[0]: [n, i[1].__class__.__name__, i[1]]})
            except:
                continue
        return for_return

    def is_generator_changed(self):
        for i in self.listInstr.keys():
            if self.listInstr.get(i) == self.w_settings.combo_gen.currentText():
                self.w_settings.addr_gen.setText(i)
                break
        if self.w_settings.combo_gen.currentText() == self.w_settings.combo_sa.currentText():
            self.w_settings.combo_sa.setCurrentText('')

    def is_analyzer_changed(self):
        for i in self.listInstr.keys():
            if self.listInstr.get(i) == self.w_settings.combo_sa.currentText():
                self.w_settings.addr_sa.setText(i)
                break
        if self.w_settings.combo_gen.currentText() == self.w_settings.combo_sa.currentText():
            self.w_settings.combo_gen.setCurrentText('')

    def select_storm_path(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "Select Storm Interface file", "", "Executable Files (*.exe)",
                                                  options=options)
        if fileName:
            self.w_settings.storm_path.setText(fileName)

    def export_settings(self):
        cfg = Config(self.parent)
        cfg.cfg_write(self.gui_read())

    def import_settings(self):
        cfg = Config(self.parent)
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "Select configuration file", "", "Configuration Files (*.ini)",
                                                  options=options)
        tmp = cfg.cfg_read(file=fileName)
        if not tmp is None:
            self.gui_write(tmp)
            self.parent.send_msg('i', 'Import settings', 'Import settings complete', 1)
