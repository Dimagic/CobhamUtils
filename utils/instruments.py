import visa
import time

from database.cobhamdb import CobhamDB


class Instruments:
    def __init__(self, **kwargs):
        self.controller = kwargs.get('controller')
        self.parent = kwargs.get('parent')
        self.sa = None
        self.gen = None
        try:
            self.rm = visa.ResourceManager()
            self.rm.timeout = 50000
        except Exception as e:
            self.controller.msg_signal.emit('w','Instrument initialisation error', str(e), 1)

    def getListInstrument(self):
        listRes = self.rm.list_resources()
        listNameRes = {}
        for i in listRes:
            instr = self.rm.open_resource(i, send_end=False)
            listNameRes.update({i: instr.query('*IDN?').split(',')[1].replace(' ', '')})
        return listNameRes

    def getInstr(self, val):
        listRes = self.rm.list_resources()
        for i in listRes:
            instr = self.rm.open_resource(i, send_end=False)
            currInstr = instr.query('*IDN?').split(',')[1].upper().replace(' ', '')
            if val.upper() == currInstr.upper():
                return instr
        return None

    def saPreset(self, **kwargs):
        self.sa = self.getInstr(CobhamDB().get_all_data('settings').get('combo_sa'))
        self.sa_send_cmd(":SYST:PRES")
        self.sa_send_cmd(":CAL:AUTO OFF")
        if kwargs.get('freq'):
            self.sa_send_cmd(":SENSE:FREQ:center {} MHz".format(kwargs.get('freq')))
        self.sa_send_cmd(":SENSE:FREQ:span 100 kHz")
        self.sa_send_cmd("DISP:WIND:TRAC:Y:RLEV:OFFS {}".format(CobhamDB().get_all_data('settings').get('atten_sa')))
        # self.sa_send_cmd(":BAND:VID 27 KHz")
        return self.sa

    def sa_calibration_settings(self, freq):
        span = 50
        self.sa_send_cmd(":CALC:MARK1:STAT ON")
        self.sa_send_cmd(":SENSE:FREQ:center {} MHz".format(freq+span/2))
        self.sa_send_cmd(":SENSE:FREQ:span {} MHz".format(span))
        self.sa_send_cmd("DISP:WIND:TRAC:Y:RLEV:OFFS 0")


    def sa_send_cmd(self, cmd):
        self.sa.write(cmd)
        time.sleep(.2)
        while int(self.sa.query("*OPC?")) != 1:
            time.sleep(.1)


    def sa_send_query(self, cmd):
        return self.sa.query(cmd)

    def get_gain_calibration(self, freq):
        self.gen.write(":FREQ:FIX {} MHz".format(freq))
        self.sa_send_cmd(self.sa_send_cmd(":CALC:MARK1:X {} MHz".format(freq)))
        gain = float(self.sa_send_query("CALC:MARK1:Y?"))
        print(gain)

    def genPreset(self, **kwargs):
        self.gen = self.getInstr(CobhamDB().get_all_data('settings').get('combo_gen'))
        self.gen.write("*RST")
        self.gen.write(":POW:OFFS -{} dB".format(CobhamDB().get_all_data('settings').get('atten_gen')))
        self.gen.write(":OUTP:STAT OFF")
        self.gen.write(":OUTP:MOD:STAT OFF")
        if kwargs.get('freq'):
            self.gen.write(":FREQ:FIX {} MHz".format(kwargs.get('freq')))
        return self.gen

    def setGenPow(self, need):
        span = self.parent.limitsAmpl.get('freqstop') - self.parent.limitsAmpl.get('freqstart')
        center = self.parent.limitsAmpl.get('freqstart') + span / 2
        self.sa_send_cmd(":SENSE:FREQ:center {} MHz".format(center))
        self.sa_send_cmd("DISP:WIND:TRAC:Y:RLEV:OFFS {}".format(self.getOffset()))
        self.sa_send_cmd(":POW:ATT 0")
        self.sa_send_cmd(":DISP:WIND:TRAC:Y:RLEV {}".format(float(self.getOffset()) - 10))
        genList = (self.gen)
        for curGen, freq in enumerate([center - 0.3,  + 0.3]):
            self.sa_send_cmd(":CALC:MARK1:STAT ON")
            self.sa_send_cmd(":CALC:MARK1:X {} MHz".format(freq))
            gen = genList[curGen]
            gen.write(":FREQ:FIX {} MHz".format(freq))
            gen.write("POW:AMPL -65 dBm")
            gen.write(":OUTP:STAT ON")
            time.sleep(1)
            self.setGainTo(gen=gen, need=need)
            gen.write(":OUTP:STAT OFF")
        self.gen.write(":OUTP:STAT ON")
        time.sleep(1)

    def setGainTo(self, gen, need):
        gain = float(self.sa.query("CALC:MARK1:Y?"))
        genPow = float(gen.query("POW:AMPL?"))
        acc = 0.1
        while not (gain - acc <= need <= gain + acc):
            if genPow >= 0:
                gen.write("POW:AMPL -65 dBm")
                self.gen.write(":OUTP:STAT OFF")
                input("Gain problem. Press enter for continue...")
                self.parent.menu()
            gen.write("POW:AMPL {} dBm".format(genPow))
            gain = float(self.sa.query("CALC:MARK1:Y?"))
            time.sleep(.1)
            delta = abs(need - gain)
            if delta <= 0.7:
                steep = 0.01
            elif delta <= 5:
                steep = 0.5
            elif delta <= 10:
                steep = 1
            else:
                steep = 5
            if gain < need:
                genPow += steep
            else:
                genPow -= steep

    def getOffset(self):
        try:
            offList = []
            span = self.parent.limitsAmpl.get('freqstop') - self.parent.limitsAmpl.get('freqstart')
            center = self.parent.limitsAmpl.get('freqstart') + span / 2
            f = open(self.config.getConfAttr('settings', 'calibrationFile'), "r")
            for line in f:
                off = line.strip().split(';')
                off[0] = float(off[0])/1000000
                offList.append(off)
            for n in offList:
                if n[0] <= center < n[0] + 70:
                    return n[1]
        except Exception as e:
            print(str(e))
            input('Calibration data file open error. Press enter for continue...')
            self.parent.menu()

    def check_instr(self):
        addr_gen = CobhamDB().get_all_data('settings').get('addr_gen')
        name_gen = CobhamDB().get_all_data('settings').get('combo_gen')
        addr_sa = CobhamDB().get_all_data('settings').get('addr_sa')
        name_sa = CobhamDB().get_all_data('settings').get('combo_sa')
        is_instrument_present = True
        list_instr = self.getListInstrument()
        print(list_instr, addr_sa)
        if addr_gen not in list_instr.keys() or list_instr.get(addr_gen) != name_gen:
            self.controller.log_signal_arg.emit("Generator {} not found".format(name_gen), -1)
            is_instrument_present = False
        if addr_sa not in list_instr.keys() or list_instr.get(addr_sa) != name_sa:
            self.controller.log_signal_arg.emit("Signal analyzer {} not found".format(name_sa), -1)
            is_instrument_present = False
        return is_instrument_present
