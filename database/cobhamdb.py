import numpy
import time
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey, create_engine, Text, Float
from sqlalchemy_utils import database_exists, create_database

# Global Variables
SQLITE = 'sqlite'

# Table Names
USERS = 'users'
TESTTYPE = 'test_type'
TESTJOURNAL = 'test_journal'
TESTS = 'tests'
PASSFAIL = 'passfail'
SETTINGS = 'settings'
INSTRUMENTS = 'instruments'
CALIBRATION = 'calibr'
IDOBR_RF = 'idobr_rf'
IDOBR_RF_TYPE = 'idobr_rf_type'
IDOBR_TYPE = 'idobr_type'
SDR_TYPE = 'sdr_type'
IDOBR = 'idobr'
SDR = 'sdr'

class CobhamDB:
    def __init__(self):
        db_path = "sqlite:///cobham_db.db"
        self.db_engine = create_engine(db_path)
        if not database_exists(self.db_engine.url):
            self.create_db()

    def create_db(self):
        create_database(self.db_engine.url)
        self.create_db_tables()

    def create_db_tables(self):
        print("Create tables")
        metadata = MetaData()
        test_type = Table(TESTTYPE, metadata,
                         Column('id', Integer, primary_key=True),
                         Column('test_type', String, nullable=False, unique=True)
                         )

        test_journal = Table(TESTJOURNAL, metadata,
                             Column('id', Integer, primary_key=True),
                             Column('user_id', None, ForeignKey('users.id')),
                             Column('date', String),
                             Column('system_id', None, ForeignKey('idobr.asis'))
                             )

        tests = Table(TESTS, metadata,
                      Column('id', Integer, primary_key=True),
                      Column('test_type_id', None, ForeignKey('test_type.id')),
                      Column('status', String)
                      )

        users = Table(USERS, metadata,
                      Column('id', Integer, primary_key=True),
                      Column('name', String),
                      )

        settings = Table(SETTINGS, metadata,
                         Column('id', Integer, primary_key=True),
                         Column('param', String, nullable=False, unique=True),
                         Column('value', String)
                         )

        calibr = Table(CALIBRATION, metadata,
                          Column('id', Integer, primary_key=True),
                          Column('cable', Float),
                          Column('gen2sa', Float),
                          Column('sa2gen', Float)
                          )

        idobr_rf_type = Table(IDOBR_TYPE, metadata,
                         Column('id', Integer, primary_key=True),
                         Column('type', String, nullable=False, unique=True),
                         )

        idobr_type = Table(IDOBR_RF_TYPE, metadata,
                              Column('id', Integer, primary_key=True),
                              Column('type', String, nullable=False, unique=True),
                              )

        sdr_type = Table(SDR_TYPE, metadata,
                           Column('id', Integer, primary_key=True),
                           Column('type', String, nullable=False, unique=True),
                           )

        idobr_rf = Table(IDOBR_RF, metadata,
                         Column('id', Integer, primary_key=True),
                         Column('type', None, ForeignKey('idobr_rf_type.type')),
                         Column('asis', String, nullable=False, unique=True),
                         )

        sdr = Table(SDR, metadata,
                         Column('id', Integer, primary_key=True),
                         Column('type', None, ForeignKey('sdr_type.type')),
                         Column('rf_1', None, ForeignKey('idobr_rf.asis')),
                         Column('rf_2', None, ForeignKey('idobr_rf.asis')),
                         Column('asis', String, nullable=False, unique=True),
                         )

        idobr = Table(IDOBR, metadata,
                         Column('id', Integer, primary_key=True),
                         Column('type', None, ForeignKey('idobr_type.type')),
                         Column('master_sdr', None, ForeignKey('sdr.asis')),
                         Column('slave_sdr', None, ForeignKey('sdr.asis')),
                         Column('sn', String, nullable=False, unique=True),
                         Column('asis', String, nullable=False, unique=True),
                         )

        try:
            metadata.create_all(self.db_engine)
            print("Tables created")
        except Exception as e:
            raise e

    # Insert, Update, Delete
    def execute_query(self, query=''):
        if query == '': return
        with self.db_engine.connect() as connection:
            try:
                connection.execute(query)
            except Exception as e:
                raise e

    def update_query(self, query=''):
        if query == '': return
        with self.db_engine.connect() as connection:
            try:
                connection.execute(query)
            except Exception as e:
                raise e

    def select_query(self, query=''):
        if query == '': return
        with self.db_engine.connect() as connection:
            try:
                s = []
                for val in connection.execute(query):
                    s.append(val)
                return s
            except Exception as e:
                raise e

    def set_test_type(self, test_type):
        q = self.select_query("SELECT test_type FROM test_type WHERE test_type = '{}' LIMIT 1".format(test_type))
        if len(q) == 0:
            self.execute_query("INSERT INTO test_type (test_type) VALUES ('{}')".format(test_type))
            self.set_test_type(test_type)
        else:
            self.execute_query("create table if not exists test_{} ("
                               "id integer PRIMARY KEY,"
                               "system_asis text NOT NULL,"
                               "date_test text NOT NULL,"
                               "meas text NOT NULL,"
                               "status text NOT NULL,"
                               "FOREIGN KEY (system_asis) REFERENCES idobr (asis)"
                               ")".format(test_type))
            return q[0][0]
    # ToDo:test result
    # def set_test_result(self, **kwargs):
    #     table = kwargs.get('test_type')
    #     asis = kwargs.get('asis')
    #     date_test = kwargs.get('date_test')
    #     meas = kwargs.get('test_name')
    #     status = kwargs.get('status')
    #     self.execute_query("INSERT INTO test_{} (system_asis, date_test, meas, status) VALUES ('{}', '{}', '{}', '{}')".
    #                        format(table, asis, date_test, test_name, status))

    def get_settings_by_name(self, val):
        tmp = self.get_all_data('settings')
        return tmp.get(val)

    def clear_calibration(self):
        self.execute_query("UPDATE settings SET last_calibr = ''")
        self.execute_query("DELETE FROM {}".format(CALIBRATION))

    def set_calibration(self, calibr):
        for i in calibr.keys():
            val = calibr.get(i)
            self.execute_query("INSERT OR REPLACE INTO calibr "
                               "(id, gen2sa, sa2gen) values "
                               "({}, {}, {})".format(i, val.get('gen2sa'), val.get('sa2gen')))
        self.execute_query("UPDATE settings SET last_calibr = {}".format(time.strftime("%Y-%m-%d", time.gmtime())))

    def get_offset(self, freq):
        offset = {}
        steep = float(self.get_settings_by_name('cal_steep'))
        freq = float(freq)
        start = freq - freq % steep
        stop = start + steep
        try:
            start_offset = self.select_query("SELECT * FROM calibr WHERE id = {}".format(start))[0]
            stop_offset = self.select_query("SELECT * FROM calibr WHERE id = {}".format(stop))[0]
            # offset_cable = {'start': start_offset[1], 'stop': stop_offset[1]}
            offset_gen = {'start': start_offset[2], 'stop': stop_offset[2]}
            offset_sa = {'start': start_offset[3], 'stop': stop_offset[3]}
            tmp = {'gen': offset_gen, 'sa': offset_sa}
            for i in tmp.keys():
                if tmp.get(i).get('start') == tmp.get(i).get('stop'):
                    offset.update({i: float(tmp.get(i).get('start'))})
                else:
                    offset_list = self.calculate_offset(val=tmp.get(i))
                    n = int(round(divmod(freq, 2)[1], 2)*100)
                    offset.update({i: round(offset_list[n], 2)})
            return offset
        except:
            raise ValueError('Calibration data from generator on frequency {} MHz not found'.format(freq))

    @staticmethod
    def calculate_offset(val):
        start = float(val.get('start'))
        stop = float(val.get('stop'))
        range_offset = stop - start
        if range_offset < 0:
            tmp = numpy.arange(stop + range_offset / 100, start, abs(range_offset) / 100)
            tmp = tmp[::-1]
        else:
            tmp = numpy.arange(start, stop, range_offset / 100)
        return tmp

    def save_settings(self, setdict):
        self.execute_query("DELETE FROM {}".format(SETTINGS))
        for key in setdict.keys():
            val = setdict.get(key)
            s = self.select_query("SELECT value FROM settings WHERE param = '{}'".format(key))
            if len(s) == 0:
                self.execute_query("INSERT INTO settings (param, value) VALUES ('{}', '{}')".format(key, val))
            else:
                self.execute_query("UPDATE settings SET value = '{}' WHERE param = '{}'".format(val, key))

    def get_all_data(self, table='', query=''):
        query = query if query != '' else "SELECT * FROM '{}';".format(table)
        for_return = {}
        with self.db_engine.connect() as connection:
            try:
                result = connection.execute(query)
            except Exception as e:
                raise e
            else:
                for row in result:
                    for_return.update({row[1]: row[2]})
                result.close()
        return for_return

    def get_port_baud(self):
        port = self.select_query("SELECT value FROM settings WHERE param = 'combo_com'")[0]
        baud = self.select_query("SELECT value FROM settings WHERE param = 'combo_baud'")[0]
        return {'port': port[0], 'baud': baud[0]}


    def get_idobr_rf_type(self, type):
        q = self.select_query("SELECT type FROM idobr_rf_type WHERE type = '{}' LIMIT 1".format(type))
        if len(q) == 0:
            self.execute_query("INSERT INTO idobr_rf_type (type) VALUES ('{}')".format(type))
            q = self.select_query("SELECT type FROM idobr_rf_type WHERE type = '{}' LIMIT 1".format(type))
            q = q[0][0]
        else:
            q = q[0][0]
        print(q)
        return q

    def set_idobr_rf(self, type, asis):
        q = self.get_idobr_rf_type(type)
        if q != type:
            print(q, type)
        try:
            self.execute_query("INSERT INTO idobr_rf (type, asis) VALUES ('{}', '{}')".format(q, asis))
        except Exception as e:
            print(e)

    def get_idobr_rf(self, asis):
        q = self.select_query("SELECT type FROM idobr_rf WHERE asis = '{}' LIMIT 1".format(asis))
        if len(q) == 0:
            return None
        return q

    def set_sdr(self, type, asis, rf_list):
        q = self.select_query("SELECT type FROM sdr_type WHERE type = '{}' LIMIT 1".format(type))
        if len(q) == 0:
            self.execute_query("INSERT INTO sdr_type (type) VALUES ('{}')".format(type))
            q = self.select_query("SELECT type FROM sdr_type WHERE type = '{}' LIMIT 1".format(type))
        try:
            rf_1 = list(rf_list.values())[0]
            rf_2 = list(rf_list.values())[1]
            self.execute_query("INSERT INTO sdr (type, asis, rf_1, rf_2) VALUES ('{}', '{}', '{}', '{}')".
                               format(q[0][0], asis, rf_1, rf_2))
        except Exception as e:
            print(e)

    def set_idobr(self, assembly):
        # print(assembly)
        idobr = assembly.get('idobr')
        rf_master = assembly.get('rf_master')
        rf_slave = assembly.get('rf_slave')

        for key in rf_master.keys():
            q = self.get_idobr_rf_type(key)
            if q != key:
                print('ERROR: create rf type: {}'.format(key))

        for key in rf_slave.keys():
            q = self.get_idobr_rf_type(key)
            if q != key:
                print('ERROR: create rf type: {}'.format(key))

        for key in assembly.get('rf_master'):
            self.set_idobr_rf(key, rf_master.get(key))
        for key in assembly.get('rf_slave'):
            self.set_idobr_rf(key, rf_slave.get(key))

        self.set_sdr(assembly.get('master_sdr').get('type'), assembly.get('master_sdr').get('asis'), rf_master)
        self.set_sdr(assembly.get('slave_sdr').get('type'), assembly.get('slave_sdr').get('asis'), rf_slave)

        q = self.select_query("SELECT type FROM idobr_type WHERE type = '{}' LIMIT 1".format(idobr.get('type')))
        if len(q) == 0:
            self.execute_query("INSERT INTO idobr_type (type) VALUES ('{}')".format(idobr.get('type')))
            q = self.select_query("SELECT type FROM idobr_type WHERE type = '{}' LIMIT 1".format(idobr.get('type')))
        try:
            q = q[0][0]
            self.execute_query("INSERT INTO idobr (type, master_sdr, slave_sdr, asis) VALUES ('{}', '{}', '{}', '{}')".
                               format(q, assembly.get('master_sdr').get('asis'),
                                      assembly.get('slave_sdr').get('asis'), idobr.get('asis')))
            return True
        except Exception as e:
            print(e)
            return False



