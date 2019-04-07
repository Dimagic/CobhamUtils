import os
import re
import socket
import threading
import time

import datetime
from sys import stdout

import pywinauto
from pywinauto import Application, application
from pywinauto.controls.win32_controls import ComboBoxWrapper
from pywinauto.timings import Timings

from database.cobhamdb import CobhamDB


class CheckStorm(threading.Thread):
    def __init__(self, group=None, target=None, name=None, kwargs=None):
        threading.Thread.__init__(self, group=group, target=target, name=name)
        self.app = kwargs['app']
        self.place = kwargs['place']
        self.band = kwargs['band']
        self.currTest = kwargs['currTest']
        self.controller = kwargs['controller']
        return

    def run(self):
        startTime = time.time()
        while True:

            tmp = application.findwindows.find_windows(title=u'StormInterface.exe')
            dialog = application.findwindows.find_windows(title=u'Save As')
            # stdout.write('\rSaving set file for band {}: {}'.format(self.band, str(delta)))
            time.sleep(.5)
            if len(tmp) > 0:
                window = self.app.Dialog
                button = window.Button
                button.Click()
                self.app.kill()
                self.currTest(self.place, self.band)
                break
            if len(dialog) > 0:
                break


class Storm:
    def __init__(self, controller, bands, bands_sn):
        self.controller = controller
        self.parent = self.controller.curr_parent
        Timings.window_find_timeout = 60
        self.count_bands = 0
        self.settings = self.controller.settings
        self.stormpath = self.settings.get('storm_path')
        self.bands = bands
        self.bands_sn = bands_sn
        if self.settings.get('storm_dynip') == '1':
            self.conn_rem_ip = self.parent.w_main.ip_lbl.text()
            self.conn_loc_ip = self.get_self_ip()
        elif self.settings.get('storm_statip') == '1':
            self.conn_rem_ip = self.parent.w_main.ip_lbl.text()
            self.conn_loc_ip =  self.settings.get('ip')
        elif self.settings.get('storm_usbip') == '1':
            self.conn_rem_ip = '192.168.152.1'
            self.conn_loc_ip = '192.168.152.2'

    def get_self_ip(self):
        sys_ip = re.search('^[0-9]{1,3}[.]', self.conn_rem_ip).group(0)
        return (([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if ip.startswith(sys_ip)] or [
            [(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in
             [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) + ["no IP found"])[0]

    def save_setfile(self, place, band):
        app, wnd_main = self.run_storm()
        if None in (app, wnd_main):
            self.controller.send_msg('w', 'Error', "Can't start StormInterface", 1)
            return
        check = CheckStorm(kwargs={'currTest': self, 'app': app, 'place': place,
                                   'band': band, 'controller': self.controller})
        check.start()
        if place <= 1:
            port = '30000'
        else:
            port = '30001'
        ComboBoxWrapper(wnd_main[u'Port ConnectionComboBox']).select('UDP')
        wnd_main[u'Local addEdit'].set_text(self.conn_loc_ip)
        wnd_main[u'Local portEdit'].set_text(port)
        wnd_main[u'Remote addEdit'].set_text(self.conn_rem_ip)
        wnd_main[u'Remote portEdit'].set_text(port)
        wnd_main[u'Rx Address:Edit'].set_text(band)
        ComboBoxWrapper(wnd_main[u'Rx Address:ComboBox']).select(band)
        wnd_main[u'Connect'].click()
        wnd_main.wait('ready')
        time.sleep(1)
        if not self.is_connected(wnd_main=wnd_main):
            self.controller.log_signal.emit('Connection fail. Reconnect')
            self.save_setfile(place, band)
        wnd_main[u'Create SetFile'].click()
        self.save_file(band)
        try:
            wnd_main.wait('ready')
        except pywinauto.findwindows.ElementAmbiguousError:
            getAnswer = False
            while not getAnswer:
                window = app.Dialog
                msg = window[u'Static2'].window_text()
                if msg != u'Finished to create setfile':
                    app.kill()
                else:
                    getAnswer = True
                window[u'OK'].click()
        wnd_main[u'Disconnect'].click()
        self.controller.log_signal.emit('Save set file for band {} - OK'.format(band))
        self.count_bands += 1
        if self.count_bands == len(self.bands):
            app.kill()

    def save_file(self, band):
        article = self.parent.w_main.art_lbl.text()
        revision = self.parent.w_main.rev_lbl.text()
        asis = self.parent.w_main.asis_lbl.text()
        file_name = '{}_{}'.format(band, self.bands_sn.get(band))
        path = self.parent.wk_dir + '\\!Backup\\' + article + '\\' + 'Rev_{}'.format(revision) + '\\' + asis + '\\'
        try:
            if not os.path.exists(self.parent.wk_dir + '\\!Backup\\'):
                os.mkdir(self.parent.wk_dir + '\\!Backup\\')
            if not os.path.exists(self.parent.wk_dir + '\\!Backup\\' + article + '\\'):
                os.mkdir(self.parent.wk_dir + '\\!Backup\\' + article + '\\')
            if not os.path.exists(self.parent.wk_dir + '\\!Backup\\' + article + '\\' + 'Rev_{}'.format(revision) + '\\'):
                os.mkdir(self.parent.wk_dir + '\\!Backup\\' + article + '\\' + 'Rev_{}'.format(revision) + '\\')
            if not os.path.exists(path):
                os.mkdir(path)
        except Exception as e:
            raise e


        while len(application.findwindows.find_windows(title=u'Save As')) == 0:
            time.sleep(1)
        try:
            app = Application().connect(title=u'Save As')
            wnd_save = app.Dialog
            wnd_save[u'Edit'].set_text(path + file_name)
            wnd_save.wait('ready')
            while len(application.findwindows.find_windows(title=u'Save As')) != 0:
                wnd_save.set_focus()
                wnd_save[u'&SaveButton'].click()
                time.sleep(1)
        except Exception as e:
            raise e

    def is_connected(self, wnd_main):
        if wnd_main[u'Button3'].texts()[0] == 'Disconnect':
            return True

    def run_storm(self):
        app, Wnd_Main = None, None
        try:
            app = Application().connect(title_re="StormInterface")
            Wnd_Main = app.window(title_re="StormInterface")
            Wnd_Main.wait('ready')
        except:
            app = Application().start(self.stormpath)
            Wnd_Main = app.window(title_re="StormInterface")
            Wnd_Main.wait('ready')
        finally:
            return app, Wnd_Main




