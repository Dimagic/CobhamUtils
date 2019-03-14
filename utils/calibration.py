import numpy
import time
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from database.cobhamdb import CobhamDB
from utils.instruments import Instruments
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation


class Calibration:
    log_signal = QtCore.pyqtSignal(str)
    log_signal_arg = QtCore.pyqtSignal(str, int)
    timer_signal = QtCore.pyqtSignal(float)
    msg_signal = QtCore.pyqtSignal(str, str, str, int)
    input_signal = QtCore.pyqtSignal(str)
    set_label_signal = QtCore.pyqtSignal(str, str)

    def __init__(self, **kwargs):
        self.controller = kwargs.get('controller')
        self.instr = Instruments(controller=self.controller)
        self.db = CobhamDB()

    def run_calibration(self):
        self.instr.genPreset()
        self.instr.saPreset()
        self.controller.log_signal.emit("Start calibration")
        answer = self.controller.send_msg('i', 'Calibration', "Connect generator to analyzer using "
                                                              "cable with attenuator. And press OK.", 2)
        if answer != QMessageBox.Ok :
            return

        self.db.clear_calibration()
        self.loop_calibration('Sa2Gen')

        answer = self.controller.send_msg('i', 'Calibration', "Connect analyzer to generator using "
                                                              "cable with attenuator. And press OK.", 2)
        if answer != QMessageBox.Ok :
            return
        self.loop_calibration('Gen2Sa')
        self.controller.log_signal.emit('Calibration complete')

    def loop_calibration(self, type):
        list_val = {}
        # time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        time_now = time.strftime("%Y-%m-%d", time.gmtime())
        steep = int(self.db.get_all_data('settings').get('cal_steep'))
        start = int(self.db.get_all_data('settings').get('cal_start'))
        stop = int(self.db.get_all_data('settings').get('cal_stop'))

        self.instr.gen.write("POW:AMPL -20 dBm")
        gen_pow = float(self.instr.gen.query("POW:AMPL?"))
        if type == 'Gen2Sa':
            atten = float(self.db.get_all_data('settings').get('atten_gen'))
        elif type == 'Sa2Gen':
            atten = float(self.db.get_all_data('settings').get('atten_sa'))
        else:
            atten = 0
        self.instr.sa_send_cmd("DISP:WIND:TRAC:Y:RLEV:OFFS {}".format(atten))
        self.instr.gen.write(":OUTP:STAT ON")
        time.sleep(1)
        for i in range(start, stop + steep, steep):
            if i % 50 == 0:
                self.instr.sa_calibration_settings(i)
            self.instr.gen.write(":FREQ:FIX {} MHz".format(i))
            self.instr.sa_send_cmd(":CALC:MARK1:X {} MHz".format(i))
            # self.instr.sa_send_cmd(":TRAC1:MODE VIEW")
            gain = round(float(self.instr.sa_send_query("CALC:MARK1:Y?")), 2)
            offset = round(gen_pow - gain, 2)
            list_val.update({i: offset})
            # self.instr.sa_send_cmd(":TRAC1:MODE WRIT")
            self.controller.log_signal.emit('Freq {} MHz: offset = {}'.format(i, offset))
        self.instr.gen.write(":OUTP:STAT OFF")
        CobhamDB().execute_query("INSERT INTO calibr (type, date, value) VALUES ('{}', '{}', '{}')".format(type,
                                time_now, list_val))

