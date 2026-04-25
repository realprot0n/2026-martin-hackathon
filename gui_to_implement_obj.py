import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView,
                             QGraphicsScene, QGraphicsTextItem, QLineEdit,
                             QVBoxLayout, QWidget, QFrame)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QGuiApplication

import ai_code

class DraggableTextNode(QGraphicsTextItem):
    def __init__(self, Node, main_window):
        super().__init__()
        self.data = Node
        self.main_window = main_window
        self.is_over_trash = False

        font = self.font()
        font.setPointSize(12)
        font.setBold(True)
        self.setFont(font)

        self.update_display_text(show_description=False)
        
        self.setFlag(QGraphicsTextItem.ItemIsMovable)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

    def paint(self, painter, option, widget):
        rect = self.boundingRect()
        color_scheme = QGuiApplication.styleHints().colorScheme()

        if color_scheme == Qt.ColorScheme.Dark:
            bg_color = QColor("#4e0000") if self.is_over_trash else QColor("#333333")
            self.setDefaultTextColor(Qt.white) # Set text to white for dark mode
        else:
            bg_color = QColor("#ffcccc") if self.is_over_trash else QColor("white")
            self.setDefaultTextColor(Qt.black) # Set text to black for light mode
            
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
            return super().mouseReleaseEvent(event)

        colliding_items = self.scene().items(self.sceneBoundingRect())
        for item in colliding_items:
            if isinstance(item, DraggableTextNode) and item is not self:
                self.main_window.merge_nodes(self, item)
                break 

        super().mouseReleaseEvent(event)
    
    def update_display_text(self, show_description=False):
        color_scheme = QGuiApplication.styleHints().colorScheme()
        is_dark = (color_scheme == Qt.ColorScheme.Dark)
        
        name_color = "white" if is_dark else "black"
        desc_color = "#aaaaaa" if is_dark else "#555555"
        
        html = f"<div style='text-align: center;'>"
        html += f"<b style='color: {name_color}; font-size: 14px;'>{self.data.name}</b>"
        
        if show_description:
            html += f"<br><span style='color: {desc_color}; font-size: 10px;'>{self.data.getShortDescription()}</span>"
        
        html += "</div>"
        self.setHtml(html)

    def hoverEnterEvent(self, event):
        self.prepareGeometryChange()
        self.update_display_text(show_description=True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.prepareGeometryChange()
        self.update_display_text(show_description=False)
        super().hoverLeaveEvent(event)

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
        self.text_entry.setStyleSheet("padding: 10px; border-radius: 20px; border: 2px solid #eee;")
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
        bottom_center = node.sceneBoundingRect().bottomLeft() + \
                        (node.sceneBoundingRect().bottomRight() - node.sceneBoundingRect().bottomLeft()) / 2
        
        view_point = self.view.mapFromScene(bottom_center)
        return view_point.y() > (self.view.height() - 80)

    def add_node(self):
        text = self.text_entry.text().strip()
        if text:
            new_item = ai_code.Node(text, is_user_created=True)
            node = DraggableTextNode(new_item, self)
            self.scene.addItem(node)
            self.text_entry.clear()
            center = self.view.mapToScene(self.view.viewport().rect().center())
            node.setPos(center)
    
    def merge_nodes(self, node1, node2):
        try:
            new_data_obj = ai_code.Node.make_node_from_parents(node1.data.name, node2.data.name)
            
            new_node = DraggableTextNode(new_data_obj, self)
            self.scene.addItem(new_node)
            new_node.setPos(node2.pos())
            
            self.scene.removeItem(node1)
            self.scene.removeItem(node2)
            
        except ai_code.NodeWithParentsAlreadyExistsException:
            print("These have already been combined!")
        except Exception as e:
            print(f"Merge error: {e}")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
