import re
import socket

import subprocess
import time

from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox


class FufuMtdi(QtCore.QThread):
    def __init__(self, controller, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.controller = controller
        self._stopFlag = False
        self.asis = None
        self.ip = None

    def set_test_name(self, name):
        self.controller.send_test_name(name, 'Started')
        self.current_test_name = name

    def start_current_test(self, test):
        test_result = getattr(self, test)()
        self.controller.send_test_name(self.current_test_name, 'Completed\n')
        return test_result

    def run_test_msdh_connection_10(self):
        self.set_test_name('Check MSDH connection')
        test_result = self.check_msdh_connection()
        if not test_result:
            q = self.controller.send_msg('i', 'MTDI FUFU', 'Connect USB, Ethernet cable to the MSDH and press OK.', 2)
            if q == QMessageBox.Retry:
                self.run_test_msdh_connection_10()
        return test_result

    def run_test_mtdi_connection_msdh_20(self):
        self.set_test_name('MTDI connection via MSDH')
        q = self.controller.send_msg('i', 'MTDI FUFU', 'Connect MSDH and MTDI systems via optical cable and press OK', 2)
        if q == QMessageBox.Cancel:
            return
        if self.get_mtdi_ip() is not None:
            return True
        return False

    def run_test_check_bands_msdh_30(self):
        self.set_test_name('Check bands via MSDH')

        bands = self.controller.send_com_command(
            'send_msg -d {} -c "cat /tmp/run/axell/rf_ranges.dat"'.format(self.ip)).split('\r\n')
        asis_band = None
        bands_dict = {}
        for i in bands:
            try:
                tmp = re.search('^([A-Z0-9]{4})', i).group()
                if tmp == 'BAND':
                    self.controller.log_signal.emit('Found {} ASIS: {}'.format(i, asis_band))
                    bands_dict.update({i: tmp})
                else:
                    asis_band = tmp
            except Exception as e:
                # print(e)
                continue
        if len(bands_dict) == 4:
            status = True
        else:
            status = False
        self.controller.log_signal.emit('Check bands: {}'.format(status))
        return status

    def run_test_mtdi_connection_com_40(self):
        self.set_test_name('MTDI connection via COM')
        q = self.controller.send_msg('i', 'MTDI FUFU', 'Connect USB, Ethernet cable to the MTDI and press OK.', 2)
        if q == QMessageBox.Cancel:
            return
        test_result = self.check_mtdi_connection()
        if not test_result:
            self.run_test_mtdi_connection_com_40()
        return test_result

    def run_test_check_bands_com_50(self):
        self.set_test_name('Check bands via COM')

        bands = self.controller.send_com_command('cat /tmp/run/axell/rf_ranges.dat'.format(self.ip)).split('\r\n')
        asis_band = None
        bands_dict = {}
        for i in bands:
            try:
                tmp = re.search('^([A-Z0-9]{4})', i).group()
                if tmp == 'BAND':
                    self.controller.log_signal.emit('Found {} ASIS: {}'.format(i, asis_band))
                    bands_dict.update({i: tmp})
                else:
                    asis_band = tmp
            except:
                continue
        if len(bands_dict) == 4:
            status = True
        else:
            status = False
        self.controller.log_signal.emit('Check bands: {}'.format(status))
        return status

    def run_test_check_ethernet_60(self):
        self.set_test_name('Check MTDI Ethernet')

        system_dns = self.get_windows_dns_ips()
        n = 5
        while n >= 0:
            mtdi_dns = self.controller.send_com_command('udhcpc')
            for i in system_dns:
                if i in mtdi_dns:
                    self.controller.log_signal.emit("MTDI DNS: {}".format(i))
                    return True
            n -= 1
            time.sleep(1)


    def get_mtdi_ip(self):
        tmp = self.controller.send_com_command('linkstatus --json')
        res = self.controller.str_to_dict(tmp)
        for i in res.get('linkstatus'):
            if i.get("Enabled") == "YES" and i.get("Link State") == "M-UP":
                self.asis = i.get("serial")
                self.controller.log_signal.emit(
                    "Found MTDI on Link: {} ASIS: {}".format(i.get("Link"), i.get("serial")))
                tmp = self.controller.send_com_command('topology --ip --json')
                res = self.controller.str_to_dict(tmp)
                for nodes in res.get('nodes'):
                    if nodes.get('ID') == self.asis:
                        self.ip = nodes.get("IP")
                        self.controller.log_signal.emit("IP address: {}".format(self.ip))
                        return self.ip
        q = self.controller.send_msg('w', 'Warning', 'MTDI not found', 5)
        if q == QMessageBox.Retry:
            self.get_mtdi_ip()
        self._stopFlag = True

    def mtdi_connection(self, status, ip):
        current_model = self.get_model()
        if status and 'MTDI' in current_model:
            return True
        if status and 'MSDH' in current_model:
            tmp = self.controller.send_com_command('dbclient {}'.format(ip))
            '''
            If first time connection
            '''
            if 'Do you want to continue connecting? (y/n)' in tmp:
                tmp = self.controller.send_com_command('y')
                if tmp == "root@{}'s password:".format(ip):
                    self.controller.send_com_command('CobhamRoot/n')
            if 'MTDI' in self.get_model():
                return True
            else:
                return False

    def check_mtdi_connection(self):
        if self.check_login('MTDI'):
            return True


    def check_msdh_connection(self):
        if self.check_login('MSDH'):
            return True



    def check_login(self, device):
        if not self.is_password_now():
            q = self.controller.send_msg('w', 'Warning', '{} login error'.format(device), 5)
            if q == QMessageBox.Retry:
                self.check_login(device)
            return False
        model = self.get_model()
        if device in model:
            return True
        else:
            self.controller.send_com_command('exit')
            self.check_login(device)
        return False

    def get_model(self):
        return self.controller.send_com_command('axsh get MDL').split('/n')[0]

    def is_password_now(self):
        tmp = self.controller.send_com_command('')
        if 'password:' in tmp:
            tmp = self.controller.send_com_command('CobhamRoot')
        if 'root@AxellShell[root]>' in tmp:
            return True
        if 'login:' in tmp:
            if not self.controller.system_login():
                self.controller.send_msg('w', 'CobhamUtils', 'System login fail', 1)
                return
        return False

    def get_windows_dns_ips(self):
        output = subprocess.check_output(["ipconfig", "-all"])
        ipconfig_all_list = output.decode("utf-8").split('\n')

        dns_ips = []
        for i in range(0, len(ipconfig_all_list)):
            if "DNS Servers" in ipconfig_all_list[i]:
                # get the first dns server ip
                first_ip = ipconfig_all_list[i].split(":")[1].strip()
                if not self.is_valid_ipv4_address(first_ip):
                    continue
                dns_ips.append(first_ip)
                # get all other dns server ips if they exist
                k = i + 1
                while k < len(ipconfig_all_list) and ":" not in ipconfig_all_list[k]:
                    ip = ipconfig_all_list[k].strip()
                    if self.is_valid_ipv4_address(ip):
                        dns_ips.append(ip)
                    k += 1
                # at this point we're done
                # break
        return dns_ips

    def is_valid_ipv4_address(self, address):
        try:
            socket.inet_pton(socket.AF_INET, address)
        except AttributeError:  # no inet_pton here, sorry
            try:
                socket.inet_aton(address)
            except socket.error:
                return False
            return address.count('.') == 3
        except socket.error:  # not a valid address
            return False

        return True


