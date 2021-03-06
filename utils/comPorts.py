import serial.tools.list_ports
import serial

from database.cobhamdb import CobhamDB

class ComPort:
    @staticmethod
    def get_port_list():
        list_com = list(serial.tools.list_ports.comports())
        return sorted(list_com)

    @staticmethod
    def get_baud_list():
        return [4800, 9600, 19200, 38400, 57600, 115200, 230400]

    @staticmethod
    def get_connection():
        db = CobhamDB()
        tmp = db.get_port_baud()
        port = tmp.get('port')
        baud = tmp.get('baud')
        try:
            ser = serial.Serial(port, baud, timeout=False)
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            return ser
        except Exception as e:
            raise e

