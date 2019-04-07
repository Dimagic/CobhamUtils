import configparser


class Config:
    def __init__(self, parent):
        self.parent = parent
        self.config = configparser.ConfigParser()
        self.configFile = './config.ini'
        self.section = 'SETTINGS_BACKUP'

    def cfg_write(self, settings):
        try:
            tmp = {}
            for key in settings.keys():
                tmp.update({key: settings.get(key)[0]})
            self.config[self.section] = tmp
            with open(self.configFile, 'w') as configfile:
                self.config.write(configfile)
                self.parent.send_msg('i', 'Import settings', 'Export settings complete', 1)
        except Exception as e:
            self.parent.send_msg('w', 'Export error', str(e), 1)


    def cfg_read(self, **kwargs):
        try:
            file = kwargs.get('file')
            section = kwargs.get('section')
            if not file:
                file = self.configFile
            if not section:
                section = self.section
            tmp = {}
            self.config.read(file, encoding='utf-8-sig')
            for i in self.config[section]:
                if section != "SETTINGS_BACKUP":
                    i = i.upper()
                tmp.update({i: self.config.get(section, i)})
            return tmp
        except Exception as e:
            self.parent.send_msg('w', 'Import error', str(e), 1)
            return None


    # def get_section(self, section):
    #     try:
    #         tmp = {}
    #         for i in self.config.items(section):
    #             tmp.update(dict([i]))
    #         return tmp
    #     except Exception as e:
    #         self.parent.send_msg('w', 'Get section error', str(e), 1)