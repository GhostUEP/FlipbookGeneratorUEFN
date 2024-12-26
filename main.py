import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QProgressBar, QComboBox, QWidget, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPalette, QColor, QPixmap, QIcon
from PIL import Image

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int, str)

    def __init__(self, images_folder, output_image_path, frames):
        super().__init__()
        self.images_folder = images_folder
        self.output_image_path = output_image_path
        self.frames = frames

    def run(self):
        try:
            columns = int((self.frames * 5 / 4) ** 0.5)
            rows = (self.frames + columns - 1) // columns

            while columns * rows < self.frames:
                columns += 1

            target_size = (7680 // columns, 6144 // rows)

            images = [
                Image.open(os.path.join(self.images_folder, img)).resize(target_size)
                for img in sorted(os.listdir(self.images_folder))[:self.frames]
            ]

            output_image = Image.new("RGBA", (7680, 6144))

            for index, image in enumerate(images):
                x = (index % columns) * target_size[0]
                y = (index // columns) * target_size[1]
                output_image.paste(image, (x, y), image)
                self.progress.emit((index + 1) * 100 // self.frames)

            output_image.save(self.output_image_path, "PNG")
            self.finished.emit(columns, rows, self.output_image_path)
        except Exception as e:
            print(f"Error: {e}")

class FinishedDialog(QDialog):
    def __init__(self, columns, rows, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Process Completed")
        self.setWindowIcon(QIcon("icon.ico"))
        self.setFixedSize(800, 480)
        self.setStyleSheet("background-color: white; color: black;")

        layout = QVBoxLayout()

        label = QLabel(f"Image saved successfully!\nGrid dimensions: {columns} columns x {rows} rows.")
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(label, alignment=Qt.AlignCenter)

        image_label = QLabel()
        pixmap = QPixmap(image_path).scaled(640, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        layout.addWidget(image_label, alignment=Qt.AlignCenter)

        self.setLayout(layout)

class FlipbookApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unreal Flipbook Generator")
        self.setWindowIcon(QIcon("icon.ico"))
        self.setGeometry(200, 200, 1280, 720)
        self.setFixedSize(1280, 720)
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()

        # Image Directory
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("Image Directory:")
        self.dir_input = QLineEdit()
        self.dir_input.setStyleSheet("color: blue; selection-background-color: #444;")
        self.dir_browse = QPushButton("Browse")
        self.style_button(self.dir_browse)
        self.dir_browse.clicked.connect(self.choose_directory)

        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.dir_browse)

        # Output File
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Output File:")
        self.file_input = QLineEdit()
        self.file_input.setStyleSheet("color: blue; selection-background-color: #444;")
        self.file_browse = QPushButton("Browse")
        self.style_button(self.file_browse)
        self.file_browse.clicked.connect(self.choose_output_file)

        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.file_browse)

        # Frame Selection
        frame_layout = QHBoxLayout()
        self.frame_label = QLabel("Number of Frames:")
        self.frame_combo = QComboBox()
        self.frame_combo.addItems(["12", "24", "48", "60", "90", "120", "150", "180"])
        self.style_combo(self.frame_combo)

        frame_layout.addWidget(self.frame_label)
        frame_layout.addWidget(self.frame_combo)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar {border: 2px solid #444; border-radius: 5px; text-align: center;} QProgressBar::chunk {background-color: #28a745; width: 10px;}")

        # Start Button
        self.start_button = QPushButton("Start")
        self.style_button(self.start_button, color="#28a745", hover_color="#1e7e34")
        self.start_button.clicked.connect(self.start_process)

        # Add widgets to layout
        self.layout.addLayout(dir_layout)
        self.layout.addLayout(file_layout)
        self.layout.addLayout(frame_layout)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.start_button)

        # Set main widget
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def style_button(self, button, color="#007bff", hover_color="#0056b3"):
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 15px;
                padding: 10px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)

    def style_combo(self, combo):
        combo.setStyleSheet("QComboBox {background-color: #444; color: white; border-radius: 5px; padding: 5px;}")

    def choose_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            self.dir_input.setText(folder)

    def choose_output_file(self):
        file, _ = QFileDialog.getSaveFileName(self, "Save File", filter="PNG Files (*.png)")
        if file:
            self.file_input.setText(file)

    def start_process(self):
        images_folder = self.dir_input.text()
        output_image_path = self.file_input.text()
        frames = int(self.frame_combo.currentText())

        if not os.path.isdir(images_folder):
            print("Invalid image directory.")
            return

        if not output_image_path.endswith(".png"):
            print("The output file must have a .png extension.")
            return

        self.disable_inputs()

        self.worker = WorkerThread(images_folder, output_image_path, frames)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.show_finished_dialog)
        self.worker.start()

    def disable_inputs(self):
        self.dir_input.setDisabled(True)
        self.file_input.setDisabled(True)
        self.dir_browse.setDisabled(True)
        self.file_browse.setDisabled(True)
        self.frame_combo.setDisabled(True)
        self.start_button.setDisabled(True)

    def enable_inputs(self):
        self.dir_input.setDisabled(False)
        self.file_input.setDisabled(False)
        self.dir_browse.setDisabled(False)
        self.file_browse.setDisabled(False)
        self.frame_combo.setDisabled(False)
        self.start_button.setDisabled(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def show_finished_dialog(self, columns, rows, image_path):
        dialog = FinishedDialog(columns, rows, image_path, self)
        dialog.exec_()
        self.enable_inputs()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#1e1e1e"))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor("#2e2e2e"))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor("#444"))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.Highlight, QColor("#28a745"))
    palette.setColor(QPalette.HighlightedText, Qt.black)

    app.setPalette(palette)

    window = FlipbookApp()
    window.show()
    sys.exit(app.exec_())
