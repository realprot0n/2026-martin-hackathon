import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView,
                             QGraphicsScene, QGraphicsTextItem, QLineEdit,
                             QVBoxLayout, QWidget, QFrame, QLabel, QHBoxLayout,
                             QTextBrowser, QSizePolicy, QPushButton)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QPoint
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QGuiApplication

import ai_code

class DescriptionWorker(QObject):
    finished = Signal(str)

    def __init__(self, node_name):
        super().__init__()
        self.node_name = node_name

    def run(self):
        description = ai_code.get_long_ai_description(self.node_name)
        self.finished.emit(description)

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

        self.setTextWidth(180)
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

    def mousePressEvent(self, event):
        self.click_pos = event.scenePos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if (event.scenePos() - self.click_pos).manhattanLength() < 5:
            self.main_window.show_details(self.data)

        if self.main_window.check_collision_with_trash(self):
            self.main_window.clear_details(self.data)
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
        
        html = f"<div style='text-align: center; width: 100%;'>"
        html += f"<b style='color: {name_color}; font-size: 13px;'>{self.data.name}</b>"
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

class HistoryNodeItem(QGraphicsTextItem):
    def __init__(self, node_data, main_window):
        super().__init__(node_data.name)
        self.node_data = node_data
        self.main_window = main_window
        self.setTextWidth(150)
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)

    def paint(self, painter, option, widget):
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#bdc3c7"), 1))
        painter.drawRoundedRect(self.boundingRect(), 5, 5)
        super().paint(painter, option, widget)

    def mousePressEvent(self, event):
        self.main_window.show_details(self.node_data)
        super().mousePressEvent(event)

class OriginSenderButton(QPushButton):
    def __init__(self, text: str = "", parent: QWidget | None = None, autoDefault: bool = False, default: bool = False, flat: bool | None = False, infinite_canvas: InfiniteCanvas = None):
        super().__init__(
            text, 
            parent, 
            autoDefault=autoDefault, 
            default=default, 
            flat=flat
        )
        self.infinite_canvas: InfiniteCanvas = infinite_canvas
        self.clicked.connect(self.send_user_to_origin)

    def send_user_to_origin(self) -> None:
        self.infinite_canvas.centerOn(QPoint(0, 0))  

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Node Explorer")
        self.resize(1200, 800)

        self.central_widget: QWidget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_h_layout = QHBoxLayout(self.central_widget)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)

        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(0)

        self.entry_container = QFrame()
        self.entry_layout = QVBoxLayout(self.entry_container)
        self.text_entry = QLineEdit()
        self.text_entry.setPlaceholderText("Type and press Enter...")
        self.text_entry.setFixedWidth(300)
        self.text_entry.setStyleSheet("padding: 10px; border-radius: 20px; border: 2px solid #eee; margin: 10px;")
        self.text_entry.returnPressed.connect(self.add_node)
        self.entry_layout.addWidget(self.text_entry, alignment=Qt.AlignHCenter)
        self.left_layout.addWidget(self.entry_container)
        

        self.scene = QGraphicsScene(-50000, -50000, 100000, 100000)
        self.view = InfiniteCanvas(self.scene) # Your InfiniteCanvas class
        
        self.history_scene = QGraphicsScene()
        self.history_view = QGraphicsView(self.history_scene)
        self.history_view.setRenderHint(QPainter.Antialiasing)
        self.history_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.history_view.hide()

        self.left_layout.addWidget(self.view)
        self.left_layout.addWidget(self.history_view)
        self.main_h_layout.addWidget(self.left_container, stretch=4)

        self.details_panel = QFrame()
        self.details_panel.setFixedWidth(300)
        self.details_panel.setStyleSheet("background-color: #f8f9fa; border-left: 1px solid #bdc3c7;")
        self.details_layout = QVBoxLayout(self.details_panel)

        self.history_btn = QPushButton("View Node History")
        self.history_btn.setStyleSheet("padding: 10px; font-weight: bold;")
        self.history_btn.clicked.connect(self.toggle_history)
        self.details_layout.addWidget(self.history_btn)

        self.origin_sender_button: OriginSenderButton = OriginSenderButton("Return to origin", infinite_canvas= self.view, parent=self.entry_container)
        self.entry_layout.addWidget(self.origin_sender_button, alignment=Qt.AlignmentFlag.AlignJustify)
        
        self.detail_title = QLabel("Select a Node")
        self.detail_title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        self.detail_title.setWordWrap(True)
        self.detail_desc = QTextBrowser()
        self.detail_desc.setStyleSheet("background: transparent; font-size: 14px; padding: 10px;")

        self.details_layout.addWidget(self.detail_title)
        self.details_layout.addWidget(self.detail_desc)
        self.main_h_layout.addWidget(self.details_panel)

        self.current_node_data = None

        self.trash_zone = QFrame(self)
        self.trash_zone.setFixedHeight(80)
        self.trash_zone.setStyleSheet("background-color: rgba(255, 100, 100, 50); border-top: 2px solid #ff4444;")
        self.trash_zone.raise_()

    def toggle_history(self):
        if self.view.isVisible():
            if not self.current_node_data: return
            self.view.hide()
            self.entry_container.hide()
            self.history_view.show()
            self.history_btn.setText("View Canvas")
            self.render_history_tree()
        else:
            self.history_view.hide()
            self.view.show()
            self.entry_container.show()
            self.history_btn.setText("View Node History")

    def render_history_tree(self):
        self.history_scene.clear()
        self._draw_history_recursive(self.current_node_data, 0, 0, 200)

    def _draw_history_recursive(self, node, x, y, x_offset):
        if not node: return
        item = HistoryNodeItem(node, self)
        self.history_scene.addItem(item)
        item.setPos(x, y)

        parents = getattr(node, 'parents', [])
        for i, parent in enumerate(parents):
            new_x = x - x_offset if i == 0 else x + x_offset
            new_y = y + 100
            self.history_scene.addLine(x + 75, y + 30, new_x + 75, new_y, QPen(QColor("#bdc3c7")))
            self._draw_history_recursive(parent, new_x, new_y, x_offset / 1.5)

    def show_details(self, node_data):
        if not node_data:
            return
            
        self.current_node_data = node_data
        self.detail_title.setText(node_data.name)
        
        try:
            if getattr(node_data, 'is_user_created', False):
                description = "This is a user generated node."
                self.detail_desc.setMarkdown(description)
            elif node_data.longDescription:
                self.detail_desc.setMarkdown(node_data.longDescription)
            else:
                # Start thread to fetch description
                self.detail_desc.setMarkdown("Loading description...")
                self.worker = DescriptionWorker(node_data.name)
                self.thread = QThread()
                self.worker.moveToThread(self.thread)
                self.thread.started.connect(self.worker.run)
                self.worker.finished.connect(self.on_description_fetched)
                self.worker.finished.connect(self.thread.quit)
                self.worker.finished.connect(self.worker.deleteLater)
                self.thread.finished.connect(self.thread.deleteLater)
                self.thread.start()
        except Exception as e:
            description = f"Error loading description: {e}"
            self.detail_desc.setMarkdown(description)


    def on_description_fetched(self, description):
        if self.current_node_data:
            self.current_node_data.longDescription = description
            self.detail_desc.setMarkdown(description or "No description available.")


    def showEvent(self, event):
        super().showEvent(event)
        self.trash_zone.setGeometry(0, self.height() - 80, self.left_container.width(), 80)
        self.trash_zone.raise_()

    def clear_details(self, node_data=None):
        if node_data is None or node_data == self.current_node_data:
            self.detail_title.setText("Select a Node")
            self.detail_desc.clear()
            self.current_node_data = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'left_container'):
            self.trash_zone.setGeometry(0, self.height() - 80, self.left_container.width(), 80)
        self.trash_zone.raise_()

    def check_collision_with_trash(self, node):
        bottom_center = node.sceneBoundingRect().bottomLeft() + \
                        (node.sceneBoundingRect().bottomRight() - node.sceneBoundingRect().bottomLeft()) / 2
        
        view_point = self.view.mapFromScene(bottom_center)
        if view_point.x() < 0 or view_point.x() > self.left_container.width():
            return False
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
            self.clear_details(node1.data)
            self.clear_details(node2.data)

            new_data_obj = ai_code.Node.make_node_from_parents(node1.data, node2.data)
            
            new_node = DraggableTextNode(new_data_obj, self)
            self.scene.addItem(new_node)
            new_node.setPos(node2.pos())
            
            self.scene.removeItem(node1)
            self.scene.removeItem(node2)
            
            self.show_details(new_data_obj)
            
        except ai_code.NodeWithParentsAlreadyExistsException:
            print("These have already been combined!")
        except Exception as e:
            print(f"Merge error: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
