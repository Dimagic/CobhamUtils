import xlrd
from PyQt5 import uic, QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QDialog, QHeaderView, QTableWidgetItem, QAbstractItemView, QMessageBox, QTreeWidgetItem

from cobhamGui.w_assembly import WindowAssembly
from cobhamTests.fufu_IDOBR import FufuiDOBR
from database.cobhamdb import CobhamDB
from utils.print_report import Report


class WindowTestJournal(QDialog):
    def __init__(self, parent):
        super(WindowTestJournal, self).__init__(parent)
        self.db = CobhamDB()
        self.parent = parent
        self.assembly = {}
        self.appIcon = parent.appIcon
        self.w_journal = uic.loadUi('forms/journal.ui')
        self.w_journal.setWindowTitle('Test journal')
        self.w_journal.setWindowIcon(self.appIcon)
        self.w_journal.setWindowFlags(QtCore.Qt.WindowSystemMenuHint |
                                       QtCore.Qt.WindowMinMaxButtonsHint |
                                       QtCore.Qt.WindowCloseButtonHint)
        self.w_journal.filter.textChanged.connect(self.filter)
        self.w_journal.print_btn.clicked.connect(self.print_report)

        self.header_journal = ["System type", "System ASIS", "System SN", "Test type", "Test date", "Result"]
        self.header_tests = ["Test name", "Result"]
        self.w_journal.journal_tab.cellDoubleClicked.connect(self.cellDoubleClick)
        self.w_journal.journal_tab.cellClicked.connect(self.cell_select)
        self.w_journal.journal_tab.setSortingEnabled(True)

        self.w_journal.assembly_tree.setHeaderHidden(True)
        curr_date = QtCore.QDate.currentDate()
        self.w_journal.start_date.setDate(curr_date.addDays(-curr_date.day() + 1))
        self.w_journal.stop_date.setDate(curr_date.addDays(curr_date.daysInMonth() - curr_date.day()))
        self.w_journal.start_date.dateChanged.connect(self.fill_tab_row)
        self.w_journal.stop_date.dateChanged.connect(self.fill_tab_row)

        self.fill_tab_header()
        self.fill_tab_row()
        self.fill_temp_combo()

        self.w_journal.exec_()

    def print_report(self):
        selected = self.w_journal.journal_tab.selectedIndexes()
        if len(selected) == 0:
            self.parent.send_msg('i', 'Print report', 'You have to choice report for print', 1)
            return
        else:
            row = selected[0].row()
            asis = self.w_journal.journal_tab.item(row, 1).text()
            test_type = self.w_journal.journal_tab.item(row, 3).text()
            date = self.w_journal.journal_tab.item(row, 4).text()



        try:
            report_data = self.db.get_current_system_tests(asis=asis, date=date)
            assembly = self.db.get_idobr_assembly(asis)
            report = Report(date=date, data=report_data, assembly=assembly, test_type=test_type)
            report.generate_report()
        except Exception as e:
            self.parent.send_msg('w', 'Generate report error', str(e), 1)

    def fill_temp_combo(self):
        workbook = xlrd.open_workbook('templates/template.xls', formatting_info=True, on_demand=True)
        for k in workbook.sheet_names():
            self.w_journal.templ_combo.addItem(k)

    def fill_tab_header(self):
        """
        Tests journal table
        """
        self.w_journal.journal_tab.setSelectionMode(QAbstractItemView.SingleSelection)
        self.w_journal.journal_tab.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.w_journal.journal_tab.setRowCount(0)
        self.w_journal.journal_tab.setColumnCount(len(self.header_journal))
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.w_journal.journal_tab.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.w_journal.journal_tab.setHorizontalHeaderLabels(self.header_journal)

        """
        Tests result table
        """
        self.w_journal.tests_tab.setSelectionMode(QAbstractItemView.SingleSelection)
        self.w_journal.tests_tab.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.w_journal.tests_tab.setRowCount(0)
        self.w_journal.tests_tab.setColumnCount(len(self.header_tests))
        self.w_journal.tests_tab.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.w_journal.tests_tab.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self.w_journal.tests_tab.setHorizontalHeaderLabels(self.header_tests)

    """
    Function fill test result table
    and statistic
    """
    def fill_tab_row(self, **kwargs):
        start = self.w_journal.start_date.date().toPyDate()
        stop = self.w_journal.stop_date.date().toPyDate()
        self.w_journal.journal_tab.setRowCount(0)
        rows = self.db.get_test_journal(filter_key=kwargs.get('f_key'),filter_val=kwargs.get('f_val'),
                                        date_start=start, date_stop=stop)
        total_system = {}
        pass_count = 0
        fail_count = 0
        total_tests = len(rows)

        for row in rows:
            total_system.update({row.get('system_asis'): None})
            res = row.get('result')
            if res == 'PASS':
                pass_count += 1
            if res == 'FAIL':
                fail_count += 1

            curr_sys = self.db.get_idobr_by_asis(row.get('asis'))
            if row.get('result') == 'PASS':
                result = QTableWidgetItem(QtGui.QIcon(self.parent.passImg), "")
            else:
                result = QTableWidgetItem(QtGui.QIcon(self.parent.failImg), "")
            rowPosition = self.w_journal.journal_tab.rowCount()
            self.w_journal.journal_tab.insertRow(rowPosition)
            self.w_journal.journal_tab.setItem(rowPosition, 0, QTableWidgetItem(curr_sys.get('type')))
            self.w_journal.journal_tab.setItem(rowPosition, 1, QTableWidgetItem(curr_sys.get('asis')))
            self.w_journal.journal_tab.setItem(rowPosition, 2, QTableWidgetItem(curr_sys.get('sn')))
            self.w_journal.journal_tab.setItem(rowPosition, 3, QTableWidgetItem(self.get_type_test(
                asis=curr_sys.get('asis'), date_test=row.get('date'))))
            self.w_journal.journal_tab.setItem(rowPosition, 4, QTableWidgetItem(row.get('date')))
            self.w_journal.journal_tab.setItem(rowPosition, 5, result)
            # self.w_journal.journal_tab.resizeRowsToContents()

        self.w_journal.total_test_stat.setText(str(total_tests))
        self.w_journal.total_system_stat.setText(str(len(total_system.keys())))
        try:
            self.w_journal.pass_stat.setText("{}({}%)".format(str(pass_count),
                                                              str(round(pass_count * 100 / int(total_tests), 1))))
            self.w_journal.fail_stat.setText("{}({}%)".format(str(fail_count),
                                                              str(round(fail_count * 100 / int(total_tests), 1))))
        except ZeroDivisionError:
            self.w_journal.pass_stat.setText("{}({}%)".format('0', '0'))
            self.w_journal.fail_stat.setText("{}({}%)".format('0', '0'))

    """
    Function return type of current test
    Partial or Complete
    """
    def get_type_test(self, **kwargs):
        asis = kwargs.get('asis')
        date = kwargs.get('date_test')
        tests = len(self.db.get_current_system_tests(date=date, asis=asis))
        # ToDo: select test type (FufuiDOBR... etc)
        queue = len(self.parent.get_tests_queue(FufuiDOBR))
        type_test = "Partial test" if tests != queue else "Complete test"
        return type_test

    """
    Function open in new window
    assembly of current system
    """
    def cellDoubleClick(self, row, column):
        if self.header_journal[column] in ["System ASIS", "System SN"]:
            by_asis = self.db.get_idobr_by_asis(self.w_journal.journal_tab.item(row, column).text())
            by_sn = self.db.get_idobr_by_sn(self.w_journal.journal_tab.item(row, column).text())
            system = by_asis if by_asis is not None else by_sn
            assembly = self.db.get_idobr_assembly(system.get('asis'))
            if len(assembly) != 0:
                WindowAssembly(parent=self.parent, assembly=assembly)

    """
    Function show in journal window 
    tests result of current system test
    """
    def cell_select(self, row, column):
        self.w_journal.tests_tab.setRowCount(0)
        date = self.w_journal.journal_tab.item(row, 4).text()
        asis = self.w_journal.journal_tab.item(row, 1).text()
        rows = self.db.get_current_system_tests(date=date, asis=asis)
        for row in rows:
            if row.get('result') == 'PASS':
                result = QTableWidgetItem(QtGui.QIcon(self.parent.passImg), "")
            else:
                result = QTableWidgetItem(QtGui.QIcon(self.parent.failImg), "")
            rowPosition = self.w_journal.tests_tab.rowCount()
            self.w_journal.tests_tab.insertRow(rowPosition)
            self.w_journal.tests_tab.setItem(rowPosition, 0, QTableWidgetItem(row.get('meas')))
            self.w_journal.tests_tab.setItem(rowPosition, 1, QTableWidgetItem(result))


        system = self.db.get_idobr_by_asis(asis=asis)
        # by_sn = self.db.get_idobr_by_sn(self.w_journal.journal_tab.item(row, 2).text())
        # system = by_asis if by_asis is not None else by_sn
        assembly = self.db.get_idobr_assembly(system.get('asis'))
        if len(assembly) != 0:
            self.fill_assembly(assembly)
        self.w_journal.assembly_tree.expandToDepth(1)

    """
    Function build and fill
    assembly tree
    """
    def fill_assembly(self, assembly):
        self.w_journal.assembly_tree.clear()
        system = "{} ASIS: {} SN: {}".format(assembly.get('idobr_type'), assembly.get('idobr_asis'), assembly.get('idobr_sn'))
        root = QTreeWidgetItem(self.w_journal.assembly_tree, [system], 1)
        sub_item_m = QTreeWidgetItem(root, ["master SDR %s ASIS: %s" % (assembly.get('sdr_type_1'), assembly.get('sdr_asis_1'))])
        sub_item_s = QTreeWidgetItem(root, ["slave SDR %s ASIS: %s" % (assembly.get('sdr_type_2'), assembly.get('sdr_asis_2'))])
        QTreeWidgetItem(sub_item_m, ["rf: {} ASIS: {}".format(assembly.get('rf_type_1'), assembly.get('rf_asis_1'))])
        QTreeWidgetItem(sub_item_m, ["rf: {} ASIS: {}".format(assembly.get('rf_type_3'), assembly.get('rf_asis_3'))])
        QTreeWidgetItem(sub_item_s, ["rf: {} ASIS: {}".format(assembly.get('rf_type_2'), assembly.get('rf_asis_2'))])
        QTreeWidgetItem(sub_item_s, ["rf: {} ASIS: {}".format(assembly.get('rf_type_4'), assembly.get('rf_asis_4'))])

    def filter(self):
        f_val = self.w_journal.filter.text().upper()
        self.fill_tab_row(f_val=f_val)





