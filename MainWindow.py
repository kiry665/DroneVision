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
        self.actionCloseFolder.triggered.connect(self.close_folder)
        self.actionExit.triggered.connect(self.close)
        self.actionAbout.triggered.connect(self.show_about)
        self.btn_process_gallery.clicked.connect(self.process_gallery)
        self.listView_images.clicked.connect(self.display_preview)

        self.yolo_model = YOLO('best.pt')

        self.coords_data = {}

        self.last_pixmap = None

        self.status_bar.showMessage("Папка не выбрана")

    def select_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Выбрать папку")
        if folder:
            print(f"Выбрана папка: {folder}")
            model = QtWidgets.QFileSystemModel()
            model.setRootPath(folder)
            self.listView_images.setModel(model)
            self.listView_images.setRootIndex(model.index(folder))
            self.model = model

            self.status_bar.showMessage(folder)

            coords_file = os.path.join(folder, 'image_coords.json')
            if os.path.exists(coords_file):
                with open(coords_file, 'r') as f:
                    self.coords_data = json.load(f)
                    print("Нашел файл image_coords.json")
            else:
                self.coords_data = {}
                print("Не нашел файл image_coords.json")

    def close_folder(self):
        model = QtWidgets.QFileSystemModel()
        self.listView_images.setModel(model)
        self.model = model
        self.status_bar.showMessage("Папка не выбрана")

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
                    self.status_bar.showMessage("Ошибка загрузки изображения")
            else:
                self.status_bar.showMessage("Превью недоступно")

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
        #self.update_preview(pixmap_with_boxes)

        # Create a QGraphicsScene for the QGraphicsView
        scene = QtWidgets.QGraphicsScene(self)

        # Create a QGraphicsPixmapItem and add it to the scene
        pixmap_item = QtWidgets.QGraphicsPixmapItem(pixmap_with_boxes)
        scene.addItem(pixmap_item)

        # Set the scene to the graphic_view
        self.graphic_view.setScene(scene)

        self.graphic_view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.graphic_view.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.graphic_view.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.graphic_view.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        self.graphic_view.wheelEvent = self._zoom_graphic_view

        #self.graphic_view.setRenderHint(QtGui.QPainter.Antialiasing)

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

    def _zoom_graphic_view(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.graphic_view.scale(zoom_factor, zoom_factor)


app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())
