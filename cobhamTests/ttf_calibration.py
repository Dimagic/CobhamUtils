import ast
import time

from utils.instruments import Instruments


class TtfCalibrate:
    def __init__(self, controller):
        self.controller = controller
        self.test_status = 'PASS'
        self.instr = Instruments(controller=self.controller)
        self.instr.genPreset()
        self.instr.saPreset()
        # {band_number: [UL, DL]}
        self.band_fft = {1: [2, 3], 2: [0, 1], 3: [6, 7], 4: [4, 5]}
        # {DL center: UL center}
        self.uldl_table = {742.5: 707, 878: 833, 1962.5: 1882.5, 2145: 1745, 2355: 2310,
                           806: 847, 942.5: 897.5, 1842.5: 1747.5, 2140: 1950, 2655: 2535}

    def run_calibrate(self):
        band_info = self.controller.str_to_dict(
            self.controller.send_com_command('dobr_filters GET {} --json'.format(n)))
        band_name = list(band_info.keys())[0]
        start = float(band_info.get(band_name)[0].get('DL_start_freq'))
        stop = float(band_info.get(band_name)[0].get('DL_end_freq'))
        center = start + (stop - start) / 2
        for uldl in [1, 0]:
            band_info = self.parent.utils.get_band_info(band_number=1)
            if uldl == 0:
                self.controller.send_msg('i', 'TTF calibration',
                                         'Connect Spectrum to Base, Generator to Mobile using attenuators 30 dB', 1)
                center_freq = self.uldl_table[band_info['center']]
            if uldl == 1:
                self.controller.send_msg('i', 'TTF calibration',
                                         'Connect Generator to Base, Spectrum to Mobile using attenuators 30 dB', 1)
                center_freq = band_info['center']
            self.utils.wait_peak(center_freq)

            for band_number, band_name in enumerate(self.utils.get_bands()):
                self.get_peak(band_number=band_number + 1, uldl=uldl)
        self.parent.result_table.append(['Setting Spectrum Power Factor', self.test_status])

    def get_peak(self, band_number, uldl):
        try:
            band_info = self.parent.utils.get_band_info(band_number=band_number)
            if uldl == 0:
                uldl_name = 'Uplink'
                center_freq = self.uldl_table[band_info['center']]
            else:
                uldl_name = 'Downlink'
                center_freq = band_info['center']

            self.sa.write(":SENSE:FREQ:center {} MHz".format(center_freq))
            self.gen.write(":FREQ:FIX {} MHz".format(center_freq))
            self.gen.write("POW:AMPL -60 dBm")
            self.gen.write(":OUTP:STAT ON")
            self.utils.send_command('axsh', 'SET fft {} -195'.format(self.band_fft[band_number][uldl])).strip()
            time.sleep(1)
            tmp_gain = self.utils.send_command('fft.lua', self.band_fft[band_number][uldl])
            res = ast.literal_eval(tmp_gain)
            curr_fft = (int(max(res['data'])) + 60) * (-1)
            self.utils.send_command('axsh', 'SET fft {} {}'.format(self.band_fft[band_number][uldl], curr_fft)).strip()
            time.sleep(1)
            res = ast.literal_eval(tmp_gain)
            fft = self.utils.send_command('axsh', 'GET fft {}'.format(self.band_fft[band_number][uldl])).strip()
            gain = int(fft) + int(max(res['data']))
            print('{0:10}{1:10} FFT = {2:3} Gain = {3:3}'.format(band_info['name'], uldl_name, fft, gain))
            fft_delta = abs(202 - abs(curr_fft))
            if fft_delta > 10:
                self.test_status = 'FAIL'
            self.gen.write(":OUTP:STAT OFF")
        except Exception as e:
            print('Get peak error, retrying: {}'.format(e))
            self.get_peak(band_number, uldl)








