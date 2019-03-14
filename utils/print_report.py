import os
import re
import xlrd
from reportlab.lib import colors
from reportlab.lib.pagesizes import (
    A4,
    inch)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Image,
    Table,
    TableStyle,
    Paragraph)


class Report:
    def __init__(self, rfb, sn, date, parent):
        self.tmpStyle = []
        if rfb is not None:
            resultDict = self.getResultDict(parent, sn, date, rfb)
            if resultDict.get('user_Dl') is None:
                resultDict.update({'user_Dl': resultDict.get('user_Ul')})
            if resultDict.get('user_Ul') is None:
                resultDict.update({'user_Ul': resultDict.get('user_Dl')})
            self.generateReport(resultDict, parent)
        else:
            self.getTemplates(parent)

    def generateReport(self, resultDict, parent):
        data = []
        tmpData = []
        Story = []

        doc = SimpleDocTemplate("test_report.pdf", pagesize=A4, rightMargin=5, leftMargin=5, topMargin=5,
                                bottomMargin=5)
        workbook = self.getTemplates(parent)
        worksheet = workbook.sheet_by_name(parent.reportTemplateCombo.currentText())

        for row in range(0, worksheet.nrows - 1):
            for col in range(0, worksheet.ncols - 1):
                val = str(worksheet.cell(row, col).value)
                if val == '':
                    tmpData.append('')
                    continue
                mm = re.findall('[#][a-zA-Z0-9_]+', val)
                if len(mm) > 0:
                    for m in mm:
                        postfix = m[len(m) - 3:]
                        if postfix in ('_Ul', '_Dl', '_at', '_st', '_re'):
                            val = str(val.replace(m, str(resultDict.get(m.replace('#', '')))))
                        else:
                            if '#user' in val:
                                val = str(val.replace(m, str(resultDict.get(m.replace('#', '')))))
                            if resultDict.get(m.replace('#', '') + '_Ul') is not None:
                                val = str(val.replace(m, str(resultDict.get(m.replace('#', '') + '_Ul'))))
                            else:
                                val = str(val.replace(m, str(resultDict.get(m.replace('#', '') + '_Dl'))))
                try:
                    tmpData.append(str(val.replace('@', '-')))
                except:
                    tmpData.append(str(val))

            data.append(tmpData)
            tmpData = []

        spanTemplate = worksheet.merged_cells

        self.tmpStyle.append(('ALIGNMENT', (0, 0), (-1, -1), 'RIGHT'))
        for row in range(0, worksheet.nrows - 1):
            for col in range(0, worksheet.ncols - 1):
                xfValue = self.getXfValue(workbook, worksheet, row, col)

                self.tmpStyle.append(('VALIGN', (col, row), (col, row), self.getAligment('v', xfValue)))
                self.tmpStyle.append(('ALIGN', (col, row), (col, row), self.getAligment('h', xfValue)))

                if xfValue.get('pattern_colour_index') is not None:
                    currColor = xfValue.get('pattern_colour_index')
                    self.tmpStyle.append(('BACKGROUND', (col, row), (col, row),
                                          colors.Color(red=(float(currColor[0]) / 255),
                                                       green=(float(currColor[1]) / 255),
                                                       blue=(float(currColor[2]) / 255))))
                self.getBorder(xfValue, row, col)

        for n in spanTemplate:
            self.tmpStyle.append(('SPAN', (n[2], n[0]), (n[3] - 1, n[1] - 1)))

        style = TableStyle(self.tmpStyle)
        tWeight = []
        for i in range(0, worksheet.ncols):
            tWeight.append(600 / worksheet.ncols - 1)
        workbook.release_resources()
        del workbook

        s = getSampleStyleSheet()
        s = s["BodyText"]
        s.wordWrap = 'CJK'
        data2 = [[Paragraph(cell, s) for cell in row] for row in data]
        t = Table(data2, colWidths=tWeight)
        t.setStyle(style)

        try:
            Story.append(self.generateHeaderTable(parent, resultDict))
            Story.append(t)
            doc.multiBuild(Story)
            # doc.build(elements)
            os.startfile(r'test_report.pdf')
        except Exception as e:
            parent.sendMsg('w', 'Create report error', str(e), 1)

    @staticmethod
    def getAligment(vh, xfValue):
        if vh == 'v':
            v = xfValue.get('vert_align')
            if v == 0:
                return 'TOP'
            elif v == 1:
                return 'MIDDLE'
            elif v == 2:
                return 'BOTTOM'
        else:
            a = xfValue.get('hor_align')
            if a == 1:
                return 'LEFT'
            elif a in [0, 2]:
                return 'CENTER'
            elif a == 3:
                return 'RIGHT'

    def getBorder(self, xfValue, row, col):
        if xfValue.get('top_line_style') != 0:
            self.tmpStyle.append(('LINEABOVE', (col, row), (col, row), 0.25, colors.black))
        if xfValue.get('bottom_line_style') != 0:
            self.tmpStyle.append(('LINEABOVE', (col, row), (col, row + 1), 0.25, colors.black))
        if xfValue.get('left_line_style') != 0:
            self.tmpStyle.append(('LINEBEFORE', (col, row), (col, row), 0.25, colors.black))
        if xfValue.get('right_line_style') != 0:
            self.tmpStyle.append(('LINEBEFORE', (col, row), (col + 1, row), 0.25, colors.black))

    def getXfValue(self, book, sheet, row, col):
        xfValue = {}
        xfx = sheet.cell_xf_index(row, col)
        xf = book.xf_list[xfx]
        bgx = xf.background.pattern_colour_index

        xfValue.update({'hor_align': xf.alignment.hor_align})
        xfValue.update({'vert_align': xf.alignment.vert_align})

        xfValue.update({'bottom_line_style': xf.border.bottom_line_style})
        xfValue.update({'top_line_style': xf.border.top_line_style})
        xfValue.update({'left_line_style': xf.border.left_line_style})
        xfValue.update({'right_line_style': xf.border.right_line_style})

        xfValue.update({'font_index': xf.font_index})

        xfValue.update({'pattern_colour_index': book.colour_map[bgx]})

        return xfValue

    @staticmethod
    def getResultDict(parent, sn, date, rfb):
        resultDict = {}
        resultKeys = []
        settingsKeys = []
        atrKeys = []
        dsaResKeys = []

        # resultDict.update({'user': parent.currUser})

        conn, cursor = parent.getConnDb()
        for n in ('test_results', 'test_settings', 'ATR', 'dsa_results'):
            q = 'PRAGMA table_info(%s)' % n
            rows = cursor.execute(q).fetchall()
            for row in rows:
                if n == 'test_results':
                    resultKeys.append(row[1])
                if n == 'test_settings':
                    settingsKeys.append(row[1])
                if n == 'ATR':
                    atrKeys.append(row[1])
                if n == 'dsa_results':
                    dsaResKeys.append(row[1])

        q = "select * from test_results where sn = '%s' and dateTest = '%s'" % (sn, date)
        rows = cursor.execute(q).fetchall()
        for row in rows:
            k = 0
            for n in row:
                # if DSA result == Warning, set to Pass
                if n == 'Warning':
                    n = 'Pass'
                resultDict.update({resultKeys[k] + '_' + row[4]: n})
                k += 1

        q = "select * from test_settings where rfb_type = '%s'" % (rfb)
        rows = cursor.execute(q).fetchall()
        for row in rows:
            k = 0
            for n in row:
                resultDict.update({settingsKeys[k] + '_st': n})
                k += 1

        q = "select * from ATR where rfb_type = '%s'" % (rfb)
        rows = cursor.execute(q).fetchall()
        for row in rows:
            k = 0
            for n in row:
                resultDict.update({atrKeys[k] + '_at': n})
                k += 1
        if resultDict.get('id_Ul') is not None:
            q = "select * from dsa_results where rfb = %s" % (resultDict.get('id_Ul'))
            rows = cursor.execute(q).fetchall()
            for row in rows:
                k = 0
                for n in row:
                    resultDict.update({'ul_' + dsaResKeys[k] + '_re': str(n).replace('{', '').replace('}', '')})
                    k += 1

        if resultDict.get('id_Dl') is not None:
            q = "select * from dsa_results where rfb = %s" % (resultDict.get('id_Dl'))
            rows = cursor.execute(q).fetchall()
            for row in rows:
                k = 0
                for n in row:
                    resultDict.update({'dl_' + dsaResKeys[k] + '_re': str(n).replace('{', '').replace('}', '')})
                    k += 1
        conn.close()
        return resultDict

    def getTemplates(self, parent):
        workbook = xlrd.open_workbook('templates/template.xls', formatting_info=True, on_demand=True)
        if len(parent.reportTemplateCombo) == 0:
            for k in workbook.sheet_names():
                parent.reportTemplateCombo.addItem(k)
        return workbook

    def generateHeaderTable(self, parent, resultDict):
        if parent.logoAxellRadio.isChecked():
            im = Image("Img/axell_logo.png", hAlign='CENTER')
            im.drawHeight = 1.2 * inch * im.drawHeight / im.drawWidth
            im.drawWidth = 1.2 * inch
        if parent.logoCobhamRadio.isChecked():
            im = Image("Img/cobham_logo.png", hAlign='CENTER')
            im.drawHeight = 1.5 * inch * im.drawHeight / im.drawWidth
            im.drawWidth = 1.5 * inch

        styleSheet = getSampleStyleSheet()

        P0 = Paragraph('''
        <b>A pa<font color=red>r</font>a<i>graph</i></b>
        <super><font color=yellow>1</font></super>''',
                       styleSheet["BodyText"])

        P = Paragraph('''
        <para align=center spaceb=3>The <b>ReportLab Left
        <font color=red>Logo</font></b>
        Image</para>''',
                      styleSheet["BodyText"])

        # if resultDict.get('rfb_type_Ul') is not None:
        #     rfb_type = resultDict.get('rfb_type_Ul')
        # else:
        #     rfb_type = resultDict.get('rfb_type_Dl')

        atr_name_at = str(resultDict.get('atr_name_at')).replace('\\n', '\n ')
        data = [[im, atr_name_at, 'Date: ' + str(resultDict.get('atr_date_at'))],
                ['', '', 'Doc. p/n: ' + str(resultDict.get('atr_doc_pn_at'))],
                ['', '', 'Rev.: ' + str(resultDict.get('atr_rev_at'))]]

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
