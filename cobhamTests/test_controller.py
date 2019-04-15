import ast
import logging
import re
import threading
import time

import datetime
import traceback
from concurrent import futures

import serial
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from cobhamTests.fufu_IDOBR import FufuiDOBR
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
    test_result_signal = QtCore.pyqtSignal(int, bool)

    def __init__(self, parent=None, **kwargs):
        QtCore.QThread.__init__(self, parent)
        self.startTime = datetime.datetime.now().timestamp()
        self.curr_parent = kwargs.get('curr_parent')
        self.type_test = kwargs.get('type_test')
        self.settings = CobhamDB().get_all_data('settings')
        self.login_msg = self.curr_parent.login_msg
        self.isSystemBoot = False
        self.curr_test = None
        self.db = CobhamDB()

    """
    Run selected tests or calibration
    """
    def run(self):
        test_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            if not Instruments(controller=self).check_instr():
                return
            if self.type_test == 'FufuiDOBR':
                # if not self.curr_parent.check_calibration():
                #     return
                if not self.system_login():
                    self.send_msg('w', 'CobhamUtils', 'System login fail', 1)
                    return
                self.send_com_command('axsh SET NIC eth0 DYNAMIC')
                self.get_ip()

                self.curr_test = FufuiDOBR(self)
                self.db.set_test_type(self.type_test)
                count = self.curr_parent.w_main.tests_tab.rowCount()
                tests_queue = self.curr_parent.tests_queue
                for x in range(0, count):
                    tmp = self.curr_parent.w_main.tests_tab.item(x, 1).text()
                    for i in list(tests_queue.values()):
                        if i[0] == tmp:
                            test = i[1]
                            break
                    is_enable = self.curr_parent.w_main.tests_tab.item(x, 0).checkState()
                    if is_enable == 2:
                        curr_test = self.curr_parent.w_main.tests_tab.item(x, 1).text()
                        result = self.curr_test.start_current_test(test)
                        for_save = {'type_test': self.type_test,
                                    'system_asis': self.curr_parent.w_main.asis_lbl.text(),
                                    'date_test': test_date,
                                    'meas_name': curr_test,
                                    'meas_func': test,
                                    'status': result}
                        self.db.save_test_result(for_save)
                        self.test_result_signal.emit(x, result)

            if self.type_test == 'calibration':
                self.curr_test = Calibration(controller=self)
                self.curr_test.run_calibration()
        # except ValueError as e:
        #     if str(e) == 'com_port': return
        #     self.send_msg('w', 'CobhamUtils', str(e), 1)
        #     return
        except serial.serialutil.SerialException as e:
            self.send_msg('c', 'Error', str(e), 1)
            print(e)
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
        print("login -> {}".format(res))
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
                raise ValueError('Login fail. Fix the problem and try again.')

    def send_com_command(self, cmd):
        cmd_tmp = cmd
        if cmd == self.settings.get('user_name') or \
                cmd == self.settings.get('user_pass') or \
                    len(cmd) == 0:
            is_login = True
        else:
            is_login = False

        with ComPort.get_connection() as ser:
            try:
                cmd = cmd + '\r'
                ser.write(cmd.encode('utf-8'))
                res = ser.read()
                self.check_com_signal.emit(ser.is_open)
                repeat = 0
                while 1:
                    time.sleep(.5)
                    data_left = ser.inWaiting()
                    res += ser.read(data_left)
                    if data_left == 0:
                        if len(res) == (len(cmd) + 1) and repeat < 20:
                            repeat += 1
                            continue
                        else:
                            break
                res = str(res, 'utf-8')
                # print(res)
                # if 'timeout end with no input' in res or 'ERROR' in res:
                #     ser.close()
                #     self.send_com_command(cmd_tmp)
                if '-sh:' in res:
                    # self.send_msg('w', 'Error', res, 1)
                    raise ValueError(res)
                if res is None:
                    q = self.send_msg('q', 'Cobham utils', 'Command "{}" received None.'.format(cmd))
                    if q == QMessageBox.Retry:
                        self.send_com_command(cmd)
                    if q == QMessageBox.Cancel:
                        pass
                if not is_login:
                    res = str(res).replace(cmd, '').replace('root@AxellShell[root]>', '')
                return res
            except Exception as e:
                q = self.send_msg('q', 'Cobham utils', str(e), 5)
                if q == QMessageBox.Retry:
                    self.send_com_command(cmd)
                if q == QMessageBox.Cancel:
                    raise e

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

    @staticmethod
    def true_to_pass(val):
        if val:
            return 'PASS'
        return 'FAIL'

    def test(self):
        print(self.curr_test)

        with futures.ThreadPoolExecutor(1) as executor:
            print(self.curr_test)
            executor.submit(self.curr_test.stop_test)
