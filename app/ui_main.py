from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QComboBox, QMessageBox
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QFile

class MainWindow(QWidget):
    def __init__(self, converter):
        super().__init__()
        self.converter = converter
        self.setWindowTitle("Sound Converter App")
        self.setGeometry(200, 200, 400, 200)
        self.setWindowIcon(QIcon("app/resources/icons/app_icon.png"))

        self.apply_styles()

        layout = QVBoxLayout()

        self.label = QLabel("No file selected")
        layout.addWidget(self.label)

        self.btn_open = QPushButton("Open Audio File")
        self.btn_open.setIcon(QIcon("app/resources/icons/open_file.png"))
        self.btn_open.clicked.connect(self.open_file)
        layout.addWidget(self.btn_open)

        self.format_box = QComboBox()
        self.format_box.addItems(["mp3", "wav", "ogg", "flac"])
        layout.addWidget(self.format_box)

        self.btn_convert = QPushButton("Convert")
        self.btn_convert.setIcon(QIcon("app/resources/icons/convert.png"))
        self.btn_convert.clicked.connect(self.convert_file)
        layout.addWidget(self.btn_convert)

        self.setLayout(layout)
        self.input_file = None

    def apply_styles(self):
        try:
            file = QFile("app/resources/styles.qss")
            if file.open(QFile.ReadOnly):
                style_data = file.readAll().data().decode("utf-8")
                self.setStyleSheet(style_data)
        except Exception as e:
            print("Could not load styles:", e)

    def open_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Audio Files (*.mp3 *.wav *.ogg *.flac)")
        if file:
            self.input_file = file
            self.label.setText(file)

    def convert_file(self):
        if not self.input_file:
            QMessageBox.warning(self, "Error", "No file selected")
            return

        output_format = self.format_box.currentText()
        save_path, _ = QFileDialog.getSaveFileName(self, "Save As", f"output.{output_format}", f"*.{output_format}")
        if save_path:
            ok, msg = self.converter.convert(self.input_file, save_path, output_format)
            if ok:
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.critical(self, "Error", msg)
