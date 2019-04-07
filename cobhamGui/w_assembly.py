from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QTreeWidgetItem, QStyle

from database.cobhamdb import CobhamDB


class WindowAssembly(QDialog):
    def __init__(self, parent, assembly):
        super(WindowAssembly, self).__init__(parent)
        self.db = CobhamDB()
        self.parent = parent
        self.appIcon = parent.appIcon
        self.w_assembly = uic.loadUi('forms/assembly.ui')
        self.w_assembly.setWindowTitle('Assembly')
        self.w_assembly.setWindowIcon(self.appIcon)

        self.w_assembly.tree.setHeaderHidden(True)
        self.fill_tree(assembly)
        self.w_assembly.tree.expandToDepth(1)
        self.w_assembly.exec_()

    def fill_tree(self, assembly):
        print(assembly)
        system = "{} ASIS: {} SN: {}".format(assembly.get('idobr_type'), assembly.get('idobr_asis'), assembly.get('idobr_sn'))
        root = QTreeWidgetItem(self.w_assembly.tree, [system], 1)
        # root.setIcon(0, app.style().standardIcon(QStyle.SP_ArrowUp))
        # # for i in range(3):
        # #     sub_item = QTreeWidgetItem(root, ["sub %s %s" % (i)])
        sub_item_m = QTreeWidgetItem(root, ["master SDR %s ASIS: %s" % (assembly.get('sdr_type_1'), assembly.get('sdr_asis_1'))])
        sub_item_s = QTreeWidgetItem(root, ["slave SDR %s ASIS: %s" % (assembly.get('sdr_type_2'), assembly.get('sdr_asis_2'))])
        QTreeWidgetItem(sub_item_m, ["rf: {} ASIS: {}".format(assembly.get('rf_type_1'), assembly.get('rf_asis_1'))])
        QTreeWidgetItem(sub_item_m, ["rf: {} ASIS: {}".format(assembly.get('rf_type_3'), assembly.get('rf_asis_3'))])
        QTreeWidgetItem(sub_item_s, ["rf: {} ASIS: {}".format(assembly.get('rf_type_2'), assembly.get('rf_asis_2'))])
        QTreeWidgetItem(sub_item_s, ["rf: {} ASIS: {}".format(assembly.get('rf_type_4'), assembly.get('rf_asis_4'))])
