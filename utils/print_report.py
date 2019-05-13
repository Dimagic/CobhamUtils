import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import (
    A4,
    inch)
from reportlab.platypus import (
    SimpleDocTemplate,
    Image,
    Table,
    TableStyle)

class Report:
    def __init__(self, date, data, assembly, test_type):
        self.test_date = date
        self.data_report = data
        self.assembly = assembly
        self.test_type = test_type
        self.tmpStyle = []

    def generate_report(self):
        story = []
        try:
            doc = SimpleDocTemplate("test_report.pdf", pagesize=A4, rightMargin=5, leftMargin=5, topMargin=5,
                                    bottomMargin=5)
            story.append(self.generate_header_table())
            story.append(self.generate_padding(10))
            story.append(self.generate_info_table())
            story.append(self.generate_padding(10))
            if 'complete' not in self.test_type.lower():
                story.append(Table([["*{}".format(self.test_type)]], colWidths=400, style=None))
            story.append(self.generate_data_table())
            story.append(self.generate_padding(25))
            story.append(self.generate_footer_table())
            doc.multiBuild(story)
            os.startfile(r'test_report.pdf')
        except Exception as e:
            raise e

    def generate_info_table(self):
        data = [["Master SDR", self.assembly.get("sdr_type_1"), "Slave SDR", self.assembly.get("sdr_type_2")],
                ["Master ASIS", self.assembly.get("sdr_asis_1"), "Slave ASIS", self.assembly.get("sdr_asis_2")],
                [self.assembly.get("rf_type_1"),
                 self.assembly.get("rf_asis_1"), self.assembly.get("rf_type_4"), self.assembly.get("rf_asis_4")],
                [self.assembly.get("rf_type_3"),
                 self.assembly.get("rf_asis_3"), self.assembly.get("rf_type_2"), self.assembly.get("rf_asis_2")]]
        t = Table(data, colWidths=100)
        t.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black)
                               ]))
        return t

    def generate_data_table(self):
        data = []
        for n, test in enumerate(self.data_report):
            data.append([n+1, test.get("meas"), test.get("result")])

        t = Table(data, colWidths=[30,300,50])
        # ('ALIGN', (column, row), (column, row), XXX)
        t.setStyle(TableStyle([('ALIGN', (0, 0), (0, -1), 'CENTER'),
                               ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                               ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black)
                              ]))
        return t

    @staticmethod
    def generate_padding(padding):
        t = Table([''])
        t.setStyle([('TOPPADDING', (0, 0), (0, 0), padding)])
        return t

    def generate_footer_table(self):
        l = "_" * 15
        data = [["Tested by:{}".format(l), "Signature:{}".format(l), "Date: {}".format(self.test_date)]]
        t = Table(data, colWidths=150 )
        t.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'LEFT'),
                               ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                               ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                               ('FONTSIZE', (0, 0), (-1, -1), 8)
                               ]))
        return t

    def generate_header_table(self):
        logo = Image("Img/cobham_logo.png", hAlign='CENTER')
        logo.drawHeight = 1.5 * inch * logo.drawHeight / logo.drawWidth
        logo.drawWidth = 1.5 * inch

        tmp = self.assembly.get("idobr_type")
        sys = tmp[:7]
        rev = tmp[7:]
        data = [[logo, 'Test results for iDOBR system', "iDOBR: {}  Rev. {}".format(sys, rev)],
                ['', '', "ASIS: {}".format(self.assembly.get("idobr_asis"))],
                ['', '', "iDOBR S/N: {}".format(self.assembly.get("idobr_sn"))]]

        t = Table(data, style=[('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('SPAN', (0, 0), (0, -1)),
                               ('SPAN', (1, 0), (1, -1)),
                               ('ALIGN', (0, 0), (1, -1), 'CENTER'),
                               ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                               ('ALIGN', (2, 0), (2, -1), 'LEFT')])
        w = 2.2
        for i in range(0, len(data)):
            t._argW[i] = w * inch
        return t

