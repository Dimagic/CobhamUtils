from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QHeaderView, QTableWidgetItem, QAbstractItemView


class WindowTestSelect(QDialog):
    def __init__(self, parent, tests):
        super(WindowTestSelect, self).__init__(parent)
        self.parent = parent
        self.appIcon = parent.appIcon
        self.w_testselect = uic.loadUi('forms/testselect.ui')
        self.w_testselect.setWindowTitle('Select test')
        self.w_testselect.setWindowIcon(self.appIcon)
        self.test_type = ''

        self.w_testselect.buttonBox.accepted.connect(self.ok_pressed)
        # self.w_testselect.buttonBox.rejected.connect(self.cancel_pressed)

        self.w_testselect.tests_tab.setSelectionMode(QAbstractItemView.SingleSelection)
        self.w_testselect.tests_tab.setColumnCount(1)
        self.w_testselect.tests_tab.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.w_testselect.tests_tab.setHorizontalHeaderLabels(["Tests"])
        self.fill_tests(tests)

        self.w_testselect.exec_()

    def fill_tests(self, tests):
        for i in tests:
            rowPosition = self.w_testselect.tests_tab.rowCount()
            self.w_testselect.tests_tab.insertRow(rowPosition)
            self.w_testselect.tests_tab.setItem(rowPosition, 0, QTableWidgetItem(i))

    def ok_pressed(self):
        rows = self.w_testselect.tests_tab.selectionModel().selectedIndexes()
        if len(rows) != 0:
            self.test_type = self.w_testselect.tests_tab.item(rows[0].row(), 0).text()
        else:
            self.parent.send_msg('i', 'CobhamUtils', 'No test selected', 1)
            return


