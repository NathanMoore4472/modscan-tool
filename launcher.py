#!/usr/bin/env python3
"""
ModScan Tool Launcher
Fast-loading launcher that shows splash screen while main app loads
"""

import sys
import time
import re

# Import only minimal PyQt6 for splash screen (fast)
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QFont


def get_version():
    """Extract version from modscan_tool.py without importing it"""
    try:
        with open("modscan_tool.py", "r") as f:
            content = f.read()
            match = re.search(r'self\.app_version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
    except:
        pass
    return "1.2.0"  # Fallback version


def create_splash():
    """Create and return splash screen"""
    version = get_version()

    # Create splash pixmap
    splash_pix = QPixmap(450, 250)
    splash_pix.fill(Qt.GlobalColor.white)

    # Draw text on splash screen
    painter = QPainter(splash_pix)
    painter.setPen(Qt.GlobalColor.black)

    # Title
    title_font = QFont("Arial", 28, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.drawText(
        splash_pix.rect(),
        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
        "\n\nModScan Tool",
    )

    # Version
    version_font = QFont("Arial", 11)
    painter.setFont(version_font)
    painter.drawText(
        splash_pix.rect(), Qt.AlignmentFlag.AlignCenter, f"Version {version}"
    )

    # Author
    author_font = QFont("Arial", 10)
    painter.setFont(author_font)
    painter.setPen(Qt.GlobalColor.darkGray)
    painter.drawText(
        splash_pix.rect(),
        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
        "by Nathan Moore\n\n",
    )

    painter.end()

    # Create splash screen
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    return splash


def main():
    # Create QApplication first
    app = QApplication(sys.argv)

    # Track splash screen start time
    splash_start = time.time()

    # Show splash screen immediately
    splash = create_splash()
    splash.show()
    app.processEvents()  # Force immediate display

    # Now import the heavy main application module
    # This happens while splash is visible
    splash.showMessage(
        "Loading modules...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        Qt.GlobalColor.black,
    )
    app.processEvents()

    from modscan_tool import ModbusScannerGUI

    # Create main window
    splash.showMessage(
        "Starting application...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        Qt.GlobalColor.black,
    )
    app.processEvents()

    window = ModbusScannerGUI()
    window.show()

    # Ensure splash displays for at least 1 second (non-blocking)
    elapsed = time.time() - splash_start
    min_splash_time = 1.0  # seconds

    if elapsed < min_splash_time:
        # Use QTimer to close splash after remaining time (keeps app responsive)
        delay_ms = int((min_splash_time - elapsed) * 1000)
        QTimer.singleShot(delay_ms, lambda: splash.finish(window))
    else:
        # Close splash immediately if enough time has passed
        splash.finish(window)

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
