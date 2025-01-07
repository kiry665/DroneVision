from PyQt5 import QtWidgets, QtGui, QtCore, uic
import sys
import os
from ultralytics import YOLO
import json

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("design.ui", self)

        self.actionSelectFolder.triggered.connect(self.select_folder)
        self.actionExit.triggered.connect(self.close)
        self.actionAbout.triggered.connect(self.show_about)
        self.btn_process_gallery.clicked.connect(self.process_gallery)
        self.listView_images.clicked.connect(self.display_preview)

        self.yolo_model = YOLO('best.pt')

        self.coords_data = {}

        self.last_pixmap = None

    def select_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Выбрать папку")
        if folder:
            print(f"Выбрана папка: {folder}")
            model = QtWidgets.QFileSystemModel()
            model.setRootPath(folder)
            self.listView_images.setModel(model)
            self.listView_images.setRootIndex(model.index(folder))
            self.model = model

            coords_file = os.path.join(folder, 'image_coords.json')
            if os.path.exists(coords_file):
                with open(coords_file, 'r') as f:
                    self.coords_data = json.load(f)
                    print("Нашел файл image_coords.json")
            else:
                self.coords_data = {}
                print("Не нашел файл image_coords.json")

    def display_preview(self, index):
        if hasattr(self, "model"):
            file_path = self.model.filePath(index)
            print(f"Выбран файл: {file_path}")

            image_file = os.path.basename(file_path)

            if os.path.isfile(file_path) and file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                pixmap = QtGui.QPixmap(file_path)
                if not pixmap.isNull():
                    self.last_pixmap = pixmap  # Store the pixmap
                    self.update_preview_with_boxes(pixmap, image_file)
                else:
                    self.label_preview.setText("Ошибка загрузки изображения")
            else:
                self.label_preview.setText("Превью недоступно")

    def update_preview(self, pixmap):
        preview_size = self.label_preview.size()

        image_width = pixmap.width()
        image_height = pixmap.height()
        label_width = preview_size.width()
        label_height = preview_size.height()

        scale_factor = min(label_width / image_width, label_height / image_height)

        new_width = int(image_width * scale_factor)
        new_height = int(image_height * scale_factor)

        scaled_pixmap = pixmap.scaled(new_width, new_height, QtCore.Qt.KeepAspectRatio)

        final_pixmap = QtGui.QPixmap(label_width, label_height)
        final_pixmap.fill(QtCore.Qt.white)

        painter = QtGui.QPainter(final_pixmap)
        x_offset = (label_width - new_width) // 2
        y_offset = (label_height - new_height) // 2
        painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
        painter.end()

        self.label_preview.setPixmap(final_pixmap)

    def update_preview_with_boxes(self, pixmap, image_file):
        # Create a QImage from the pixmap
        image = pixmap.toImage()

        # Check if the coordinates for this image exist

        print(image_file)

        if image_file in self.coords_data:
            boxes_coords = self.coords_data[image_file]

            # Create a QPainter to draw on the image
            painter = QtGui.QPainter(image)
            painter.setPen(QtGui.QPen(QtCore.Qt.red, 3))  # Set pen for drawing (red color and 2px width)

            # Draw bounding boxes
            for coords in boxes_coords:
                xmin, ymin, xmax, ymax = coords
                rect = QtCore.QRectF(xmin, ymin, xmax - xmin, ymax - ymin)
                painter.drawRect(rect)

            painter.end()

        # Convert the image back to pixmap
        pixmap_with_boxes = QtGui.QPixmap.fromImage(image)

        # Update the label to display the image with boxes
        self.update_preview(pixmap_with_boxes)

    def resizeEvent(self, event):
        if self.last_pixmap:
            self.update_preview(self.last_pixmap)
        event.accept()

    def process_gallery(self):

        folder_path = self.model.rootPath()

        image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]

        if not image_files:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "В выбранной папке нет изображений!")
            return

        for image_file in image_files:
            image_path = os.path.join(folder_path, image_file)

            results = self.yolo_model(image_path)

            boxes_coords = []

            for result in results:
                boxes = result.boxes
                for box in boxes:

                    coords = box.xyxy[0].cpu().numpy()
                    xmin, ymin, xmax, ymax = coords

                    boxes_coords.append([float(xmin), float(ymin), float(xmax), float(ymax)])

            self.coords_data[image_file] = boxes_coords

        coords_file = os.path.join(folder_path, 'image_coords.json')
        with open(coords_file, 'w') as f:
            json.dump(self.coords_data, f)

        QtWidgets.QMessageBox.information(self, "Завершено", "Обработка изображений завершена!")

    def show_about(self):
        QtWidgets.QMessageBox.information(self, "О программе", "Программа для поиска людей в изображениях.\nВерсия 0.1")


app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())
