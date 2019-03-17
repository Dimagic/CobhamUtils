import ast
import re
import time

from PyQt5.QtWidgets import QMessageBox

from utils.instruments import Instruments


class TtfCalibrate:
    def __init__(self, controller, bands):
        self.controller = controller
        self.bands = bands
        self.test_status = 'PASS'
        self.instr = Instruments(controller=self.controller)
        self.instr.genPreset()
        self.instr.saPreset()
        # {band_number: [UL, DL]}
        self.band_uldl = {}
        self.band_fft = {1: [2, 3], 2: [0, 1], 3: [6, 7], 4: [4, 5]}

    def run_calibrate(self):
        self.controller.send_test_name('FFT calibration', 'started')
        all_bands = self.controller.str_to_dict(self.controller.send_com_command('bands --json')).get('bands')

        for n, band in enumerate(self.bands):
            n = n + 1
            band_info = self.controller.str_to_dict(
                self.controller.send_com_command('dobr_filters GET {} --json'.format(n)))
            band_name = list(band_info.keys())[0]
            band_name_freq = re.search('(\d){3,4}', band_name).group(0)
            start = float(band_info.get(band_name)[0].get('DL_start_freq'))
            stop = float(band_info.get(band_name)[0].get('DL_end_freq'))
            dl_center = start + (stop - start) / 2
            for band in all_bands:
                if band.get('Band') == band_name_freq:
                    apac = int(band.get('APAC'))
                    duplex = int(band.get('Duplex'))/1000000
                    if apac == 1:
                        ul_center = dl_center - duplex
                    elif apac == 0:
                        ul_center = dl_center + duplex
                    else:
                        raise ValueError()
                    self.band_uldl.update({n: [ul_center, dl_center]})
        q = self.controller.send_msg('i', 'FFT calibration',
                                     'Connect Generator to Base, Spectrum to Mobile using attenuators 30 dB', 1)
        if q == QMessageBox.Ok:
            for i in self.band_uldl.keys():
                self.get_peak(i, 1)
        q = self.controller.send_msg('i', 'FFT calibration',
                                     'Connect Spectrum to Base, Generator to Mobile using attenuators 30 dB', 1)
        if q == QMessageBox.Ok:
            for i in self.band_uldl.keys():
                self.get_peak(i, 0)
        self.controller.log_signal.emit('FFT calibration: {}'.format(self.test_status))
        self.controller.send_test_name('FFT calibration', 'completed')


    def get_peak(self, band_number, uldl):
        try:
            if uldl == 0:
                uldl_name = 'Uplink'
            else:
                uldl_name = 'Downlink'

            center_freq = self.band_uldl.get(band_number)[uldl]

            self.instr.sa.write(":SENSE:FREQ:center {} MHz".format(center_freq))
            self.instr.gen.write(":FREQ:FIX {} MHz".format(center_freq))
            self.instr.gen.write("POW:AMPL {} dBm".format(-60 + self.instr.get_offset(center_freq)))
            self.instr.gen.write(":OUTP:STAT ON")
            self.controller.send_com_command('axsh SET fft {} -195'.format(self.band_fft[band_number][uldl]))
            time.sleep(1)
            tmp_gain = self.controller.send_com_command('fft.lua {}'.format(self.band_fft[band_number][uldl])).strip()
            res = ast.literal_eval(tmp_gain)
            curr_fft = (int(max(res['data'])) + 60) * (-1)
            self.controller.send_com_command('axsh SET fft {} {}'.format(self.band_fft[band_number][uldl], curr_fft))
            time.sleep(1)
            res = ast.literal_eval(tmp_gain)
            fft = self.controller.send_com_command('axsh GET fft {}'.format(self.band_fft[band_number][uldl])).strip()
            gain = int(fft) + int(max(res['data']))

            fft_delta = abs(202 - abs(curr_fft))
            if fft_delta > 10:
                self.test_status = 'FAIL'
            self.controller.log_signal.emit('{} {} FFT = {} Gain = {} '.format(res.get('band'), uldl_name, fft, gain))
            self.instr.gen.write(":OUTP:STAT OFF")
        except:
            self.controller.log_signal.emit('Get peak error, retrying')
            self.get_peak(band_number, uldl)








