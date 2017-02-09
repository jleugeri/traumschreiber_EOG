import pexpect
from datetime import datetime
import time
import numpy as np
import threading
import random

from PyQt5.QtWidgets import QApplication, QWidget, QGraphicsView, QGraphicsScene
from PyQt5.QtGui import QKeyEvent, QBrush, QPen, QPixmap, QCloseEvent
from PyQt5.Qt import Qt
from PyQt5.QtCore import QThread, QRect, QRectF, QPoint, QSize
from PyQt5.QtTest import QTest



# setup variables
device_addr = '20:73:7A:17:69:31'
chx_handle = '0x010c'
gatt_logging = False
filename = 'dump.csv'


# global variables for thread communication
current_x = 0
current_y = 0
lock = threading.Lock()

data = []


class GattListener:

    def __init__(self, device_addr, char_handle, gatt_logging):
        self.device_addr = device_addr
        self.char_handle = char_handle
        self.gatt_logging = gatt_logging
        self.gatt_process = None
        self.thread = None
        self.running = True

    def spawn_gattprocess(self):
        self.close_gattprocess()
        self.gatt_process = pexpect.spawn('gatttool -b {addr} --char-write-req -a {hndl} --value=0100 --listen'.format(addr=self.device_addr, hndl=self.char_handle))
        self.log('Waiting for device setup...')
        time.sleep(5)

    def close_gattprocess(self):
        if self.gatt_process:
            self.gatt_process.close()
            self.gatt_process = None

    def start(self):
        self.log('Starting ...')
        self.running = True
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def stop(self):
        self.log('Shutting Down ...')
        self.running = False
        self.thread.join()
        self.close_gattprocess()


    def run(self):
        global current_x, current_y, lock, data
        self.spawn_gattprocess()
        t1 = time.time()
        counter = 0
        while self.running:
            try:
                self.gatt_process.expect('Notification handle = {hndl} value: ([0123456789abcdef ]*) \r\n'.format(hndl=self.char_handle), timeout=1)
                values,  = self.gatt_process.match.groups()
                values = self.parse(values)
                with lock:
                    value_tuple = (time.time(), values, (current_x, current_y))
                data.append(value_tuple)
                counter += 1
                if counter == 100:
                    t2 = time.time()
                    self.log('Receiving {:d} packages per second.'.format(int(100/(t2-t1))))
                    counter = 0
                    t1 = t2
                if self.gatt_logging:
                    self.log('received values: {}'.format(value_tuple))

            except pexpect.TIMEOUT:
                self.log('Connection timeout! Restarting connection ...')
                self.spawn_gattprocess()


    @staticmethod
    def parse(str):
        ''' Parse the received package '''
        buf = bytes((int(x, 16) for x in str.split(b' ')))
        return np.frombuffer(buf, dtype=np.int16)

    @staticmethod
    def log(msg):
        print('[GATT]: {msg}'.format(msg=msg))




class Stimulus(QGraphicsView):
    def __init__(self):
        QGraphicsView.__init__(self)
        self.running = False

        self.img = None
        # optional: specify background image, or set to None
        # self.img = QPixmap('keyboard.png') # type: QPixmap

        # setup scene
        self.setScene(QGraphicsScene())
        self.setBackgroundBrush(QBrush(Qt.black))
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)


    def stop(self):
        global current_x, current_y, lock
        self.log('Stopping...')
        self.running = False
        with lock:
            current_x = 0
            current_y = 0

    def start(self):
        self.log('Starting...')
        self.running = True

        # TODO: pick different parameters for each run
        while self.running:

            n = 10
            t = 800
            sigma = 100
            border = 50

            rect = self.frameRect()  # type: QRect

            # show corner points for calibration in random order
            # top-left, bottom-left, bottom-right, top-right
            xs = [border, border, rect.width() - border, rect.width() - border]
            ys = [border, rect.height() - border, rect.height() - border, border]
            corners = list(zip(xs, ys))
            random.shuffle(corners)
            for x, y in corners:
                if not self.running:
                    break
                self.show_point(x, y, t, sigma)

            # show uniform distributed random points
            for i in range(n):
                if not self.running:
                    break
                x = random.randrange(rect.width()-2*border)
                y = random.randrange(rect.height()-2*border)
                self.show_point(border+x, border+y, t, sigma)

        self.scene().clear()
        QApplication.processEvents()



    def show_point(self, x, y, t, sigma = None):
        global current_x, current_y, lock
        self.log('Show point at ({},{})'.format(x, y))
        point_size = 15

        global_point = self.mapToGlobal(QPoint(x, y))  # type: QPoint
        with lock:
            current_x = global_point.x()
            current_y = global_point.y()

            s = self.scene()  # type: QGraphicsScene
            s.clear()
            rect = QRectF(self.frameRect())
            s.addRect(rect)
            if self.img:
                s.addPixmap(self.img.scaled(rect.size().toSize(), Qt.KeepAspectRatio))
            s.addEllipse(x, y, point_size, point_size, QPen(Qt.white), QBrush(Qt.red))
            QApplication.processEvents()

        if sigma:
            QTest.qWait(random.gauss(t, sigma))
        else:
            QTest.qWait(t)


    def keyPressEvent(self, event : QKeyEvent):
        # toggle full-screen
        if event.key() == Qt.Key_F:
            if self.isFullScreen():
                self.log('Exit fullscreen ...')
                self.showNormal()
            else:
                self.log('Start fullscreen ...')
                self.showFullScreen()

        # start/stop recording
        if event.key() == Qt.Key_S:
            if self.running:
                self.stop()
            else:
                self.start()

    def closeEvent(self, event : QCloseEvent):
        self.stop()
        event.accept()

    @staticmethod
    def log(msg):
        print('[STIM]: {msg}'.format(msg=msg))


gatt = GattListener(device_addr, chx_handle, gatt_logging)
gatt.start()

qapp = QApplication([])
stim = Stimulus()
stim.show()
qapp.exec_()

gatt.stop()

with open(filename, 'w') as f:
    f.write('t, ' + ', '.join('ch{}'.format(n) for n in range(8)) + ', x, y\n')
    for time, vals, (x, y) in data:
        f.write('{}, {}, {}, {}\n'.format(time, ", ".join(str(v) for v in vals), x, y))

