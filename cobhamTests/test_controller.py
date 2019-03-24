import ast
import logging
import re
import threading
import time

import datetime
import traceback

import serial
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from cobhamTests.fufu_MtdiDoha import FufuMtdi
from database.cobhamdb import CobhamDB
from utils.calibration import Calibration
from utils.comPorts import ComPort
from utils.instruments import Instruments


class TestController(QtCore.QThread):
    LOG_FILENAME = './Log/cobham_utils.log'
    logging.basicConfig(filename=LOG_FILENAME, level=logging.ERROR)

    log_signal = QtCore.pyqtSignal(str)
    log_signal_arg = QtCore.pyqtSignal(str, int)
    timer_signal = QtCore.pyqtSignal(float)
    msg_signal = QtCore.pyqtSignal(str, str, str, int)
    input_signal = QtCore.pyqtSignal(str)
    set_label_signal = QtCore.pyqtSignal(str, str)
    check_com_signal = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None, **kwargs):
        QtCore.QThread.__init__(self, parent)
        self.curr_parent = kwargs.get('curr_parent')
        self.type_test = kwargs.get('type_test')
        self.settings = CobhamDB().get_all_data('settings')
        self.login_msg = self.curr_parent.login_msg
        self.isSystemBoot = False
        self.db = CobhamDB()

    def run(self):
        try:
            print(self.db.get_offset(1578.32))
            if not Instruments(controller=self).check_instr():
                return
            if self.type_test == 'test':
                if not self.curr_parent.check_calibration():
                    return
                if not self.system_login():
                    self.send_msg('w', 'CobhamUtils', 'System login fail', 1)
                    return
                self.get_ip()
                # self.get_bands()

                FufuMtdi(self)
            if self.type_test == 'calibration':
                calibr = Calibration(controller=self)
                calibr.run_calibration()
        except ValueError as e:
            self.send_msg('w', 'CobhamUtils', str(e), 1)
            return
        except serial.serialutil.SerialException as e:
            self.send_msg('c', 'Error', str(e), 1)
            return
        except Exception as e:
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            self.log_signal_arg.emit(traceback_str, -1)
            self.send_msg('c', 'Error', str(e), 1)
            return

    def system_up_check(self):
        res = self.send_com_command('')
        if not self.login_msg in res:
            match = re.search(r'(Axell-Controller-)(\w{4}\s)(login:)', res)
            if match:
                self.system_login()
            else:
                t = threading.Thread(target=self.axell_boot)
                t.start()
                start = datetime.datetime.now().timestamp()
                while not self.isSystemBoot:
                    delta = datetime.datetime.now().timestamp() - start
                    self.timer_signal.emit(delta)
                    time.sleep(1)
        # ToDo: add timeout( return False)
        return True

    def axell_boot(self):
        self.log_signal_arg.emit("Waiting End of Axell boot", 0)
        with ComPort.get_connection() as ser:
            while ser.is_open:
                try:
                    try:
                        out = str(ser.readline(), 'utf-8').replace("\n", "")
                    except:
                        out = ser.readline()
                    if len(out) != 0:
                        # if out not string
                        if not isinstance(out, str):
                            continue
                        self.set_label_signal.emit('console_lbl', out)
                        if 'End of Axell boot' in out:
                            self.isSystemBoot = True
                            self.curr_parent.send_log("Done")
                            time.sleep(3)
                            self.system_login()
                except serial.SerialException as e:
                    return e

    def system_login(self):
        res = self.send_com_command('')
        re_string = '({})@[\S]+\[{}\]'.format(self.settings.get('user_name'), self.settings.get('user_name'))
        if res is None:
            return
        if re.search(re_string, res):
            self.log_signal.emit('System already login ...')
            return True
        else:
            self.log_signal.emit('Login in system ...')
            self.send_com_command(self.settings.get('user_name'))
            time.sleep(1)
            res = self.send_com_command(self.settings.get('user_pass'))
            if re.search(re_string, res):
                self.log_signal.emit('Login in system complete')
                return True
            else:
                self.log_signal.emit('Login fail. Retry after 5 seconds ...')
                time.sleep(5)
                self.system_login()


    def send_com_command(self, cmd):
        # print('-> {}'.format(cmd))
        res = ''
        cmd_tmp = cmd
        if cmd == self.settings.get('user_name') or \
                cmd == self.settings.get('user_pass') or \
                    len(cmd) == 0:
            is_login = True
        else:
            is_login = False
        ser = ComPort.get_connection()
        if 'Exception' in type(ser).__name__:
            self.send_msg('w', 'Warning', str(ser), 1)
            raise ser
        else:
            self.check_com_signal.emit(ser.is_open)
        try:
            cmd = cmd + '\r'
            ser.write(cmd.encode('utf-8'))
            res = ser.read()
            repeat = 0
            while 1:
                time.sleep(.5)
                data_left = ser.inWaiting()
                res += ser.read(data_left)
                # print(len(res), len(cmd), data_left)
                if data_left == 0:
                    if len(res) == (len(cmd) + 1) and repeat < 20:
                        repeat += 1
                        print(repeat)
                        continue
                    else:
                        break
            res = str(res, 'utf-8')
            # print(res)
            if 'timeout end with no input' in res or 'ERROR' in res:
                # ser.close()
                # self.send_com_command(cmd.replace('\r', ''))
                # raise ValueError(res)
                ser.close()
                self.send_com_command(cmd_tmp)
            if '-sh:' in res:
                # self.send_msg('w', 'Error', res, 1)
                raise ValueError(res)
            if res is None:
                q = self.send_msg('q', 'Cobham utils', 'Command "{}" received None.'.format(cmd))
                if q == QMessageBox.Retry:
                    self.send_com_command(cmd)
                if q ==  QMessageBox.Cancel:
                    pass
            if not is_login:
                res = str(res).replace(cmd, '').replace('root@AxellShell[root]>', '')
            # print('<- {}'.format(res))
        except Exception as e:
            raise e
        finally:
            ser.close()
            self.check_com_signal.emit(ser.is_open)
            return res

    def get_ip(self):
        cmd = 'axsh get nic eth0'
        res = self.send_com_command(cmd).strip().split(' ')
        ip = res[1]
        self.set_label_signal.emit('ip_lbl', ip)
        self.log_signal.emit('ip = {}'.format(ip))
        return res

    def get_bands(self):
        bands = []
        q = self.send_com_command('udp_bridge1 list').split('\n')
        for i in q:
            r = re.search('(ABCD\d\d)', i)
            if r is not None:
                bands.append(r.group(0))
        # if len(bands) != 4:
        #     self.send_msg('w', 'Error', 'Found only {} bands'.format(len(bands)), 1)
        #     self.log_signal.emit(self.send_com_command('udp_bridge1 list'))
        #     input('Press Enter for return...')
        return bands

    def get_bands_sn(self):
        bands = self.get_bands()
        bands_sn = {}
        for i, val in enumerate(bands):
            self.log_signal.emit('Getting serial for board with SnapId = {}'.format(val))
            if i/2 < 1:
                bands_sn.update({val: self.get_band_serial(True, i + 1)})
            else:
                bands_sn.update({val: self.get_band_serial(False, i - 1)})
            self.log_signal.emit('Serial number: {}'.format(bands_sn.get(val)))


    def get_band_serial(self, master, n):
        print(n)
        if master:
            res = self.send_com_command('dobr_partNum GET {}'.format(n))
        else:
            res = self.send_com_command('send_msg -d 172.24.30.2 -c dobr_partNum GET {}'.format(n))
        match = re.search(r'(part\snumber\s=\s)\w{4}', res)
        print(res)
        if match:
            for_return = match.group().split('=')[1].strip()
            if for_return is None:
                self.get_band_serial(master, n)
            return for_return
        else:
            self.get_band_serial(master, n)

    def send_msg(self, icon, msgTitle, msgText, typeQestions):
        self.msg_signal.emit(icon, msgTitle, msgText, typeQestions)
        while self.curr_parent.answer is None:
            time.sleep(.05)
        else:
            for_return = self.curr_parent.answer
            self.curr_parent.answer = None
            return for_return

    @staticmethod
    def str_to_dict(val):
        start = val.find('{')
        stop = 0
        for i, j in enumerate(val):
            if j == '}':
                stop = i
        return ast.literal_eval(val[start: stop + 1])

    def send_test_name(self, name, status):
        if status == 'completed':
            status = status + '\n'
        self.log_signal.emit('*** {} *** {}'.format(name, status))

    def get_sdr_info(self):
        info = {}
        for i in ['master_sdr', 'slave_sdr']:
            if i == 'master_sdr':
                pref = ''
            else:
                pref = 'send_msg -d 172.24.30.2 -c '
            val = self.send_com_command(pref + 'axsh get sis').split(' ')
            info.update({i: {'type': val[2], 'asis': val[3]}})
        return info

    @staticmethod
    def true_to_pass(val):
        if val:
            return 'PASS'
        return 'FAIL'

    def get_parent(self):
        return self.curr_parent
