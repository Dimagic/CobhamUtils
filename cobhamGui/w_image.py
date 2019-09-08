from PyQt5 import uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog


class ImageMessage(QDialog):
    def __init__(self, parent, **kwargs):
        super(ImageMessage, self).__init__(parent)
        self.answer = False
        self.parent = parent
        self.appIcon = parent.appIcon
        self.w_image_msg = uic.loadUi('forms/image_msg.ui')
        self.w_image_msg.setWindowTitle(kwargs.get('title'))
        self.w_image_msg.setWindowIcon(self.appIcon)
        self.w_image_msg.img_txt_lbl.setText(kwargs.get('text'))
        img = QPixmap('img/{}'.format(kwargs.get('image')))
        self.w_image_msg.img_lbl.setPixmap(img)
        row_num = len(kwargs.get('text').split('\n')) * 20 + 25

        self.w_image_msg.setFixedSize(img.width() + 25, img.height() + self.w_image_msg.buttonBox.height() + row_num)

        self.w_image_msg.buttonBox.accepted.connect(self.ok)
        self.w_image_msg.buttonBox.rejected.connect(self.cancel)

        self.w_image_msg.exec_()


    def ok(self):
        self.answer = True
        self.w_image_msg.close()

    def cancel(self):
        self.answer = False
        self.w_image_msg.close()

    def get_answer(self):
        return self.answer
