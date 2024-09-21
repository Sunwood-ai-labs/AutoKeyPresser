import sys
import os
import threading
import time
import pyautogui
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFrame, QLineEdit)
from PyQt6.QtGui import QIcon, QMouseEvent, QCursor
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QSize, pyqtSignal
from qt_material import apply_stylesheet

class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.icon_label = QLabel()
        # アイコン画像のパスを設定してください
        self.icon_label.setPixmap(QIcon("./docs/icon.png").pixmap(20, 20))
        self.icon_label.setStyleSheet("padding: 5px;")
        self.layout.addWidget(self.icon_label)

        self.title = QLabel("AutoKeyPresser")
        self.title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        self.layout.addWidget(self.title)

        self.layout.addStretch(1)

        self.minimize_button = QPushButton("－")
        self.minimize_button.clicked.connect(self.window().showMinimized)
        self.layout.addWidget(self.minimize_button)

        self.close_button = QPushButton("✕")
        self.close_button.clicked.connect(self.window().close)
        self.layout.addWidget(self.close_button)

        self.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 5px 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #44475a;
            }
        """)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self.window().drag_position)
            event.accept()

class AutoClicker(QMainWindow):
    status_signal = pyqtSignal(str)
    mouse_pos_signal = pyqtSignal(int, int)  # マウス座標用のシグナルを追加

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 400, 300)

        # リサイズに関する初期化
        self.resizing = False
        self.dragging = False
        self.drag_position = QPoint()
        self.mouse_pos = None
        self.margin = 10

        # アプリケーションアイコンの設定
        icon_path = os.path.abspath("./docs/icon.png")  # アイコン画像のパスを設定してください
        self.setWindowIcon(QIcon(icon_path))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.frame = QFrame()
        self.frame.setObjectName("mainFrame")
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(0, 0, 0, 0)
        self.frame_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        self.frame_layout.addWidget(self.title_bar, 0)

        # メインコンテンツ
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(10)

        # キー入力
        self.key_label = QLabel('連打するキー:')
        self.key_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.content_layout.addWidget(self.key_label)

        self.key_input = QLineEdit()
        self.content_layout.addWidget(self.key_input)

        # インターバル入力
        self.interval_label = QLabel('間隔 (ミリ秒):')
        self.interval_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.content_layout.addWidget(self.interval_label)

        self.interval_input = QLineEdit()
        self.content_layout.addWidget(self.interval_input)

        # 座標入力
        coord_layout = QHBoxLayout()
        self.x_label = QLabel('X座標:')
        self.x_input = QLineEdit()
        self.y_label = QLabel('Y座標:')
        self.y_input = QLineEdit()
        coord_layout.addWidget(self.x_label)
        coord_layout.addWidget(self.x_input)
        coord_layout.addWidget(self.y_label)
        coord_layout.addWidget(self.y_input)
        self.content_layout.addLayout(coord_layout)

        # 位置取得ボタン
        self.get_pos_button = QPushButton('現在のマウス位置を取得 (F8)')
        self.get_pos_button.clicked.connect(self.get_mouse_position)
        self.content_layout.addWidget(self.get_pos_button)

        # ステータスラベル
        self.status_label = QLabel('ステータス: 停止中')
        self.content_layout.addWidget(self.status_label)

        self.frame_layout.addWidget(self.content)
        self.layout.addWidget(self.frame)

        self.is_running = False
        self.stop_event = threading.Event()
        self.status_signal.connect(self.update_status)
        self.mouse_pos_signal.connect(self.update_mouse_position)  # シグナルをスロットに接続

        # グローバルホットキーの設定
        self.listener = threading.Thread(target=self.listen_hotkeys)
        self.listener.daemon = True
        self.listener.start()

        self.setStyleSheet("""
            #mainFrame {
                background-color: #282a36;
                border-radius: 0px;
            }
            QLabel {
                color: #f8f8f2;
            }
            QLineEdit {
                border-radius: 5px;
                height: 25px;
                color: #f8f8f2;  /* テキストの色を白に設定 */
            }
            QPushButton {
                border-radius: 5px;
                height: 25px;
                background-color: #6272a4;
                color: #f8f8f2;
            }
            QPushButton:hover {
                background-color: #44475a;
            }
        """)

    def get_mouse_position(self):
        pos = QCursor.pos()
        self.x_input.setText(str(pos.x()))
        self.y_input.setText(str(pos.y()))

    def listen_hotkeys(self):
        import keyboard  # keyboardモジュールを使用

        keyboard.add_hotkey('F9', self.start_actions)
        keyboard.add_hotkey('F10', self.stop_actions)
        keyboard.add_hotkey('F8', self.get_mouse_position_hotkey)
        keyboard.wait()

    def get_mouse_position_hotkey(self):
        pos = pyautogui.position()
        self.mouse_pos_signal.emit(pos.x, pos.y)

    def update_mouse_position(self, x, y):
        self.x_input.setText(str(x))
        self.y_input.setText(str(y))

    def start_actions(self):
        if not self.is_running:
            key = self.key_input.text()
            interval_text = self.interval_input.text()
            x_text = self.x_input.text()
            y_text = self.y_input.text()

            try:
                interval = float(interval_text) / 1000.0
            except ValueError:
                self.status_signal.emit('無効な間隔です')
                return

            if not key and (not x_text or not y_text):
                self.status_signal.emit('キーまたは座標が指定されていません')
                return

            self.is_running = True
            self.status_signal.emit('ステータス: 実行中')
            self.stop_event.clear()

            self.thread = threading.Thread(target=self.perform_actions, args=(key, interval, x_text, y_text))
            self.thread.start()

    def stop_actions(self):
        if self.is_running:
            self.is_running = False
            self.stop_event.set()
            self.thread.join()
            self.status_signal.emit('ステータス: 停止中')

    def perform_actions(self, key_str, interval, x_text, y_text):
        import pyautogui

        if key_str:
            key = key_str
        else:
            key = None

        if x_text and y_text:
            try:
                x = int(x_text)
                y = int(y_text)
                click = True
            except ValueError:
                self.status_signal.emit('無効な座標です')
                self.is_running = False
                return
        else:
            click = False

        while not self.stop_event.is_set():
            if key:
                pyautogui.press(key)
            if click:
                pyautogui.click(x, y)
            time.sleep(interval)

    def update_status(self, status):
        self.status_label.setText(status)

    def closeEvent(self, event):
        self.stop_actions()
        # ホットキーを解除
        import keyboard
        keyboard.unhook_all_hotkeys()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.mouse_pos = event.globalPosition().toPoint()
            event.accept()
            if self.cursor().shape() != Qt.CursorShape.ArrowCursor:
                self.resizing = True
                self.dragging = False

    def mouseMoveEvent(self, event):
        pos = event.globalPosition().toPoint()
        rect = self.geometry()
        if self.resizing:
            delta = pos - self.mouse_pos
            self.resizeWindow(delta)
            self.mouse_pos = pos
            event.accept()
        elif self.dragging:
            self.move(pos - self.drag_position)
            event.accept()
        else:
            self.updateCursorShape(event.globalPosition().toPoint())
            event.accept()

    def mouseReleaseEvent(self, event):
        self.resizing = False
        self.dragging = False
        self.updateCursorShape(event.globalPosition().toPoint())
        event.accept()

    def updateCursorShape(self, global_pos):
        rect = self.geometry()
        x = global_pos.x() - rect.x()
        y = global_pos.y() - rect.y()
        margin = self.margin
        if x < margin and y < margin:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif x > rect.width() - margin and y > rect.height() - margin:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif x < margin and y > rect.height() - margin:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif x > rect.width() - margin and y < margin:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif x < margin:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif x > rect.width() - margin:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif y < margin:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif y > rect.height() - margin:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def resizeWindow(self, delta):
        rect = self.geometry()
        cursor_shape = self.cursor().shape()

        if cursor_shape == Qt.CursorShape.SizeHorCursor:
            if self.mouse_pos.x() < rect.center().x():
                rect.setLeft(rect.left() + delta.x())
            else:
                rect.setRight(rect.right() + delta.x())
        elif cursor_shape == Qt.CursorShape.SizeVerCursor:
            if self.mouse_pos.y() < rect.center().y():
                rect.setTop(rect.top() + delta.y())
            else:
                rect.setBottom(rect.bottom() + delta.y())
        elif cursor_shape == Qt.CursorShape.SizeFDiagCursor:
            if self.mouse_pos.x() < rect.center().x():
                rect.setLeft(rect.left() + delta.x())
                rect.setTop(rect.top() + delta.y())
            else:
                rect.setRight(rect.right() + delta.x())
                rect.setBottom(rect.bottom() + delta.y())
        elif cursor_shape == Qt.CursorShape.SizeBDiagCursor:
            if self.mouse_pos.x() < rect.center().x():
                rect.setLeft(rect.left() + delta.x())
                rect.setBottom(rect.bottom() + delta.y())
            else:
                rect.setRight(rect.right() + delta.x())
                rect.setTop(rect.top() + delta.y())

        min_width = 300
        min_height = 200
        if rect.width() < min_width:
            rect.setWidth(min_width)
        if rect.height() < min_height:
            rect.setHeight(min_height)

        self.setGeometry(rect)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_teal.xml')

    # アプリケーションアイコンの設定
    icon_path = os.path.abspath("./docs/icon.png")  # アイコン画像のパスを設定してください
    app.setWindowIcon(QIcon(icon_path))

    window = AutoClicker()
    window.show()
    sys.exit(app.exec())
