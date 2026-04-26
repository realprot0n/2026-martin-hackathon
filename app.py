import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView,
                             QGraphicsScene, QGraphicsTextItem, QLineEdit,
                             QVBoxLayout, QWidget, QFrame, QLabel, QHBoxLayout,
                             QTextBrowser, QSizePolicy, QPushButton)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QPoint
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QGuiApplication

import ai_code

class DescriptionWorker(QObject):
    """
    A worker class designed to run in a separate thread to fetch AI descriptions.
    Prevents the main UI thread from freezing during long-running network calls.
    """
    
    # Signal emitted when the AI generation is complete, carrying the description text
    finished = Signal(str)

    def __init__(self, node_name):
        """
        Initializes the worker with the specific node to be described.

        Args:
            node_name (str): The name of the node for which to generate a description.
        """
        super().__init__()
        self.node_name = node_name

    def run(self):
        """
        Executes the AI fetch logic.
        
        This method should be connected to a QThread's started signal. 
        Once the description is retrieved via ai_code, it emits the 'finished' signal.
        """
        # Triggers the lengthy AI generation process
        description = ai_code.get_long_ai_description(self.node_name)
        
        # Sends the result back to the main thread/UI
        self.finished.emit(description)

class DraggableTextNode(QGraphicsTextItem):
    """
    A visual, interactive UI element representing a Node in a QGraphicsScene.
    Handles dragging, collision detection for merging, and deletion via a trash zone.
    """
    def __init__(self, Node, main_window):
        """
        Initializes the draggable UI component.

        Args:
            Node (Node): The backend data object containing names and descriptions.
            main_window (QMainWindow): Reference to the main application for callback logic.
        """
        super().__init__()
        self.data = Node
        self.main_window = main_window
        self.is_over_trash = False

        # Visual Styling: Bold, 12pt font
        font = self.font()
        font.setPointSize(12)
        font.setBold(True)
        self.setFont(font)

        # Layout: Fixed width with centered HTML content
        self.setTextWidth(180)
        self.update_display_text(show_description=False)
        
        # Interaction Flags: Enable movement, selection, and hover detection
        self.setFlag(QGraphicsTextItem.ItemIsMovable)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

    def paint(self, painter, option, widget):
        """
        Customizes the look of the node box.
        Draws a rounded rectangle background that turns dark red when over the trash.
        """
        rect = self.boundingRect()
        
        # Style logic: Red theme if over trash, dark gray theme otherwise
        bg_color = QColor("#4e0000") if self.is_over_trash else QColor("#333333")
        self.setDefaultTextColor(Qt.white)
        border_color = QColor("#ff4444") if self.is_over_trash else QColor("#bdc3c7")
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 2 if self.is_over_trash else 1))
        painter.drawRoundedRect(rect, 5, 5)
        
        super().paint(painter, option, widget)

    def mouseMoveEvent(self, event):
        """
        Updates the node's position and checks for collisions with the trash icon in real-time.
        """
        super().mouseMoveEvent(event)
        
        was_over = self.is_over_trash
        self.is_over_trash = self.main_window.check_collision_with_trash(self)
        
        # Trigger a repaint only if the "over trash" state changed
        if was_over != self.is_over_trash:
            self.update()

    def mousePressEvent(self, event):
        """Stores the initial click position to differentiate between a click and a drag."""
        self.click_pos = event.scenePos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handles three potential end-of-drag outcomes:
        1. Click: Shows detailed info if the mouse barely moved.
        2. Delete: Removes node if dropped over the trash area.
        3. Merge: Attempts to combine nodes if dropped onto another DraggableTextNode.
        """
        # Case 1: Simple click detection (threshold of 5 pixels)
        if (event.scenePos() - self.click_pos).manhattanLength() < 5:
            self.main_window.show_details(self.data)

        # Case 2: Drop into trash
        if self.main_window.check_collision_with_trash(self):
            self.main_window.clear_details(self.data)
            self.scene().removeItem(self)
            return super().mouseReleaseEvent(event)

        # Case 3: Drop onto another node for merging
        colliding_items = self.scene().items(self.sceneBoundingRect())
        for item in colliding_items:
            if isinstance(item, DraggableTextNode) and item is not self:
                self.main_window.merge_nodes(self, item)
                break 

        super().mouseReleaseEvent(event)
    
    def update_display_text(self, show_description=False):
        """
        Refreshes the node's HTML content.
        
        Args:
            show_description (bool): If True, reveals the short AI description below the name.
        """
        name_color = "white"
        desc_color = "#cccccc"
        
        html = f"<div style='text-align: center; width: 100%;'>"
        html += f"<b style='color: {name_color}; font-size: 13px;'>{self.data.name}</b>"
        if show_description:
            html += f"<br><span style='color: {desc_color}; font-size: 10px;'>{self.data.getShortDescription()}</span>"
        
        html += "</div>"
        self.setHtml(html)

    def hoverEnterEvent(self, event):
        """Expands node content to show description on mouse hover."""
        self.prepareGeometryChange()
        self.update_display_text(show_description=True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Collapses node content to show only the name when mouse leaves."""
        self.prepareGeometryChange()
        self.update_display_text(show_description=False)
        super().hoverLeaveEvent(event)

class InfiniteCanvas(QGraphicsView):
    """
    A custom interactive viewport for navigating a large workspace.
    Supports panning, smooth zooming, and a procedural background grid.
    """
    def __init__(self, scene):
        """
        Sets up the canvas with hidden scrollbars and high-quality rendering.

        Args:
            scene (QGraphicsScene): The scene containing nodes and items.
        """
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        
        # Enables 'Hand' cursor for clicking and dragging the canvas
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # Ensures zooming focuses on the cursor position
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Hides scrollbars for a cleaner, modern look
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Sets background color based on system theme (Dark vs Light)
        color_scheme = QGuiApplication.styleHints().colorScheme()
        self.setBackgroundBrush(QColor("#2a2a2a") if color_scheme == Qt.ColorScheme.Dark else QColor("#fcfcfc"))

    def wheelEvent(self, event):
        """
        Handles mouse wheel scrolling to zoom in and out.
        
        Constraints:
            - Max Zoom: 5.0x
            - Min Zoom: 0.2x
            - Increment: 15% per notch
        """
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        current_zoom = self.transform().m11() # m11 is the X-scale factor
        
        if event.angleDelta().y() > 0 and current_zoom < 5.0:
            self.scale(zoom_in_factor, zoom_in_factor)
        elif event.angleDelta().y() < 0 and current_zoom > 0.2:
            self.scale(zoom_out_factor, zoom_out_factor)

    def drawBackground(self, painter, rect):
        """
        Procedurally draws an infinite light-gray grid pattern.
        Adjusts to the viewport's bounding rectangle during movement.
        """
        painter.setPen(QPen(QColor("#e0e0e0"), 0.5))
        grid_size = 40
        
        # Align grid lines to integer multiples of grid_size
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        
        # Vertical lines
        for x in range(left, int(rect.right()), grid_size):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        
        # Horizontal lines
        for y in range(top, int(rect.bottom()), grid_size):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

class HistoryNodeItem(QGraphicsTextItem):
    """
    A simplified visual representation of a Node specifically for history logs.
    Non-draggable and static compared to DraggableTextNode.
    """
    def __init__(self, node_data, main_window):
        """
        Args:
            node_data (Node): The backend node data.
            main_window (QMainWindow): Reference for showing details on click.
        """
        super().__init__(node_data.name)
        self.node_data = node_data
        self.main_window = main_window
        self.setTextWidth(150)
        
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)

    def paint(self, painter, option, widget):
        """Draws a fixed dark-themed style for history entries."""
        bg_color = QColor("#333333")
        self.setDefaultTextColor(Qt.white)
        
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor("#bdc3c7"), 1))
        painter.drawRoundedRect(self.boundingRect(), 5, 5)
        super().paint(painter, option, widget)

    def mousePressEvent(self, event):
        """Clicking a history item opens its details in the main window."""
        self.main_window.show_details(self.node_data)
        super().mousePressEvent(event)

class OriginSenderButton(QPushButton):
    """
    A navigation button that repositions the InfiniteCanvas view back to (0,0).
    Essentially acts as a 'Home' or 'Reset View' button for the workspace.
    """
    def __init__(self, text: str = "", parent: QWidget | None = None, autoDefault: bool = False, default: bool = False, flat: bool | None = False, infinite_canvas: InfiniteCanvas = None):
        """
        Initializes the button and applies theme-aware styling.

        Args:
            text (str): Label for the button (e.g., "Go to Origin").
            parent (QWidget, optional): The parent widget.
            autoDefault (bool): Whether the button is an auto-default button.
            default (bool): Whether the button is the default button.
            flat (bool): Whether the button border is raised.
            infinite_canvas (InfiniteCanvas): The canvas instance this button will control.
        """
        super().__init__(
            text, 
            parent, 
            autoDefault=autoDefault, 
            default=default, 
            flat=flat
        )
        self.infinite_canvas: InfiniteCanvas = infinite_canvas
        
        # UI Styling: Ensures text is visible (white) when using system dark mode
        color_scheme = QGuiApplication.styleHints().colorScheme()
        if color_scheme == Qt.ColorScheme.Dark:
            self.setStyleSheet("color: white;")
            
        # Connect the click event to the navigation logic
        self.clicked.connect(self.send_user_to_origin)

    def send_user_to_origin(self) -> None:
        """
        Commands the linked InfiniteCanvas to center the viewport on the 
        absolute scene coordinates (0, 0).
        """
        self.infinite_canvas.centerOn(QPoint(0, 0))

class MainWindow(QMainWindow):
    """
    The primary application window for 'Node Explorer'.
    Manages the layout, user input, canvas interaction, and the side details panel.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Node Explorer")
        self.resize(1200, 800)

        # Main Layout Setup: Uses a horizontal layout to split the screen into Canvas and Details
        self.central_widget: QWidget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_h_layout = QHBoxLayout(self.central_widget)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)

        # Left Container: Houses the top input area, the Infinite Canvas, and the History View
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(0)

        # Entry Area: Contains the search/add text field
        self.entry_container = QFrame()
        self.entry_layout = QVBoxLayout(self.entry_container)
        self.text_entry = QLineEdit()
        self.text_entry.setPlaceholderText("Type and press Enter...")
        self.text_entry.setFixedWidth(300)
        
        # Dynamic Styling: Adapts UI colors based on System Dark/Light mode
        color_scheme = QGuiApplication.styleHints().colorScheme()
        if color_scheme == Qt.ColorScheme.Dark:
            self.left_container.setStyleSheet("background-color: #181818;")
            self.entry_container.setStyleSheet("background-color: #181818;")
            self.text_entry.setStyleSheet("padding: 10px; border-radius: 20px; border: 2px solid #444444; margin: 10px; background-color: #2a2a2a; color: white;")
        else:
            self.text_entry.setStyleSheet("padding: 10px; border-radius: 20px; border: 2px solid #eee; margin: 10px;")
        
        # Event Connection: Pressing enter triggers node creation
        self.text_entry.returnPressed.connect(self.add_node)
        self.entry_layout.addWidget(self.text_entry, alignment=Qt.AlignHCenter)
        self.left_layout.addWidget(self.entry_container)

        # Graphics Scene: Defines a massive coordinate space (100,000 x 100,000 units)
        self.scene = QGraphicsScene(-50000, -50000, 100000, 100000)
        self.view = InfiniteCanvas(self.scene) 
        
        # History View: A secondary scene used to view previously created/interacted nodes
        self.history_scene = QGraphicsScene()
        self.history_view = QGraphicsView(self.history_scene)
        self.history_view.setRenderHint(QPainter.Antialiasing)
        self.history_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.history_view.hide() # Hidden by default until toggled

        self.left_layout.addWidget(self.view)
        self.left_layout.addWidget(self.history_view)
        self.main_h_layout.addWidget(self.left_container, stretch=4)

        # Details Panel: Right-side panel for viewing node descriptions and history controls
        self.details_panel = QFrame()
        self.details_panel.setFixedWidth(300)
        self.details_layout = QVBoxLayout(self.details_panel)

        self.history_btn = QPushButton("View Node History")
        self.history_btn.clicked.connect(self.toggle_history)
        self.details_layout.addWidget(self.history_btn)

        # Reset View: Button to snap the camera back to (0,0)
        self.origin_sender_button: OriginSenderButton = OriginSenderButton("Return to origin", infinite_canvas= self.view, parent=self.entry_container)
        self.entry_layout.addWidget(self.origin_sender_button, alignment=Qt.AlignmentFlag.AlignJustify)
        
        # Content Labels: Displaying the name and description of the selected node
        self.detail_title = QLabel("Select a Node")
        self.detail_title.setWordWrap(True)
        self.detail_desc = QTextBrowser()

        self.details_layout.addWidget(self.detail_title)
        self.details_layout.addWidget(self.detail_desc)
        self.main_h_layout.addWidget(self.details_panel)
        
        # Initialize styles for the details panel based on system theme
        self._update_details_panel_style(color_scheme)

        # State Management: Tracking current threads and workers for AI fetching
        self.current_node_data = None
        self.thread = None
        self.worker = None

        # Trash Zone: UI element at the bottom where nodes can be dragged to be deleted
        self.trash_zone = QFrame(self)
        self.trash_zone.setFixedHeight(80)
        self.trash_zone.setStyleSheet("background-color: rgba(255, 100, 100, 50); border-top: 2px solid #ff4444;")
        self.trash_zone.raise_() # Ensure it sits on top of other widgets

        self.total_user_nodes_ever: int = 0

    def toggle_history(self):
        """
        Switches the UI state between the Infinite Canvas and the History Tree view.
        
        Logic:
            - If entering History: Hides entry controls and renders the parent lineage.
            - If entering Canvas: Restores the main workspace and entry bar.
            - Prevents switching to history if no node is currently selected.
        """
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
        """
        Clears the current history scene and initiates a fresh recursive draw 
        of the selected node's ancestry.
        """
        self.history_scene.clear()
        self._draw_history_recursive(self.current_node_data, 0, 0, 200)

    def _draw_history_recursive(self, node, x, y, x_offset):
        """
        A recursive visualization tool that builds a "Family Tree" of ideas.
        
        Args:
            node (Node): The current node to draw.
            x (int): Horizontal position in the scene.
            y (int): Vertical position in the scene.
            x_offset (int): Horizontal spacing for child/parent branches.
            
        Logic:
            - Places a HistoryNodeItem at coordinates.
            - Draws a line connecting the current node to its parents.
            - Recursively calls itself for every parent found in node.parents.
        """
        if not node: return
        item = HistoryNodeItem(node, self)
        self.history_scene.addItem(item)
        item.setPos(x, y)

        parents = getattr(node, 'parents', [])
        for i, parent in enumerate(parents):
            # Calculate positions for parent nodes (branching out)
            new_x = x - x_offset if i == 0 else x + x_offset
            new_y = y + 100
            
            # Draw connection line (using hardcoded offsets to center on the box)
            self.history_scene.addLine(x + 75, y + 30, new_x + 75, new_y, QPen(QColor("#bdc3c7")))
            
            # Recurse deeper into the tree with a reduced horizontal offset
            self._draw_history_recursive(parent, new_x, new_y, x_offset / 1.5)

    def _update_details_panel_style(self, color_scheme):
        """
        Applies a cohesive theme to the right-side details panel.
        
        Dark Mode: Uses #1e1e1e backgrounds with white text.
        Light Mode: Uses #f8f9fa backgrounds with black text.
        """
        if color_scheme == Qt.ColorScheme.Dark:
            self.details_panel.setStyleSheet("background-color: #1e1e1e; border-left: 1px solid #444444; color: white;")
            self.detail_title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: white;")
            self.detail_desc.setStyleSheet("background-color: #2a2a2a; color: white; font-size: 14px; padding: 10px; border-radius: 5px;")
            self.history_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #333333; color: white; border: 1px solid #555555;")
        else:
            self.details_panel.setStyleSheet("background-color: #f8f9fa; border-left: 1px solid #bdc3c7; color: black;")
            self.detail_title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: black;")
            self.detail_desc.setStyleSheet("background: transparent; font-size: 14px; padding: 10px;")
            self.history_btn.setStyleSheet("padding: 10px; font-weight: bold;")
    
    def _cleanup_description_thread(self):
        """
        Safely shuts down background AI threads to prevent memory leaks or 
        crashes during window closing or new node selection.
        """
        if self.thread is not None:
            try:
                if self.thread.isRunning():
                    self.thread.quit()
                    self.thread.wait()
            except RuntimeError:
                # Catch cases where the C++ object was destroyed before the Python object
                pass
        self.thread = None
        self.worker = None

    def _on_description_thread_finished(self):
        """Standard callback to reset thread references once a background task completes."""
        self.thread = None
        self.worker = None
    
    def show_details(self, node_data):
        """
        Updates the details panel with info from the selected node.
        
        Logic:
            - If user-created: Shows a static notice.
            - If cached: Instantly displays the existing long description.
            - If missing: Spawns a background thread to fetch the description via AI.
            - Thread Safety: Cleans up old threads before starting new ones to prevent collisions.
        """
        if not node_data:
            return
        
        # Avoid restarting a fetch that is already in progress for this node
        if self.current_node_data == node_data and self.thread is not None and self.thread.isRunning():
            return
        
        # New selection cleanup
        if self.current_node_data is not node_data:
            self._cleanup_description_thread()
            self.current_node_data = node_data
        
        self.detail_title.setText(node_data.name)
        
        try:
            if getattr(node_data, 'is_user_created', False):
                description = "This is a user generated node."
                self.detail_desc.setMarkdown(description)
            elif node_data.longDescription:
                # Cache-first approach: Never regenerate if data exists
                self.detail_desc.setMarkdown(node_data.longDescription)
            else:
                # Async background fetch
                self.detail_desc.setMarkdown("Loading description...")
                self.worker = DescriptionWorker(node_data.name)
                self.thread = QThread()
                self.worker.moveToThread(self.thread)
                
                # Signal connections for thread lifecycle management
                self.thread.started.connect(self.worker.run)
                self.worker.finished.connect(self.on_description_fetched)
                self.worker.finished.connect(self.thread.quit)
                self.worker.finished.connect(self.worker.deleteLater)
                self.thread.finished.connect(self._on_description_thread_finished)
                self.thread.finished.connect(self.thread.deleteLater)
                self.thread.start()
        except Exception as e:
            description = f"Error loading description: {e}"
            self.detail_desc.setMarkdown(description)

    def on_description_fetched(self, description):
        """Callback for the worker thread; saves and displays the fetched text."""
        if self.current_node_data:
            self.current_node_data.longDescription = description
            self.detail_desc.setMarkdown(description or "No description available.")

    def showEvent(self, event):
        """Ensures the trash zone is correctly sized and positioned when the window opens."""
        super().showEvent(event)
        self.trash_zone.setGeometry(0, self.height() - 80, self.left_container.width(), 80)
        self.trash_zone.raise_()

    def clear_details(self, node_data=None):
        """Resets the details panel to its default empty state."""
        if node_data is None or node_data == self.current_node_data:
            self._cleanup_description_thread()
            self.detail_title.setText("Select a Node")
            self.detail_desc.clear()
            self.current_node_data = None

    def resizeEvent(self, event):
        """Reposition the trash zone dynamically when the window size changes."""
        super().resizeEvent(event)
        if hasattr(self, 'left_container'):
            self.trash_zone.setGeometry(0, self.height() - 80, self.left_container.width(), 80)
        self.trash_zone.raise_()

    def check_collision_with_trash(self, node):
        """
        Calculates if a node is currently hovering over the trash zone.
        
        Logic:
            - Maps the node's bottom-center scene point to viewport coordinates.
            - Returns True if the point falls within the trash area's height at the bottom.
        """
        bottom_center = node.sceneBoundingRect().bottomLeft() + \
                        (node.sceneBoundingRect().bottomRight() - node.sceneBoundingRect().bottomLeft()) / 2
        
        view_point = self.view.mapFromScene(bottom_center)
        if view_point.x() < 0 or view_point.x() > self.left_container.width():
            return False
        return view_point.y() > (self.view.height() - 80)

    def add_node(self):
        """
        Adds a new user-generated node to the center of the current view.
        Clears the input field upon completion.
        """
        text = self.text_entry.text().strip()
        if text:
            # Create backend data
            new_item = ai_code.Node(text, is_user_created=True)
            # Create frontend UI item
            node = DraggableTextNode(new_item, self)
            self.scene.addItem(node)
            self.text_entry.clear()
            
            self.total_user_nodes_ever += 1
            # Place node at the current center of the viewport
            spacing = 50
            center = self.view.mapToScene(self.view.viewport().rect().center())
            center.setY(center.y() + spacing*self.total_user_nodes_ever)
            node.setPos(center)
    
    def merge_nodes(self, node1, node2):
        """
        Combines two nodes to create a new derived idea using AI logic.
        
        Workflow:
            1. Clears current detail panels for both participating nodes.
            2. Calls the backend factory to generate a new Node object.
            3. Spawns a new DraggableTextNode at the position of the second parent.
            4. Deletes the original two nodes from the scene.
            5. Automatically selects and displays details for the newly created node.

        Args:
            node1 (DraggableTextNode): The first parent node.
            node2 (DraggableTextNode): The second parent node.

        Raises:
            NodeWithParentsAlreadyExistsException: Logged if this pair was already combined.
        """
        try:
            # Clean up UI state before modification
            self.clear_details(node1.data)
            self.clear_details(node2.data)

            # Generate the child data object via AI backend
            new_data_obj = ai_code.Node.make_node_from_parents(node1.data, node2.data)
            
            # Create and place the new visual node
            new_node = DraggableTextNode(new_data_obj, self)
            self.scene.addItem(new_node)
            new_node.setPos(node2.pos())
            
            # Remove parents from the workspace
            self.scene.removeItem(node1)
            self.scene.removeItem(node2)
            
            # Focus the UI on the new discovery
            self.show_details(new_data_obj)
            
        except ai_code.NodeWithParentsAlreadyExistsException:
            # Prevents redundant API calls and duplicate nodes
            print("These have already been combined!")
        except Exception as e:
            # General safety net for API or logic failures
            print(f"Merge error: {e}")

# --- Application Entry Point ---
if __name__ == "__main__":
    """
    Standard boilerplate to launch the Qt application.
    Initializes the event loop and displays the MainWindow.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
