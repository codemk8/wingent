# Multi-Window Process GUI with Drag-and-Drop Links

A Python GUI application using PyQt5 that allows you to create multiple independent windows representing processes and establish communication channels between them via drag-and-drop.

## Features

✅ **Multiple Independent Windows** - Create any number of process windows
✅ **Drag-and-Drop Link Creation** - Click and drag between windows to create links
✅ **Bidirectional Link Tracking** - Incoming links (green) and outgoing links (blue)
✅ **Message Logging** - Each window logs link creation events
✅ **Clean Architecture** - Minimal, extensible code (~170 lines core)

## Installation

### Option 1: Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PyQt5
pip install PyQt5
```

### Option 2: Using Homebrew + pipx

```bash
brew install pipx
pipx install PyQt5
```

## Usage

### Run the Main Application

```bash
# Using the virtual environment
source venv/bin/activate
python3 process_gui.py
```

This launches 4 pre-configured process windows:
- Parser
- Validator
- Transformer
- Output Handler

### Run the Demo Script

```bash
# Interactive mode (default) - drag to create links
python3 demo_usage.py

# Auto mode - programmatically creates links
python3 demo_usage.py --mode auto
```

### Run the Drag-Drop Test

```bash
# Test drag-drop functionality with simple windows
python3 test_drag_drop.py
```

## How to Use

1. **Open the application** - 4 windows appear automatically
2. **Create links** - Click and drag the blue "Drag me to create link" button from one window to another
3. **Drop to connect** - Release the mouse over another window to create a communication link
4. **View results** - The receiving window shows green incoming links, the source shows blue outgoing links

## Code Structure

### Core Classes

**`DraggableButton`** - Custom QPushButton with drag support
- Handles mouse press events to initiate drag
- Encodes window ID in MIME data for drop detection

**`ProcessWindow`** - Main window class
- Represents a process
- Displays incoming/outgoing links
- Accepts drops to create new links
- Logs messages about link creation

**`ProcessApp`** - Application controller
- Manages all open windows
- Handles link creation notifications
- Tracks window relationships

## Example: Programmatic Link Creation

```python
from process_gui import ProcessApp

app = ProcessApp()

# Create windows
parser = app.create_window("Parser")
validator = app.create_window("Validator")
transformer = app.create_window("Transformer")

# Create links programmatically
validator.add_incoming_link(parser.window_id)
parser.add_outgoing_link(validator.window_id)

validator.log_message("Ready to receive data")
```

## File Structure

```
/Users/ypzhang/dev/wingent/
├── process_gui.py       # Main application (~170 lines)
├── demo_usage.py        # Demo script with multiple modes
├── test_drag_drop.py    # Simplified test for drag-drop
└── README.md            # This file
```

## Architecture Overview

```
ProcessApp (QApplication)
├── ProcessWindow 1
│   ├── DraggableButton
│   ├── Incoming Links Display
│   ├── Outgoing Links Display
│   └── Message Log
├── ProcessWindow 2
│   └── ...
└── ProcessWindow 3
    └── ...
```

## Technical Details

### Drag-and-Drop Implementation

1. **Button Press**: `DraggableButton.mousePressEvent()` triggers drag
2. **Drag Start**: Creates QDrag with window ID in MIME data
3. **Target Accept**: `ProcessWindow.dragEnterEvent()` accepts if data matches
4. **Drop**: `ProcessWindow.dropEvent()` creates link when data is validated

### Link Management

- Links stored as dictionaries: `{target_id: True}`
- Prevents duplicate links (checked before adding)
- Both source and target are notified of new links
- Color-coded for quick visual identification

## Extending the Application

### Add Custom Message Sending

```python
class ProcessWindow(QMainWindow):
    def send_message(self, target_id, message):
        """Send a message to a linked process."""
        if target_id in self.outgoing_links:
            # Implementation here
            self.log_message(f"Sent to {target_id}: {message}")
```

### Add Process Execution

```python
import subprocess

class ProcessWindow(QMainWindow):
    def start_process(self, command):
        """Start an actual subprocess."""
        self.process = subprocess.Popen(
            command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.log_message(f"Started process: {command}")
```

### Add Real-Time Communication

```python
from PyQt5.QtCore import QThread, pyqtSignal

class CommunicationThread(QThread):
    message_received = pyqtSignal(str)

    def run(self):
        """Listen for messages from linked processes."""
        # Implementation here
        pass
```

## Troubleshooting

### Drag-Drop Not Working

If the drag-and-drop button doesn't work:

1. **Verify PyQt5 Installation**:
   ```bash
   python3 -c "from PyQt5.QtGui import QDrag; print('PyQt5 OK')"
   ```

2. **Run the Test**:
   ```bash
   python3 test_drag_drop.py
   ```

3. **Check Python Version** (requires Python 3.7+):
   ```bash
   python3 --version
   ```

### Windows Not Appearing

- Make sure you're using the Python from the virtual environment
- Check that PyQt5 is properly installed: `pip list | grep PyQt5`

## Performance

- Minimal resource usage: each window is independent
- No blocking operations - all events are non-blocking
- Scales to 10+ windows without performance issues

## Future Enhancements

- [ ] Visual link lines between windows
- [ ] Real-time message passing between processes
- [ ] Process monitoring and health status
- [ ] Link configuration/properties dialog
- [ ] Save/load window layouts
- [ ] Network-based inter-process communication
