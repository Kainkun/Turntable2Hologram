import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QFileDialog,
    QSlider,
    QHBoxLayout,
    QLabel,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt


class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video Player")
        self.setGeometry(100, 100, 800, 600)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)

        self.open_button = QPushButton("Open Video")
        self.open_button.clicked.connect(self.open_file)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.media_player.play)

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.media_player.pause)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.sliderPressed.connect(
            lambda: self.set_frame_position(self.slider.value())
        )
        self.slider.sliderMoved.connect(self.set_frame_position) # Scrubbing updates frame

        self.frame_label = QLabel("Frame: X")

        self.media_player.positionChanged.connect(self.update_slider)
        self.media_player.durationChanged.connect(self.set_slider_range)

        layout = QVBoxLayout()
        layout.addWidget(self.video_widget)
        layout.addWidget(self.slider)
        layout.addWidget(self.frame_label)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.fps = 30  # Default FPS (will be updated)

    def open_file(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)"
        )
        if file_path:
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.media_player.setPosition(0)  # Start at the beginning
            self.update_fps()

    def update_fps(self):
        """Retrieve FPS from video metadata"""
        fps = self.media_player.metaData().value(QMediaMetaData.Key.VideoFrameRate)
        if fps and fps > 0:
            self.fps = fps
        else:
            self.fps = 30  # Fallback to 30 FPS

    def set_slider_range(self, duration):
        """Set slider range based on total frames instead of milliseconds"""
        total_frames = int((duration / 1000) * self.fps)
        self.slider.setRange(0, total_frames)

    def update_slider(self, position):
        """Update slider position based on current frame"""
        if not self.slider.isSliderDown():
            frame_number = int((position / 1000) * self.fps)
            self.slider.setValue(frame_number)
            self.frame_label.setText(f"Frame: {frame_number}")

    def set_frame_position(self, frame_number):
        """Set video position based on frame number"""
        milliseconds = (frame_number / self.fps) * 1000
        self.media_player.setPosition(int(milliseconds))
        self.frame_label.setText(f"Frame: {frame_number}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
