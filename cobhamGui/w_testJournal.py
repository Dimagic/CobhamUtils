from PyQt5 import uic, QtCore, QtGui
from PyQt5.QtWidgets import QDialog, QHeaderView, QTableWidgetItem, QAbstractItemView

from cobhamGui.w_assembly import WindowAssembly
from database.cobhamdb import CobhamDB


class WindowTestJournal(QDialog):
    def __init__(self, parent):
        super(WindowTestJournal, self).__init__(parent)
        self.db = CobhamDB()
        self.parent = parent
        self.appIcon = parent.appIcon
        self.w_journal = uic.loadUi('forms/journal.ui')
        self.w_journal.setWindowTitle('Test journal')
        self.w_journal.setWindowIcon(self.appIcon)
        self.w_journal.setWindowFlags(QtCore.Qt.WindowSystemMenuHint |
                                       QtCore.Qt.WindowMinMaxButtonsHint |
                                       QtCore.Qt.WindowCloseButtonHint)
        self.w_journal.filter.textChanged.connect(self.filter)
        self.header = ["System type", "System ASIS", "System SN", "Test type", "Test date", "Result"]
        self.w_journal.journal_tab.cellDoubleClicked.connect(self.cellDoubleClick)

        self.fill_tab_header()
        self.fill_tab_row()

        self.w_journal.exec_()

    def fill_tab_header(self):
        self.w_journal.journal_tab.setSelectionMode(QAbstractItemView.SingleSelection)
        self.w_journal.journal_tab.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.w_journal.journal_tab.setRowCount(0)
        self.w_journal.journal_tab.setColumnCount(len(self.header))
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.w_journal.journal_tab.setHorizontalHeaderLabels(self.header)

    def fill_tab_row(self, **kwargs):
        self.w_journal.journal_tab.setRowCount(0)
        rows = self.db.get_test_journal(filter_key=kwargs.get('f_key'),filter_val=kwargs.get('f_val'))
        for row in rows:
            curr_sys = self.db.get_idobr_by_asis(row.get('asis'))
            print(curr_sys)
            if row.get('result') == 'PASS':
                result = QTableWidgetItem(QtGui.QIcon(self.parent.passImg), "")
            else:
                result = QTableWidgetItem(QtGui.QIcon(self.parent.failImg), "")
            rowPosition = self.w_journal.journal_tab.rowCount()
            self.w_journal.journal_tab.insertRow(rowPosition)
            self.w_journal.journal_tab.setItem(rowPosition, 0, QTableWidgetItem(curr_sys.get('type')))
            self.w_journal.journal_tab.setItem(rowPosition, 1, QTableWidgetItem(curr_sys.get('asis')))
            self.w_journal.journal_tab.setItem(rowPosition, 2, QTableWidgetItem(curr_sys.get('sn')))
            self.w_journal.journal_tab.setItem(rowPosition, 3, QTableWidgetItem("Partial test"))
            self.w_journal.journal_tab.setItem(rowPosition, 4, QTableWidgetItem(row.get('date')))
            self.w_journal.journal_tab.setItem(rowPosition, 5, result)
            # self.w_journal.journal_tab.resizeRowsToContents()

    def cellDoubleClick(self, row, column):
        if self.header[column] in ["System ASIS", "System SN"]:
            by_asis = self.db.get_idobr_by_asis(self.w_journal.journal_tab.item(row, column).text())
            by_sn = self.db.get_idobr_by_sn(self.w_journal.journal_tab.item(row, column).text())
            system = by_asis if by_asis is not None else by_sn
            assembly = self.db.get_idobr_assembly(system.get('asis'))
            if len(assembly) != 0:
                WindowAssembly(parent=self.parent, assembly=assembly)

    def filter(self):
        f_val = self.w_journal.filter.text().upper()
        self.fill_tab_row(f_val=f_val)





