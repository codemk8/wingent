#!/usr/bin/env python3
"""
Simplified canvas test - Tkinter version.
"""

import tkinter as tk
import math


class SimpleCanvasWidget(tk.Canvas):
    """Simple canvas for testing."""

    def __init__(self, parent):
        super().__init__(parent, width=800, height=600, bg="#f0f0f0")

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

        # Drag state
        self.dragging_node = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Bind mouse events
        self.bind("<ButtonPress-1>", self.on_mouse_press)
        self.bind("<B1-Motion>", self.on_mouse_drag)
        self.bind("<ButtonRelease-1>", self.on_mouse_release)

        print("Canvas initialized - ready to paint")
        self.draw_canvas()

    def draw_canvas(self):
        """Draw the canvas elements."""
        print("Drawing canvas")

        # Draw arrows first (so they appear behind nodes)
        print(f"Drawing {len(self.links)} links")
        for source_id, target_id in self.links:
            source_node = next(n for n in self.nodes if n["id"] == source_id)
            target_node = next(n for n in self.nodes if n["id"] == target_id)

            # Calculate arrow line positions (center of nodes)
            x1 = source_node["x"] + 75
            y1 = source_node["y"] + 30
            x2 = target_node["x"] + 75
            y2 = target_node["y"] + 30

            # Draw arrow line with arrowhead
            self.create_line(
                x1, y1, x2, y2,
                arrow=tk.LAST,
                fill="#1976D2",
                width=2,
                arrowshape=(15, 20, 6)
            )

        # Draw nodes
        print(f"Drawing {len(self.nodes)} nodes")
        for node in self.nodes:
            x = node["x"]
            y = node["y"]
            w = 150
            h = 60

            # Node rectangle with fill and border
            self.create_rectangle(
                x, y, x + w, y + h,
                fill="#2196F3",
                outline="#000000",
                width=2
            )

            # Node text
            self.create_text(
                x + w/2, y + h/2,
                text=node["name"],
                fill="#FFFFFF",
                font=("Arial", 10, "bold")
            )

        print("Canvas drawing completed")

    def find_node_at_position(self, x, y):
        """Find which node (if any) is at the given position."""
        for node in self.nodes:
            node_x = node["x"]
            node_y = node["y"]
            w = 150
            h = 60

            if node_x <= x <= node_x + w and node_y <= y <= node_y + h:
                return node
        return None

    def on_mouse_press(self, event):
        """Handle mouse button press - start dragging if on a node."""
        node = self.find_node_at_position(event.x, event.y)
        if node:
            self.dragging_node = node
            self.drag_offset_x = event.x - node["x"]
            self.drag_offset_y = event.y - node["y"]
            self.config(cursor="fleur")  # Change cursor to indicate dragging
            print(f"Started dragging {node['name']}")

    def on_mouse_drag(self, event):
        """Handle mouse drag - move the node."""
        if self.dragging_node:
            # Update node position
            self.dragging_node["x"] = event.x - self.drag_offset_x
            self.dragging_node["y"] = event.y - self.drag_offset_y

            # Redraw everything
            self.delete("all")
            self.draw_canvas()

    def on_mouse_release(self, event):
        """Handle mouse button release - stop dragging."""
        if self.dragging_node:
            print(f"Stopped dragging {self.dragging_node['name']}")
            self.dragging_node = None
            self.config(cursor="")  # Reset cursor


class SimpleCanvasApp:
    """Simple test application."""

    def __init__(self, root):
        self.root = root
        self.root.title("Simple Canvas Test")
        self.root.geometry("900x700")

        # Create canvas
        self.canvas = SimpleCanvasWidget(self.root)
        self.canvas.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        print("Application window created")


def main():
    print("Starting Simple Canvas Test")

    root = tk.Tk()
    app = SimpleCanvasApp(root)

    print("Window shown - you should see a canvas with 3 boxes and 2 arrows")
    root.mainloop()


if __name__ == "__main__":
    main()
