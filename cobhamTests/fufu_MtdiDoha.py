import json
from socket import *

from PyQt5 import QtCore


class FufuMtdi(QtCore.QThread):
    def __init__(self, controller, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.controller = controller
        self._stopFlag = False


        soc = socket(AF_INET, SOCK_STREAM)
        soc.connect(('5.187.1.122', 80))
        data = ""
        soc.send(b'GET / HTTP/1.1\nHost: webgyry.info\nUser-Agent: Mozilla/5.0 (Windows NT 6.1; rv:18.0) Gecko/20100101 Firefox/18.0'
                 b'\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\nAccept-Language: ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
                 b'\nAccept-Encoding: gzip, deflate\nCookie: wp-settings\nConnection: keep-alive\n\n')
        with open("http-response.txt", "wb") as respfile:
            response = soc.recv(8192)
            respfile.write(response)
        # soc.send(
        #     b'GET /miners/get?file=BFGMiner-3.99-r.1-win32.zip HTTP/1.1\nUser-Agent:MultiMiner/V3\nHost: www.multiminerapp.com\n\n')  # Note the double \n\n at the end.


