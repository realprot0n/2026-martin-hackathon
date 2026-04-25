import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView,
                             QGraphicsScene, QGraphicsTextItem, QLineEdit,
                             QVBoxLayout, QWidget, QFrame)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QBrush, QColor, QPen

import ai_code

class DraggableTextNode(QGraphicsTextItem):
    def __init__(self, Node, main_window):
        super().__init__(Node.name) 

        self.data = Node
        self.main_window = main_window
        
        font = self.font()
        font.setPointSize(12)
        font.setBold(True)
        self.setFont(font)
        
        self.is_over_trash = False

        self.setFlag(QGraphicsTextItem.ItemIsMovable)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable)

    def paint(self, painter, option, widget):
        rect = self.boundingRect()
        
        bg_color = QColor("#ffcccc") if self.is_over_trash else QColor("white")
        border_color = QColor("#ff4444") if self.is_over_trash else QColor("#bdc3c7")
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 2 if self.is_over_trash else 1))
        painter.drawRoundedRect(rect, 5, 5)
        
        super().paint(painter, option, widget)



    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        
        was_over = self.is_over_trash
        self.is_over_trash = self.main_window.check_collision_with_trash(self)
        
        if was_over != self.is_over_trash:
            self.update()

    def mouseReleaseEvent(self, event):
        if self.main_window.check_collision_with_trash(self):
            self.scene().removeItem(self)
        super().mouseReleaseEvent(event)

class InfiniteCanvas(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor("#fcfcfc"))

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        current_zoom = self.transform().m11()
        
        if event.angleDelta().y() > 0 and current_zoom < 5.0:
            self.scale(zoom_in_factor, zoom_in_factor)
        elif event.angleDelta().y() < 0 and current_zoom > 0.2:
            self.scale(zoom_out_factor, zoom_out_factor)

    def drawBackground(self, painter, rect):
        painter.setPen(QPen(QColor("#e0e0e0"), 0.5))
        grid_size = 40
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        for x in range(left, int(rect.right()), grid_size):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        for y in range(top, int(rect.bottom()), grid_size):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("test gui")
        self.resize(1000, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.entry_container = QFrame()
        self.entry_layout = QVBoxLayout(self.entry_container)
        self.text_entry = QLineEdit()
        self.text_entry.setPlaceholderText("type box")
        self.text_entry.setFixedWidth(300)
        self.text_entry.setStyleSheet("padding: 10px; border-radius: 20px; border: 2px solid #eee; background: white;")
        self.text_entry.returnPressed.connect(self.add_node)
        self.entry_layout.addWidget(self.text_entry, alignment=Qt.AlignHCenter)
        self.layout.addWidget(self.entry_container)

        self.scene = QGraphicsScene(-50000, -50000, 100000, 100000)
        self.view = InfiniteCanvas(self.scene)
        self.layout.addWidget(self.view)

        self.trash_zone = QFrame(self)
        self.trash_zone.setFixedHeight(80)
        self.trash_zone.setStyleSheet("background-color: rgba(255, 100, 100, 50); border-top: 2px solid #ff4444;")

    def resizeEvent(self, event):
        self.trash_zone.setGeometry(0, self.height() - 80, self.width(), 80)
        super().resizeEvent(event)

    def check_collision_with_trash(self, node):
        node_rect_in_view = self.view.mapFromScene(node.sceneBoundingRect()).boundingRect()
        
        return node_rect_in_view.bottom() > (self.view.height() - 80)

    def add_node(self):
        text = self.text_entry.text().strip()
        if text:
            new_item = ai_code.Node(text)
            node = DraggableTextNode(new_item, self)
            self.scene.addItem(node)
            self.text_entry.clear()
            center = self.view.mapToScene(self.view.viewport().rect().center())
            node.setPos(center)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
