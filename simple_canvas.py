#!/usr/bin/env python3
"""
Simplified canvas test - Debug version to verify painting works.
"""

import sys
import math
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush

class SimpleCanvasWidget(QWidget):
    """Simple canvas for testing."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #ffffff;")

        # Simple node positions
        self.nodes = [
            {"name": "Input", "x": 50, "y": 100, "id": "node1"},
            {"name": "Process", "x": 300, "y": 100, "id": "node2"},
            {"name": "Output", "x": 550, "y": 100, "id": "node3"},
        ]

        # Simple links
        self.links = [
            ("node1", "node2"),
            ("node2", "node3"),
        ]

        print("Canvas initialized - ready to paint")

    def paintEvent(self, event):
        """Paint the canvas."""
        print("paintEvent called")

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), QColor("#f0f0f0"))

        # Draw arrows
        print(f"Drawing {len(self.links)} links")
        for source_id, target_id in self.links:
            source_node = next(n for n in self.nodes if n["id"] == source_id)
            target_node = next(n for n in self.nodes if n["id"] == target_id)

            # Draw arrow line
            x1 = source_node["x"] + 75
            y1 = source_node["y"] + 30
            x2 = target_node["x"] + 75
            y2 = target_node["y"] + 30

            pen = QPen(QColor("#1976D2"), 2)
            painter.setPen(pen)
            painter.drawLine(x1, y1, x2, y2)

            # Draw arrowhead
            angle = math.atan2(y2 - y1, x2 - x1)
            arrow_size = 15

            p1_x = x2 - arrow_size * math.cos(angle - math.pi / 6)
            p1_y = y2 - arrow_size * math.sin(angle - math.pi / 6)

            p2_x = x2 - arrow_size * math.cos(angle + math.pi / 6)
            p2_y = y2 - arrow_size * math.sin(angle + math.pi / 6)

            painter.setBrush(QBrush(QColor("#1976D2")))
            painter.drawPolygon([
                QPoint(int(x2), int(y2)),
                QPoint(int(p1_x), int(p1_y)),
                QPoint(int(p2_x), int(p2_y))
            ])

        # Draw nodes
        print(f"Drawing {len(self.nodes)} nodes")
        for node in self.nodes:
            x = node["x"]
            y = node["y"]
            w = 150
            h = 60

            # Node background
            painter.fillRect(x, y, w, h, QColor("#2196F3"))

            # Node border
            painter.setPen(QPen(QColor("#000000"), 2))
            painter.drawRect(x, y, w, h)

            # Node text
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(x + 5, y + 20, w - 10, h - 10,
                           Qt.AlignCenter, node["name"])

        print("paintEvent completed")

class SimpleCanvasApp(QMainWindow):
    """Simple test application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Canvas Test")
        self.setGeometry(100, 100, 900, 700)

        # Create canvas
        self.canvas = SimpleCanvasWidget()

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        print("Application window created")

def main():
    print("Starting Simple Canvas Test")
    app = QApplication(sys.argv)

    window = SimpleCanvasApp()
    window.show()
    print("Window shown - you should see a canvas with 3 boxes and 2 arrows")

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
