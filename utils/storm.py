import os
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
            currTime = time.time()
            delta = float(currTime - startTime)
            tmp = application.findwindows.find_windows(title=u'StormInterface.exe')
            dialog = application.findwindows.find_windows(title=u'Save As')
            # stdout.write('\rSaving set file for band {}: {}'.format(self.band, str(delta)))
            self.controller.timer_signal.emit(delta)
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
        self.parent = self.controller.get_parent()
        Timings.window_find_timeout = 60
        self.count_bands = 0
        self.settings = self.controller.settings
        self.stormpath = self.settings.get('storm_path')
        self.bands = bands
        self.bands_sn = bands_sn
        self.conn_loc_ip = '192.168.1.2'
        self.conn_rem_ip = '192.168.1.253'

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
        serial = self.parent.w_main.ser_lbl.text()
        file_name = '{}_{}'.format(band, self.bands_sn.get(band))
        path = self.parent.wk_dir + '\\!Backup\\' + article + '\\' + 'Rev_{}'.format(revision) + '\\' + serial + '\\'
        try:
            os.stat(path)
        except:
            try:
                os.mkdir(self.parent.wk_dir + '\\!Backup\\')
            except:
                os.mkdir(self.parent.wk_dir + '\\!Backup\\' + article + '\\')
                try:
                    os.mkdir(path)
                except:
                    os.mkdir(self.parent.wk_dir + '\\!Backup\\' + article + '\\' + 'Rev_{}'.format(revision) + '\\')
                    try:
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




