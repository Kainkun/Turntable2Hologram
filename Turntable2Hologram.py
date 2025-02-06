import sys
import os
import shutil
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QMessageBox,
    QRadioButton,
    QCheckBox,
    QSpinBox,
)
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QPalette, QColor
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from moviepy.video.io.VideoFileClip import VideoFileClip
from superqt import QLabeledRangeSlider
from PIL import Image
import imagehash
import atexit

TEMP_FOLDER = "_tempFrames"
SUPPORTED_EXPORT_FORMATS = (".png", ".jpg", ".jpeg", ".bmp")
TEMP_FRAME_FORMAT = "jpeg"
HOLOGRAM_FRAME_FORMAT = "jpeg"


def compareImages(imageA, imageB):
    # Get the average hashes of both images
    hash0 = imagehash.phash(Image.open(imageA), hash_size=32)
    hash1 = imagehash.phash(Image.open(imageB), hash_size=32)
    cutoff = 10  # Can be changed according to what works best for your images

    hashDiff = hash0 - hash1  # Finds the distance between the hashes of images
    print(imageA, imageB, hashDiff)
    return hashDiff < cutoff


class crange:
    def __init__(self, start, stop, step=None, modulo=None):
        if step == 0:
            raise ValueError("crange() arg 3 must not be zero")

        if step is None and modulo is None:
            self.start = 0
            self.stop = start
            self.step = 1
            self.modulo = stop
        else:
            self.start = start
            self.stop = stop
            if modulo is None:
                self.step = 1
                self.modulo = step
            else:
                self.step = step
                self.modulo = modulo

    def __iter__(self):
        n = self.start
        if self.step > 0:
            if n > self.stop:
                while n < self.modulo:
                    yield n
                    n += self.step
                n = 0
            while n < self.stop:
                yield n
                n += self.step
        else:
            if n < self.stop:
                while n >= 0:
                    yield n
                    n += self.step
                n = self.modulo - 1
            while n > self.stop:
                yield n
                n += self.step

    def __contains__(self, n):
        if self.start >= self.stop:
            return self.start <= n < self.modulo or 0 <= n < self.stop
        else:
            return self.start <= n < self.stop


class VideoToImageThread(QThread):
    percent_signal = pyqtSignal(float)
    frame_exported_signal = pyqtSignal(str, int)
    completed_signal = pyqtSignal()
    stopped_signal = pyqtSignal()

    def __init__(self, video_path, output_folder):
        super().__init__()
        atexit.register(self.cleanup)
        self.video_path = video_path
        self.output_folder = output_folder
        self.running = True
        self.num_digits = None
        self.previous_image_path = None

    def cleanup(self):
        shutil.rmtree(TEMP_FOLDER, ignore_errors=True)

    def run(self):
        video = VideoFileClip(self.video_path)
        total_frames = int(video.fps * video.duration)
        self.num_digits = len(str(total_frames))

        os.makedirs(self.output_folder, exist_ok=True)

        for i, frame in enumerate(video.iter_frames()):
            if not self.running:
                self.stopped_signal.emit()
                video.close()
                return

            frame_path = os.path.join(
                self.output_folder, f"frame{i:0{self.num_digits}d}.{TEMP_FRAME_FORMAT}"
            )
            VideoFileClip.save_frame(video, frame_path, t=i / video.fps)
            if not self.previous_image_path or not compareImages(
                self.previous_image_path, frame_path
            ):
                self.frame_exported_signal.emit(frame_path, i)
                self.previous_image_path = frame_path
            self.percent_signal.emit((i + 1) / float(total_frames))

        video.close()
        self.completed_signal.emit()

    def stop(self):
        self.running = False


class Turntable2Hologram(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Turntable2Hologram")
        self.setGeometry(100, 100, 800, 600)

        self.valid_frames = []
        self.start_frame = 0
        self.end_frame = 0
        self.current_slider_handle = 0

        self.videoToImageThread = None

        self.init_ui()
        self.set_placeholder_image()
        self.update_ui_state()

        self.setAcceptDrops(True)

    def init_ui(self):

        self.image_title = QLabel()
        self.image_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.open_button = QPushButton("Load Turntable Video")
        self.open_button.clicked.connect(self.open_video)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setVisible(False)
        self.stop_button.clicked.connect(self.stop_import)

        self.convert_button = QPushButton("Convert")
        self.convert_button.clicked.connect(self.convert)

        self.range_slider = QLabeledRangeSlider(Qt.Orientation.Horizontal)
        self.range_slider.setRange(0, 0)
        self.range_slider.valueChanged.connect(self.set_image_range)
        self.range_slider._min_label.setDisabled(True)
        self.range_slider._max_label.setDisabled(True)

        self.loop_around_checkbox = QCheckBox("Flip Start and End Frames")

        self.clockwise_radio = QRadioButton("Clockwise")
        self.clockwise_radio.setChecked(True)
        self.counter_clickwise_radio = QRadioButton("Counter Clockwise")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        self.prev_button = QPushButton("Previous Frame")
        self.prev_button.clicked.connect(self.prev_frame)

        self.next_button = QPushButton("Next Frame")
        self.next_button.clicked.connect(self.next_frame)

        layout = QVBoxLayout()
        layout.addWidget(self.image_title)
        layout.addWidget(self.image_label)

        layout.addWidget(self.clockwise_radio)
        layout.addWidget(self.counter_clickwise_radio)
        layout.addWidget(self.range_slider)

        frame_layout = QHBoxLayout()
        frame_layout.addWidget(self.loop_around_checkbox)
        frame_layout.addStretch()
        frame_layout.addWidget(self.prev_button)
        frame_layout.addWidget(self.next_button)
        layout.addLayout(frame_layout)

        padding_layout = QHBoxLayout()
        padding_label = QLabel("Padding")
        padding_layout.addWidget(padding_label)
        self.padding_spinbox = QSpinBox()
        padding_layout.addWidget(self.padding_spinbox)
        padding_layout.addStretch()
        layout.addLayout(padding_layout)

        layout.addStretch()
        layout.addWidget(self.progress_bar)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()
        button_layout.addWidget(self.convert_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if len(event.mimeData().urls()) == 1:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        file = event.mimeData().urls()[0].toLocalFile()
        self.start_frame_import(file)

    def on_import_done(self):
        self.progress_bar.setVisible(False)
        self.stop_button.setVisible(False)
        self.open_button.setDisabled(False)

        if self.valid_frames:
            self.range_slider.setRange(0, len(self.valid_frames) - 1)
            self.range_slider.setValue((0, len(self.valid_frames) - 1))
            self.start_frame = 0
            self.end_frame = len(self.valid_frames) - 1
            self.update_image_by_index(0)
        else:
            self.set_placeholder_image()

        self.update_ui_state()

    def on_frame_exported(self, path, index):
        self.valid_frames.append(path)
        self.update_image_by_index(-1)

    def open_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)"
        )
        if file_path:
            self.start_frame_import(file_path)

    def start_frame_import(self, video_path):
        """Start importing frames from the selected video"""

        # Clear previous frames
        shutil.rmtree(TEMP_FOLDER, ignore_errors=True)
        os.makedirs(TEMP_FOLDER, exist_ok=True)
        self.valid_frames = []
        self.start_frame = 0
        self.end_frame = 0
        self.range_slider.setRange(0, 0)
        self.update_ui_state()

        self.image_title.setText(os.path.basename(video_path))
        self.set_placeholder_image()  # Keep placeholder visible during loading
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.stop_button.setVisible(True)
        self.open_button.setDisabled(True)

        self.videoToImageThread = VideoToImageThread(video_path, TEMP_FOLDER)
        self.videoToImageThread.frame_exported_signal.connect(self.on_frame_exported)
        self.videoToImageThread.percent_signal.connect(
            lambda percent: self.progress_bar.setValue(int(percent * 100))
        )
        self.videoToImageThread.completed_signal.connect(self.on_import_done)
        self.videoToImageThread.stopped_signal.connect(self.on_import_done)
        self.videoToImageThread.start()

    def stop_import(self):
        """Stop ongoing frame import"""
        if self.videoToImageThread and self.videoToImageThread.isRunning():
            self.videoToImageThread.stop()

    def update_image_by_index(self, index):
        index = index % len(self.valid_frames)

        # have images fill up as its being imported
        if self.valid_frames:
            pixmap = QPixmap(self.valid_frames[index])
            self.image_label.setPixmap(
                pixmap.scaled(
                    self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio
                )
            )
        else:
            self.set_placeholder_image()

    def set_image_range(self, values):
        """Update the start and end frame indices based on slider values."""
        start_frame, end_frame = values
        if start_frame != self.start_frame and end_frame != self.end_frame:
            self.start_frame = start_frame
            self.end_frame = end_frame
            self.update_image_by_index(
                end_frame if self.current_slider_handle else start_frame
            )
        elif start_frame != self.start_frame:
            self.start_frame = start_frame
            self.current_slider_handle = 0
            self.update_image_by_index(self.start_frame)
        elif end_frame != self.end_frame:
            self.end_frame = end_frame
            self.current_slider_handle = 1
            self.update_image_by_index(self.end_frame)

    def next_frame(self):
        current_index = (
            self.end_frame if self.current_slider_handle else self.start_frame
        )

        if current_index < len(self.valid_frames) - 1:
            current_index += 1
            self.update_image_by_index(current_index)
            slider_value = (
                (self.start_frame, current_index)
                if self.current_slider_handle
                else (current_index, self.end_frame)
            )
            self.range_slider.setValue(slider_value)

    def prev_frame(self):
        current_index = (
            self.end_frame if self.current_slider_handle else self.start_frame
        )

        if current_index > 0:
            current_index -= 1
            self.update_image_by_index(current_index)
            slider_value = (
                (self.start_frame, current_index)
                if self.current_slider_handle
                else (current_index, self.end_frame)
            )
            self.range_slider.setValue(slider_value)

    def set_placeholder_image(self):
        """Set a persistent blank gray placeholder image"""
        width, height = 400, 300
        placeholder = QImage(width, height, QImage.Format.Format_RGB32)
        placeholder.fill(Qt.GlobalColor.lightGray)
        pixmap = QPixmap.fromImage(placeholder)
        self.image_label.setPixmap(pixmap)

    def update_ui_state(self):
        has_valid_frames = bool(self.valid_frames)
        self.range_slider.setEnabled(has_valid_frames)
        self.prev_button.setEnabled(has_valid_frames)
        self.next_button.setEnabled(has_valid_frames)
        self.convert_button.setEnabled(has_valid_frames)
        self.stop_button.setVisible(
            False if has_valid_frames else self.stop_button.isVisible()
        )

    def convert(self):
        if not self.valid_frames:
            return

        video_name = os.path.splitext(
            os.path.basename(self.videoToImageThread.video_path)
        )[0]

        output_folder = os.path.join(os.getcwd(), "Converted Holograms", f"{video_name}_hologram")

        counter = 1
        new_output_folder = output_folder
        while os.path.exists(new_output_folder):
            new_output_folder = f"{output_folder}_{counter}"
            counter += 1
        os.makedirs(new_output_folder)
        output_folder = new_output_folder

        if not self.loop_around_checkbox.isChecked():
            start_frame, end_frame = self.start_frame, self.end_frame
        else:
            start_frame, end_frame = self.end_frame, self.start_frame

        if self.clockwise_radio.isChecked():
            frame_range = crange(start_frame, end_frame + 1, 1, len(self.valid_frames))
        elif self.counter_clickwise_radio.isChecked():
            frame_range = crange(end_frame, start_frame - 1, -1, len(self.valid_frames))
        else:
            raise ValueError("Invalid rotation direction")

        padding_amount = self.padding_spinbox.value()
        num_digits = len(str(end_frame - start_frame + 1 + (padding_amount * 2)))

        for i in range(padding_amount):
            src_path = self.valid_frames[start_frame]
            dst_path = os.path.join(
                output_folder,
                f"frame{i:0{num_digits}d}.{HOLOGRAM_FRAME_FORMAT}",
            )
            shutil.copyfile(src_path, dst_path)

        for export_index, imported_index in enumerate(frame_range):
            src_path = self.valid_frames[imported_index]
            dst_path = os.path.join(
                output_folder,
                f"frame{padding_amount + export_index:0{num_digits}d}.{HOLOGRAM_FRAME_FORMAT}",
            )
            shutil.copyfile(src_path, dst_path)

        for i in range(padding_amount):
            src_path = self.valid_frames[end_frame]
            dst_path = os.path.join(
                output_folder,
                f"frame{padding_amount + len(list(frame_range)) + i:0{num_digits}d}.{HOLOGRAM_FRAME_FORMAT}",
            )
            shutil.copyfile(src_path, dst_path)

        print(
            f"Exported frames {start_frame} to {end_frame} to folder: {output_folder}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = Turntable2Hologram()
    player.show()
    sys.exit(app.exec())
