"""
UI constants and styling.
"""

# Node dimensions
NODE_WIDTH = 180
NODE_HEIGHT = 100
NODE_PADDING = 10

# Provider-specific colors (enhanced gradients)
PROVIDER_COLORS = {
    "anthropic": "#8B5CF6",  # Purple
    "openai": "#10B981",     # Green
    "local": "#F59E0B",      # Amber
    "default": "#3B82F6"     # Blue
}

# Provider hover colors (lighter variants)
PROVIDER_COLORS_HOVER = {
    "anthropic": "#A78BFA",
    "openai": "#34D399",
    "local": "#FBBF24",
    "default": "#60A5FA"
}

# UI colors
CANVAS_BG = "#F8FAFC"  # Lighter, more modern
NODE_BORDER = "#1E293B"
NODE_BORDER_LIGHT = "#94A3B8"  # Softer border option
NODE_TEXT = "#FFFFFF"
EDGE_COLOR = "#6366F1"
EDGE_WIDTH = 2

# Selection colors
SELECTION_COLOR = "#F43F5E"  # Brighter pink-red
SELECTION_GLOW = "#FCA5A5"   # Soft glow effect
SELECTION_WIDTH = 3

# Fonts
FONT_FAMILY = "Segoe UI, Arial, sans-serif"  # Better system fonts
FONT_SIZE_TITLE = 11
FONT_SIZE_SUBTITLE = 8
FONT_SIZE_SMALL = 7
FONT_WEIGHT_BOLD = "bold"
FONT_WEIGHT_NORMAL = "normal"

# Config button
CONFIG_BUTTON_SIZE = 20  # Slightly larger
CONFIG_BUTTON_COLOR = "#FFFFFF"
CONFIG_BUTTON_BG = "#64748B"
CONFIG_BUTTON_BG_HOVER = "#475569"

# Monitor colors
MONITOR_BG = "#FFFFFF"
MONITOR_LOG_BG = "#F8FAFC"
MONITOR_BORDER = "#E2E8F0"

# Button colors (enhanced)
BUTTON_START = "#10B981"
BUTTON_START_HOVER = "#059669"
BUTTON_STOP = "#EF4444"
BUTTON_STOP_HOVER = "#DC2626"
BUTTON_CLEAR = "#64748B"
BUTTON_CLEAR_HOVER = "#475569"
BUTTON_PRIMARY = "#3B82F6"
BUTTON_PRIMARY_HOVER = "#2563EB"
BUTTON_SECONDARY = "#94A3AF"
BUTTON_SECONDARY_HOVER = "#6B7280"

# Status colors
STATUS_RUNNING = "#10B981"
STATUS_STOPPED = "#EF4444"
STATUS_IDLE = "#F59E0B"

# Message colors (for monitor)
MESSAGE_USER = "#DBEAFE"
MESSAGE_AGENT = "#E0E7FF"
MESSAGE_SYSTEM = "#F3F4F6"

# Shadow/depth colors
SHADOW_LIGHT = "#E2E8F0"
SHADOW_MEDIUM = "#CBD5E1"
SHADOW_DARK = "#94A3B8"

# Header colors
HEADER_BG = "#0F172A"  # Darker, more modern
HEADER_TEXT = "#F8FAFC"

# Spacing constants
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 24


def get_provider_color(provider: str) -> str:
    """
    Get color for a provider.

    Args:
        provider: Provider name

    Returns:
        Hex color string
    """
    return PROVIDER_COLORS.get(provider, PROVIDER_COLORS["default"])


def get_provider_hover_color(provider: str) -> str:
    """
    Get hover color for a provider.

    Args:
        provider: Provider name

    Returns:
        Hex color string
    """
    return PROVIDER_COLORS_HOVER.get(provider, PROVIDER_COLORS_HOVER["default"])
