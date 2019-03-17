import re

import time

import datetime
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from cobhamTests.ttf_calibration import TtfCalibrate
from database.cobhamdb import CobhamDB
from utils.instruments import Instruments
from utils.storm import Storm


class FufuMtdi(QtCore.QThread):
    def __init__(self, controller, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.controller = controller
        self.parent = controller.get_parent()
        self.db = CobhamDB()
        self.bands = None
        self.bands_sn = None
        self.sn_list_master = {}
        self.sn_list_slave = {}
        self.filters = {'ABCD08': [806,5,847],
                        'ABCD09': [942.5,5,897.5],
                        'ABCD18': [1842.5,5,1747.5],
                        'ABCD21': [2140,5,1950]}
        self.test_result = {}
        self.run_fufu()

    def run_fufu(self):
        self.check_bands()

        # TtfCalibrate(self.controller, self.bands).run_calibrate()


        # self.save_set_file()
        # self.test_band_status()
        # self.set_assembly()
        # self.set_filters(1)
        # self.test_composite_power()
        #
        # self.verify_connections()
        # self.test_swv()
        # self.mute_test()
        # self.test_ext_alarm()
        # self.gpr_gps_test()
        # self.set_ip()
        # self.clear_log()

    def set_assembly(self):
        db = CobhamDB()
        assembly = {}
        assembly.update(self.controller.get_sdr_info())
        assembly.update({'rf_master': self.sn_list_master})
        assembly.update({'rf_slave': self.sn_list_slave})
        assembly.update({'idobr': {'type': self.parent.idobr_type, 'asis': self.parent.idobr_asis}})
        self.controller.log_signal.emit(str(assembly))
        if db.set_idobr(assembly):
            self.controller.log_signal.emit('Creating assembly completed')
        else:
            # ToDo: verify assembly
            self.controller.log_signal_arg.emit('Creating assembly not completed', -1)

    def get_bands(self):
        bands = []
        q = self.controller.send_com_command('udp_bridge1 list').split('\n')
        for i in q:
            r = re.search('(ABCD\d\d)', i)
            if r is not None:
                snap = r.group(0)
                tmp = str(int(re.search('\d{2}$', snap).group(0))) + '00'
                if i.find(tmp) == -1:
                    freq = re.search('\d{3,4}', i).group(0)
                    self.controller.log_signal.emit('Band {}: incorrect SnapId: {}'.format(freq, snap))
                else:
                    self.controller.log_signal.emit('Band {} detected: SnapId: {}'.format(tmp, snap))
                bands.append(snap)
        if len(bands) != 4:
            q = self.controller.send_msg('w', 'Error', 'Found only {} bands'.format(len(bands)), 3)
            if q == QMessageBox.Retry:
                self.get_bands()
            # ToDo: realise Cancel
        return bands

    def get_bands_sn(self):
        sn_list = {}
        for i, j in enumerate(self.bands):
            n = i%2
            while 1:
                q = self.get_sn(i, n)
                if q.get('is_err') is not None:
                    self.controller.log_signal.emit('Get band {} ASIS error. Retrying'.format(j))
                    time.sleep(1)
                    continue
                else:
                    sn = q.get('sn')
                    break
            sn_list.update({j: sn})
            if i < 2:
                self.sn_list_master.update({j: sn})
            else:
                self.sn_list_slave.update({j: sn})
            self.controller.log_signal.emit('Band {} ASIS = {}'.format(j, sn))
        return sn_list

    def get_sn(self, i, n):
        if i < 2:
            tmp = self.controller.send_com_command('dobr_partNum GET {}'.format(n + 1))
        else:
            tmp = self.controller.send_com_command('send_msg -d 172.24.30.2 -c dobr_partNum GET {}'.format(n + 1))
        is_err = re.search('(ERROR)', tmp)
        sn = re.search('[A-Z0-9]{4}', tmp).group(0)
        return {'is_err': is_err, 'sn': sn}

    def check_bands(self):
        self.controller.send_test_name('Check bands', 'starting')
        self.bands = self.get_bands()
        self.bands_sn = self.get_bands_sn()
        status = True
        doubles = {}
        for i in self.bands:
            if i in doubles:
                doubles.update({i: False})
            else:
                doubles.update({i: True})
        if not all(doubles.values()):
            status = False
            self.controller.log_signal.emit('Bands has same names: {}'.format(doubles))
        if not status:
            q = self.controller.send_msg('w', 'Error', 'Bands has same names: {}'.format(doubles), 3)
            if q == QMessageBox.Retry:
                self.check_bands()
        self.controller.log_signal.emit('Check bands: {}'.format(self.controller.true_to_pass(status)))
        self.controller.send_test_name('Check bands', 'completed')
        return status

    def test_band_status(self):
        self.controller.send_test_name('Band status test', 'started')
        tmp = self.controller.send_com_command('dobrstatus --json')
        res = self.controller.str_to_dict(tmp)
        res_list = []
        result = True
        for val in res.get('Bands'):
            if not int(val.get('No')):
                result = False
            if not int(val.get('Band')):
                result = False
            if val.get('Installed').upper() != 'YES':
                result = False
            res_list.append(result)
            self.controller.log_signal.emit('Band {} status = {}'.
                                            format(val.get('Band'), self.controller.true_to_pass(result)))
        test_result = all(res_list)
        self.controller.log_signal.emit('Band status: {}'.format(self.controller.true_to_pass(test_result)))
        self.controller.send_test_name('Band status test', 'completed')
        return test_result

    def test_ext_alarm(self):
        self.controller.send_test_name('External alarms test', 'started')
        self.controller.send_com_command('axsh SET EXT 0 0 0 0')
        keys = ['7', '6', '5', '4']
        res_list = []
        for pin in keys:
            counter = 3
            while True:
                alarms = self.get_ext_alarm()
                if alarms.get(pin) == '0':
                    curr_status = True
                    res_list.append(curr_status)
                    self.controller.log_signal.emit('EXT{} alarm: PASS'.format(pin))
                    break
                else:
                    self.controller.send_msg('i', 'Alarms test', 'Short pin {} to the chassis'.format(pin), 1)
                    counter -= 1
                    if counter < 0:
                        res_list.append(False)
                        self.controller.log_signal.emit('EXT{} alarm: FAIL'.format(pin))
                        break
        test_status = self.controller.true_to_pass(all(res_list))
        self.controller.log_signal.emit('External alarms: {}'.format(test_status))
        self.controller.send_test_name('External alarms test', 'completed')
        return test_status

    def test_swv(self):
        self.controller.send_test_name('Software verification', 'started')
        need_sw = self.db.get_all_data('settings').get('sw_version').split(';')
        need_patch = self.db.get_all_data('settings').get('patch_version').split(';')

        master_model = self.controller.send_com_command('axsh get mdl')
        master_versions = self.controller.send_com_command('axsh get swv')
        master_patch = self.controller.send_com_command('get_patches.sh')
        print(master_model)
        print(master_versions)
        print(master_patch)
        res = 'PASS'
        if not self.check_sw(need_sw, master_versions) or not self.check_sw(need_patch, master_patch):
            res = 'FAIL'
        print('SW ver. verification on board {}: {}'.format(master_model, res))

        slave_model = self.controller.send_com_command('send_msg -d 172.24.30.2 -c "axsh get mdl"').strip()
        slave_versions = self.controller.send_com_command('send_msg -d 172.24.30.2 -c "axsh get swv"')
        slave_path = self.controller.send_com_command('send_msg -d 172.24.30.2 -c "get_patches.sh"')
        res = 'PASS'
        if not self.check_sw(need_sw, slave_versions) or not self.check_sw(need_patch, slave_path):
            res = 'FAIL'
        self.controller.log_signal.emit('SW ver. verification on board {}: {}'.format(slave_model, res))

    def check_sw(self, need, current):
        for ver in need:
            if str(ver).upper() not in current.upper():
                self.controller.log_signal.emit('Software version {} not equal current version {}'.format(need, current))
                return False
        return True

    def verify_connections(self):
        self.controller.send_test_name('Connection DOBR', 'started')
        status = 'PASS'
        master = True if 'DOBR-M' in self.controller.send_com_command('axsh get MDL') else False
        slave = True if 'DOBR-S' in self.controller.send_com_command('send_msg -d 172.24.30.2 -c "axsh get mdl"') else False
        if not master or not slave:
            status = 'FAIL'
        self.controller.log_signal.emit("Verify connections to both SDR'S: {}".format(status))

    def get_ext_alarm(self):
        alarms = {}
        tmp = self.controller.send_com_command('get_ext_alarm.sh').split('\r\n')
        # re.search('(?<=\s=\s)(\d)(?=\s)', tmp)
        for i in tmp:
            if re.search(r'(EXT_ALM)', i) is None or i == '':
                continue
            alarms.update({re.search(r'(^\d)', i).group(): re.search(r'(\d$)', i).group()})
        print(alarms)
        return alarms

    def save_set_file(self):
        q = self.controller.send_msg('q', 'Cobham utils', 'Do you want to save set files?', 2)
        if q != QMessageBox.Ok:
            return
        self.controller.send_test_name('Save set file', 'started')
        self.controller.send_com_command('udp_bridge1 restart')
        self.controller.log_signal.emit("Starting udp_bridge")
        storm = Storm(controller=self.controller, bands=self.bands, bands_sn=self.bands_sn)
        for place, band in enumerate(self.bands):
            storm.save_setfile(place=place, band=band)
        self.controller.send_com_command('udp_bridge1 stop')
        self.controller.log_signal.emit("Stoping udp_bridge")

    def mute_test(self):
        self.controller.send_test_name('System mute', 'started')
        for band in range(1, len(self.bands) + 1):
            self.controller.log_signal.emit('Set band {} Transmission: Disable'.format(self.bands[band - 1]))
            self.controller.send_com_command('dobr_pa_control SET {} {}'.format(band, 0))

        # self.set_filters(0)

        answer = self.controller.send_msg('i', 'Mute test', 'Is all leds on the rf boards are RED?', 2)
        if answer == QMessageBox.Ok:
            status = 'PASS'
        else:
            status = 'FAIL'

        for band in range(1, len(self.bands) + 1):
            self.controller.log_signal.emit('Set band {} Transmission: Enable'.format(self.bands[band - 1]))
            self.controller.send_com_command('dobr_pa_control SET {} {}'.format(band, 1))
        self.set_filters(1)

    def set_filters(self, enable_filter):
        self.controller.send_test_name('Setting filters', 'started')
        val = 'ENABLE' if enable_filter == 1 else 'DISABLE'
        self.controller.log_signal.emit('Filters: {}'.format(val))
        # dobr_filters SET |band_index| |filter_num| |Tag| |Enable| |Tech| |DL_start_freq|
        #                  |DL_stop_freq| |DL_max_power| |DL_max_gain| |power_delta| |Gain_delta|
        for n, band in enumerate(self.bands):
            self.controller.log_signal.emit('Setting filter for {}'.format(band))
            conf_filter = self.filters.get(band)
            band_index = n + 1
            tech = 'GSM'
            center = float(conf_filter[0])
            bw = float(conf_filter[1])
            DL_start_freq = center - (bw / 2)
            DL_stop_freq = center + (bw / 2)

            res = self.controller.str_to_dict(self.controller.send_com_command('dobr_filters SET {} 1 1 {} {} {} {} 24 73 3 0'.
                              format(band_index, enable_filter, tech, DL_start_freq, DL_stop_freq)))
            self.controller.send_com_command('dobr_pa_control SET {} {}'.format(band_index, enable_filter))
            self.set_imop_status(n + 1, 0)

            self.controller.log_signal.emit('Set filter {}: {}'.format(band, res['DOBR FILTER'][0]['Status']))

    def set_imop_status(self, band, status):
        self.controller.send_com_command('imop_control SET {} {}'.format(band, status))

    def test_composite_power(self):
        self.controller.send_test_name('DL composite power test', 'started')
        test_status = True
        gen_calibr = self.controller.str_to_dict(self.db.get_gen_offset()[0])
        sa_calibr = self.controller.str_to_dict(self.db.get_sa_offset()[0])

        try:
            self.controller.send_msg('i', 'DL composite power test',
                'Connect Generator to Base, Spectrum to Mobile using attenuators 30 dB', 1)
            instr = Instruments(controller=self.controller)
            instr.genPreset()
            instr.saPreset()
            for n in range(1, len(self.bands) + 1):
                band_info = self.controller.str_to_dict(
                    self.controller.send_com_command('dobr_filters GET {} --json'.format(n)))
                band_name = list(band_info.keys())[0]
                start = float(band_info.get(band_name)[0].get('DL_start_freq'))
                stop = float(band_info.get(band_name)[0].get('DL_end_freq'))
                center = start + (stop - start) / 2
                if center in gen_calibr.keys():
                    gen_offset = gen_calibr.get(center)
                    sa_offset = sa_calibr.get(center)
                else:
                    gen_offset = gen_calibr.get(center - center % 5)
                    sa_offset = sa_calibr.get(center - center % 5)
                instr.sa.write("DISP:WIND:TRAC:Y:RLEV:OFFS {}".format(30 + sa_offset ))
                instr.sa.write(":SENSE:FREQ:center {} MHz".format(center))
                instr.gen.write(":FREQ:FIX {} MHz".format(center))
                instr.gen.write("POW:AMPL {} dBm".format(-60 + gen_offset))
                instr.gen.write(":OUTP:STAT ON")
                instr.sa.write(":CALC:MARK1:STAT ON")
                time.sleep(3)
                instr.sa.write("CALC:MARK1:MAX")
                time.sleep(1)
                gain = round(float(instr.sa.query("CALC:MARK1:Y?")), 2)
                if gain > 16 or gain < 10:
                    status = 'FAIL'
                    test_status = False
                else:
                    status = 'PASS'
                self.controller.log_signal.emit('{} DL composite power = {} dB : {}'.
                                                format(band_name, gain, status))
                instr.gen.write(":OUTP:STAT OFF")
            self.controller.log_signal.emit('DL composite power: {}'.format(self.controller.true_to_pass(test_status)))
            self.controller.send_test_name('DL composite power test', 'completed')
            # return
            # self.parent.result_table.append(['Reading DL COMPOSITE Power', test_status])
            # if not test_status:
            #     while True:
            #         q = input("Input R -> Retry; C -> Continue; X -> Break :")
            #         if q.upper() == 'R':
            #             self.test_composite_power()
            #         elif q.upper() == 'C':
            #             break
            #         elif q.upper() == 'X':
            #             self.parent.menu()
        except Exception as e:
            raise e

    def gpr_gps_test(self):
        self.controller.send_test_name('GPR & GPS', 'started')
        self.controller.send_msg('i', 'GPR & GPS', 'Connect GPS and GPR antenna, and insert sim card', 1)
        test_start = time.time()
        self.controller.log_signal.emit('Enable Remote and Modem Communication: {}'.format(self.set_remote_communication(1)))

        gde = int(self.controller.send_com_command('axsh GET CDE').split(' ')[0])
        gpr = int(self.controller.send_com_command('axsh GET GPR ENB'))
        apn = self.controller.send_com_command('axsh GET GPR APN').strip()

        if gde != 1 or gpr != 1 or apn != self.db.get_all_data('settings').get('apn_name'):
            self.controller.log_signal.emit('gpr_gps_test: initialisation FAIL')
            return
        else:
            self.controller.log_signal.emit('gpr_gps_test: initialisation PASS')

        while True:
            gps_status = False
            modem_status = False
            is_modem_printed = False
            is_gps_printed = False

            time_wait = int(self.db.get_all_data('settings').get('modem_timeout'))
            cur_time = time.time()
            delta_time = int(cur_time - test_start)
            if delta_time % 5 == 0:
                if int(self.controller.send_com_command('axsh GET GPR STATUS')) == 1 and not modem_status:
                    modem_status = True
                    if not is_modem_printed:
                        self.controller.log_signal.emit('Modem test: {}'.format(modem_status))
                        ip = self.get_ip_by_iface('wwan0')
                        self.controller.log_signal.emit('IP address: {}'.format(ip))
                        is_modem_printed = True

                tmp = self.controller.send_com_command('read_gps_coordinates.sh')
                gps_arr = self.controller.str_to_dict(tmp)['coordinates'][0]
                if gps_arr['x'] + gps_arr['y'] > 0 and not gps_status:
                    gps_status = True
                    if not is_gps_printed:
                        self.controller.log_signal.emit('GPS test: {}'.format(gps_status))
                        self.controller.log_signal.emit('Coordinates: {} : {}'.format(gps_arr['x'], gps_arr['y']))
                        is_gps_printed = True

                if gps_status and modem_status:
                    break
            if delta_time // 60 >= time_wait:
                modem_status = 'FAIL'
                break
            delta = float(test_start + time_wait * 60 - cur_time)
            self.controller.timer_signal.emit(delta)
            time.sleep(.5)
        self.controller.log_signal.emit('Disable Remote and Modem Communication: {}'.format(self.set_remote_communication(0)))
        self.controller.send_msg('i', 'GPR & GPS', 'Disconnect GPS and GPR antenna, and replace sim card', 1)

    def set_remote_communication(self, status):
        # Remote Communication:    axsh SET CDE 1
        # Enable Modem Connection: axsh SET GPR ENB 0
        # Check Modem Connection: asch GET GPR STATUS
        self.controller.send_com_command('axsh SET CDE {}'.format(status))
        self.controller.send_com_command('axsh SET GPR ENB {}'.format(status))
        if status == 1:
            self.controller.send_com_command('axsh SET GPR APN {}'.format(self.db.get_all_data('settings').get('apn_name')))
        else:
            self.controller.send_com_command("axsh SET GPR APN ''")

        comm = int(self.controller.send_com_command('axsh GET CDE'.format(status)).split(' ')[0])
        modem = int(self.controller.send_com_command('axsh GET GPR ENB'))
        test = [int(comm), int(modem)]
        apn = self.controller.send_com_command('axsh GET GPR APN').strip()

        if status == 0 and apn == '':
            test.append(0)
        if status == 1 and apn == self.db.get_all_data('settings').get('apn_name'):
            test.append(1)

        if status == 0 and sum(test) == 0:
            return True
        elif status == 1 and sum(test) == 3:
            return True
        else:
            return False

    def clear_log(self):
        # ToDO: make Cancel function
        self.controller.send_test_name('Clear log', 'started')
        logs = self.controller.send_com_command('alarms numoflogs --json')
        logs = self.controller.str_to_dict(logs)
        num_logs = logs.get('NumOfLogs')[0].get('NUM')
        self.controller.log_signal.emit('Found {} logs in system'.format(num_logs))
        if num_logs == '0':
            return
        self.controller.log_signal.emit('Deleting logs')
        self.controller.send_com_command('alarms logsclear')
        time.sleep(3)
        logs = self.controller.send_com_command('alarms numoflogs --json')
        logs = self.controller.str_to_dict(logs)
        num_logs = logs.get('NumOfLogs')[0].get('NUM')
        self.controller.log_signal.emit('Found {} logs in system'.format(num_logs))
        if num_logs != '0':
            q = self.controller.send_msg('w', 'Clear logs', 'Not all logs deleted.', 3)
            if q == QMessageBox.Retry:
                self.clear_log()
            elif q == QMessageBox.Cancel:
                return
            else:
                return

    def get_ip_by_iface(self, iface):
        tmp = self.controller.send_com_command("ifconfig {} | grep 'inet addr:' | cut -d: -f2".
                                               format(iface)).replace('Bcast', '')
        return tmp

    def set_ip(self):
        self.controller.send_test_name('Set static IP', 'started')
        ip = self.db.get_all_data('settings').get('ip')
        mask = self.db.get_all_data('settings').get('mask')
        tmp = re.search('^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}', mask).group(0)
        gtw = tmp + '254'
        # ToDo: check ip
        self.controller.send_com_command('axsh SET NIC eth0 STATIC {} {} {}'.format(ip, mask, gtw))
        self.controller.send_com_command('ifconfig eth0 {} netmask {} up'.format(ip, mask))
        curr_ip = self.controller.get_ip()
        if ip != curr_ip[1] or curr_ip[0] != 'STATIC':
            self.controller.send_msg('w', 'Cobham FuFu', 'Trying set static ip is FAIL', 1)
            for_return = False
        else:
            for_return = True
        self.controller.log_signal.emit('Setting static IP: {}'.format(self.controller.true_to_pass(for_return)))
        self.controller.send_test_name('Set static IP', 'completed')
        return for_return










