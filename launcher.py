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
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor


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
    splash_pix = QPixmap(450, 300)
    splash_pix.fill(QColor("#F5F7F7"))  # Match logo background

    # Draw on splash screen
    painter = QPainter(splash_pix)

    # Load and draw logo
    logo = QPixmap("icon.png")
    if not logo.isNull():
        # Scale logo to 80x80 and center it at top
        logo = logo.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
        logo_x = (splash_pix.width() - logo.width()) // 2
        painter.drawPixmap(logo_x, 20, logo)

    painter.setPen(Qt.GlobalColor.black)

    # Title (positioned below logo)
    title_font = QFont("Arial", 28, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.drawText(
        splash_pix.rect(),
        Qt.AlignmentFlag.AlignCenter,
        "ModScan Tool",
    )

    # Version (below title)
    version_font = QFont("Arial", 11)
    painter.setFont(version_font)
    painter.drawText(
        20, 190, splash_pix.width() - 40, 30,
        Qt.AlignmentFlag.AlignCenter,
        f"Version {version}"
    )

    # Author (at bottom)
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
    min_splash_time = 2.0  # seconds

    if elapsed < min_splash_time:
        # Use QTimer to close splash after remaining time (keeps app responsive)
        window.hide()
        delay_ms = int((min_splash_time - elapsed) * 1000)
        QTimer.singleShot(delay_ms, lambda: (splash.finish(window), window.show()))
    else:
        # Close splash immediately if enough time has passed
        splash.finish(window)

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
