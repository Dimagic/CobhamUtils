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

        idobr_rf = Table(IDOBR_RF, metadata,
                         Column('id', Integer, primary_key=True),
                         Column('type', String, nullable=False),
                         Column('asis', String, nullable=False, unique=True),
                         )

        sdr = Table(SDR, metadata,
                         Column('id', Integer, primary_key=True),
                         Column('type', String, nullable=False),
                         Column('rf_1', None, ForeignKey('idobr_rf.asis')),
                         Column('rf_2', None, ForeignKey('idobr_rf.asis')),
                         Column('asis', String, nullable=False, unique=True),
                         )

        idobr = Table(IDOBR, metadata,
                         Column('id', Integer, primary_key=True),
                         Column('type', String, nullable=False),
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
                               "meas_name text NOT NULL,"
                               "meas_func text NOT NULL,"
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
        self.execute_query("UPDATE settings SET value = '' where param = 'last_calibr'")
        self.execute_query("DELETE FROM {}".format(CALIBRATION))

    def set_calibration(self, calibr):
        for i in calibr.keys():
            val = calibr.get(i)
            self.execute_query("INSERT OR REPLACE INTO calibr "
                               "(id, gen2sa, sa2gen) values "
                               "({}, {}, {})".format(i, val.get('gen2sa'), val.get('sa2gen')))
        self.execute_query("UPDATE settings SET value = '{}' where param = 'last_calibr'".
                           format(time.strftime("%Y-%m-%d", time.gmtime())))

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
                    try:
                        n = int(round(divmod(freq, 2)[1], 2)*100)
                        offset.update({i: round(offset_list[n], 2)})
                    except:
                        n = int(round(divmod(freq, 1)[1], 2) * 100)
                        offset.update({i: round(offset_list[n], 2)})
            return offset
        except Exception as e:
            print(e)
            raise ValueError('Calibration data on frequency {} MHz not found'.format(freq))

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

    def get_idobr_assembly(self, asis):
        assembly = {}
        keys = ['sdr_type', 'sdr_asis', 'rf_asis', 'rf_type', 'idobr_type', 'idobr_sn', 'idobr_asis']
        query = "select * from ("
        for i in [1, 2]:
            for j in ['master', 'slave']:
                q_row = "select sdr.type, sdr.asis, sdr.rf_{} as rf_asis," \
                        " idobr_rf.type as rf_type, idobr.type as sys_type, " \
                        "idobr.sn, idobr.asis as sys_asis from sdr " \
                        "inner join idobr_rf on sdr.rf_{} = idobr_rf.asis " \
                        "inner join idobr on idobr.{}_sdr = sdr.asis\nunion all\n".format(i, i, j)
                query = query + q_row
        query = query + ")\nwhere sys_asis = '{}'".format(asis)
        query = query.replace('union all\n)', ')')
        for m, i in enumerate(self.select_query(query)):
            for k, j in enumerate(i):
                if keys[k] in ['sdr_type', 'sdr_asis'] and m > 1:
                    continue
                if 'idobr_' in keys[k]:
                    key = keys[k]
                else:
                    key = "{}_{}".format(keys[k], m + 1)
                assembly.update({key: j})
        return assembly

    def get_idobr_by_asis(self, asis):
        assembly = {}
        rows = 'asis,type,sn,master_sdr,slave_sdr'
        rows_list = rows.split(',')
        tmp = self.select_query("SELECT {} FROM idobr WHERE asis = '{}'".format(rows, asis))
        if len(tmp) == 0:
            return
        else:
            tmp = tmp[0]
        for i, j in enumerate(rows_list):
            assembly.update({j: tmp[i]})
        return assembly

    def get_sdr_by_asis(self, asis):
        keys = "type,rf_1,rf_2"
        for_return = {}
        q = self.select_query("select {} from sdr where asis = '{}'".format(keys, asis))[0]
        for i, j in enumerate(keys.split(',')):
            for_return.update({j: q[i]})
        return for_return

    def get_idobr_by_sn(self, sn):
        tmp = self.select_query("SELECT asis, type, sn, master_sdr, slave_sdr "
                                "FROM idobr WHERE sn = '{}'".format(sn))
        if len(tmp) == 0:
            return
        else:
            tmp = tmp[0]
        return {'asis': tmp[0], 'type': tmp[1], 'sn': tmp[2], 'master_sdr': tmp[3], 'slave_sdr': tmp[4]}

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


    def set_idobr_rf(self, type, asis):
        if self.get_idobr_rf(asis) is None:
            self.execute_query("INSERT INTO idobr_rf (type, asis) VALUES ('{}', '{}')".format(type, asis))


    def get_idobr_rf(self, asis):
        q = self.select_query("SELECT type FROM idobr_rf WHERE asis = '{}' LIMIT 1".format(asis))
        print("rf -> {}".format(q))
        if len(q) == 0:
            return None
        return q

    def set_sdr(self, **kwargs):
        try:
            sdr_type = kwargs.get("sdr_type")
            sdr_asis = kwargs.get("sdr_asis")
            rf_1 = list(kwargs.get("rf_list"))[0]
            rf_2 = list(kwargs.get("rf_list"))[1]
            self.execute_query("INSERT INTO sdr (type, asis, rf_1, rf_2) VALUES ('{}', '{}', '{}', '{}')".
                               format(sdr_type, sdr_asis, rf_1, rf_2))
        except Exception as e:
            print(e)

    def set_idobr_assembly(self, assembly):
        idobr_type = assembly.get("idobr_type")
        idobr_asis = assembly.get("idobr_asis")
        idobr_sn = assembly.get("idobr_sn")
        for i in range(1,5):
            rf_type = assembly.get("rf_type_{}".format(i))
            rf_asis = assembly.get("rf_asis_{}".format(i))
            self.set_idobr_rf(rf_type, rf_asis)
        for i in [1, 2]:
            sdr_type = assembly.get("sdr_type_{}".format(i))
            sdr_asis = assembly.get("sdr_asis_{}".format(i))
            if i == 1:
                rf_1 = assembly.get("rf_asis_{}".format(1))
                rf_2 = assembly.get("rf_asis_{}".format(2))
            else:
                rf_1 = assembly.get("rf_asis_{}".format(3))
                rf_2 = assembly.get("rf_asis_{}".format(4))
            rf_list = [rf_1, rf_2]
            self.set_sdr(sdr_type=sdr_type, sdr_asis=sdr_asis, rf_list=rf_list)
        try:
            self.execute_query("INSERT INTO idobr (type, master_sdr, slave_sdr, asis, sn) "
                               "VALUES ('{}', '{}', '{}', '{}', '{}')".
                               format(idobr_type, assembly.get("sdr_asis_1"),
                                      assembly.get("sdr_asis_2"), idobr_asis, idobr_sn))
            return True
        except Exception as e:
            print(e)
            return False

    def save_test_result(self, res):
        status = 'PASS' if res.get('status') else 'FAIL'
        asis = self.get_idobr_by_asis(res.get('system_asis')).get('asis')
        if asis is not None:
            self.execute_query("INSERT INTO test_{} (system_asis, date_test, meas_name, meas_func, status) "
                               "VALUES ('{}', '{}', '{}', '{}', '{}')"
                               .format(res.get('type_test'), asis,
                                       res.get('date_test'), res.get('meas_name'), res.get('meas_func'), status))
        else:
            raise ValueError('System {} not found in database'.format(res.get('system_asis')))

    def get_test_journal(self, **kwargs):
        filter_val = kwargs.get('filter_val')
        date_start = kwargs.get('date_start')
        date_stop = kwargs.get('date_stop')
        for_return = []
        if filter_val:
            query = "select * from " \
                    "(select *, idobr.sn " \
                    "from test_FufuiDOBR inner join idobr on idobr.asis = system_asis group by date_test) " \
                    "where system_asis like '%{}%' or sn like '%{}%' or type like '%{}%' " \
                    "and date_test between '{}' and '{}'"\
                .format(filter_val, filter_val, filter_val, date_start, date_stop)
        else:
            query = "select * from test_FufuiDOBR where date_test between '{}' and '{}' group by date_test".\
                format(date_start, date_stop)
        q = self.select_query(query)
        for i in q:
            q_status = self.select_query("select status from test_FufuiDOBR where "
                                         "system_asis = '{}' and date_test = '{}'".format(i[1], i[2]))
            for_return.append({'asis': i[1],
                               'date': i[2],
                               'meas': i[3],
                               'result': 'FAIL' if 'FAIL' in [x[0] for x in q_status] else 'PASS'})
        return for_return

    def get_current_system_tests(self, **kwargs):
        for_return = []
        date = kwargs.get('date')
        asis = kwargs.get('asis')
        query = "SELECT * from test_FufuiDOBR where date_test = '{}' and system_asis = '{}'".format(date, asis)
        q = self.select_query(query)
        for i in q:
            for_return.append({'asis': i[1],
                               'date': i[2],
                               'meas': i[3],
                               'meas_name': i[4],
                               'result': i[5]})
        return for_return


    def compare_assembly(self, assembly):
        db_assembly = self.get_idobr_assembly(assembly.get('idobr_asis'))
        diff_sys = set(list(assembly.values())) - set(list(db_assembly.values()))
        diff_db = set(list(db_assembly.values())) - set(list(assembly.values()))
        # print(diff_sys, diff_db)
        return {"diff": diff_sys == diff_db, "diff_sys": diff_sys, "diff_db": diff_db}



