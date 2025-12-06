#!/usr/bin/env python3
"""
Auto-updater module for ModScan Tool
Handles checking for updates, downloading, and installing new versions from GitHub
"""

import sys
import json
import urllib.request
import urllib.error
import ssl
import platform
import os
import tempfile
import subprocess
import shutil
import re

# Import certifi for SSL certificate verification
try:
    import certifi
    HAS_CERTIFI = True
except ImportError:
    HAS_CERTIFI = False

from PyQt6.QtWidgets import (QMessageBox, QCheckBox, QApplication, QDialog,
                             QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
                             QPushButton, QDialogButtonBox)
from PyQt6.QtCore import Qt


def _macos_update_and_restart(app_path, new_app_path, temp_dir):
    """Helper function for macOS update - must be at module level for multiprocessing"""
    import time
    import os
    import shutil
    import subprocess

    # Create debug log
    log_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'update_debug.txt')

    def log(msg):
        with open(log_path, 'a') as f:
            f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")

    log(f"Starting update process")
    log(f"Current app path: {app_path}")
    log(f"New app path: {new_app_path}")
    log(f"Temp dir: {temp_dir}")

    # Wait for app to quit
    log("Waiting 5 seconds for app to quit...")
    time.sleep(5)

    # Replace the app bundle
    try:
        log(f"Checking if old app exists: {os.path.exists(app_path)}")
        if os.path.exists(app_path):
            log("Removing old app...")
            shutil.rmtree(app_path)
            log("Old app removed")

        log(f"Checking if new app exists: {os.path.exists(new_app_path)}")
        log("Moving new app to location...")
        shutil.move(new_app_path, app_path)
        log("New app moved successfully")

        # Set permissions
        log("Setting permissions...")
        for root, dirs, files in os.walk(app_path):
            for d in dirs:
                try:
                    os.chmod(os.path.join(root, d), 0o755)
                except:
                    pass
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), 0o755)
                except:
                    pass
        log("Permissions set")

        # Wait for filesystem
        time.sleep(2)

        # Launch the app
        log(f"Launching app: {app_path}")
        result = subprocess.call(['open', app_path])
        log(f"Launch command result: {result}")

    except Exception as e:
        log(f"ERROR: {str(e)}")
    finally:
        # Clean up
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                log("Temp dir cleaned up")
        except Exception as e:
            log(f"Cleanup error: {str(e)}")

    log("Update process complete")


class UpdateChecker:
    """Handles automatic update checking and installation for ModScan Tool"""

    def __init__(self, app_version, settings, parent_window):
        """
        Initialize the update checker

        Args:
            app_version: Current application version string
            settings: QSettings object for storing preferences
            parent_window: Parent QWidget for dialogs
        """
        self.app_version = app_version
        self.settings = settings
        self.parent = parent_window

        # Load preferences
        self.check_updates_on_startup = settings.value("check_updates_on_startup", True, type=bool)
        self.update_debug_logging = settings.value("update_debug_logging", False, type=bool)

    def is_frozen(self):
        """Check if running as compiled executable"""
        return getattr(sys, 'frozen', False)

    def get_platform_asset_name(self):
        """Get the asset name for the current platform"""
        system = platform.system()
        if system == "Windows":
            return "ModScan-Tool-Windows.zip"
        elif system == "Darwin":  # macOS
            return "ModScan-Tool-macOS.zip"
        elif system == "Linux":
            return "ModScan-Tool-Linux.tar.gz"
        return None

    def get_executable_path(self):
        """Get the path to the current executable"""
        if self.is_frozen():
            return sys.executable
        else:
            return os.path.abspath(__file__)

    def get_app_bundle_path(self):
        """Get the path to the .app bundle on macOS"""
        if platform.system() == "Darwin" and self.is_frozen():
            exe_path = sys.executable
            parts = exe_path.split('/')
            try:
                app_index = next(i for i, part in enumerate(parts) if part.endswith('.app'))
                return '/'.join(parts[:app_index + 1])
            except StopIteration:
                return exe_path
        else:
            return self.get_executable_path()

    def check_for_updates(self, silent=False):
        """
        Check for available updates from GitHub

        Args:
            silent: If True, only show dialog if update is available
        """
        print(f"Checking for updates... (silent={silent}, current version={self.app_version})")
        try:
            url = "https://api.github.com/repos/NathanMoore4472/modscan-tool/releases/latest"
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'ModScan-Tool')

            # Use certifi for SSL verification if available
            if HAS_CERTIFI:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
            else:
                ssl_context = ssl.create_default_context()

            with urllib.request.urlopen(req, timeout=5, context=ssl_context) as response:
                data = json.loads(response.read().decode())

            latest_version = data.get('tag_name', '').lstrip('v')
            release_url = data.get('html_url', '')
            release_notes = data.get('body', '')
            assets = data.get('assets', [])

            print(f"Latest version: {latest_version}, Current version: {self.app_version}")

            # Compare versions
            if self._is_newer_version(latest_version, self.app_version):
                print(f"Update available! {latest_version} > {self.app_version}")
                self.show_update_dialog(latest_version, release_url, release_notes, assets)
            elif not silent:
                QMessageBox.information(
                    self.parent,
                    "No Updates Available",
                    f"You are running the latest version ({self.app_version})."
                )

        except urllib.error.URLError as e:
            # Always log errors to console for debugging
            print(f"Update check failed (URLError): {e}")
            if not silent:
                QMessageBox.warning(
                    self.parent,
                    "Update Check Failed",
                    f"Could not check for updates: {str(e)}"
                )
        except Exception as e:
            # Always log errors to console for debugging
            print(f"Update check failed (Exception): {e}")
            import traceback
            traceback.print_exc()
            if not silent:
                QMessageBox.warning(
                    self.parent,
                    "Update Check Failed",
                    f"Could not check for updates: {str(e)}"
                )

    def _is_newer_version(self, latest, current):
        """Compare version strings (e.g., '1.2.3' vs '1.2.2')"""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            return latest_parts > current_parts
        except:
            return False

    def _markdown_to_html(self, markdown_text):
        """Convert basic markdown to HTML for release notes"""
        if not markdown_text:
            return ""

        html = markdown_text

        # Escape HTML special characters first (but preserve for conversion)
        # html = html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Convert headers (### Header -> <h3>Header</h3>)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Convert bold (**text** or __text__)
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        html = re.sub(r'__(.+?)__', r'<b>\1</b>', html)

        # Convert italic (*text* or _text_) - but not inside words
        html = re.sub(r'\*([^\*]+?)\*', r'<i>\1</i>', html)
        html = re.sub(r'(?<!\w)_([^_]+?)_(?!\w)', r'<i>\1</i>', html)

        # Convert links [text](url)
        html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)

        # Convert inline code `code`
        html = re.sub(r'`([^`]+)`', r'<code style="background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px;">\1</code>', html)

        # Convert unordered lists (- item or * item)
        lines = html.split('\n')
        in_list = False
        result_lines = []

        for line in lines:
            # Check if line is a list item
            if re.match(r'^[\s]*[-*]\s+(.+)$', line):
                list_item = re.sub(r'^[\s]*[-*]\s+(.+)$', r'\1', line)
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                result_lines.append(f'<li>{list_item}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)

        if in_list:
            result_lines.append('</ul>')

        html = '\n'.join(result_lines)

        # Convert line breaks to <br> for paragraphs
        html = re.sub(r'\n\n+', '</p><p>', html)

        # Wrap in paragraph if not already wrapped
        if not html.startswith('<'):
            html = f'<p>{html}</p>'

        return html

    def show_update_dialog(self, version, url, notes, assets=None):
        """Show dialog notifying user of available update"""
        asset_name = self.get_platform_asset_name()
        asset_url = None

        # Only look for assets if running as frozen executable
        if self.is_frozen() and assets and asset_name:
            for asset in assets:
                if asset.get('name') == asset_name:
                    asset_url = asset.get('browser_download_url')
                    break

        # Create custom dialog
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Update Available")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Header with version info
        header_html = f"""
<h2>Update Available!</h2>
<p>A new version of ModScan Tool is available.</p>
<table style="margin-top: 10px;">
<tr><td><b>Current Version:</b></td><td>{self.app_version}</td></tr>
<tr><td><b>Latest Version:</b></td><td>{version}</td></tr>
</table>
"""
        header_label = QLabel(header_html)
        header_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header_label)

        # Release notes section header
        notes_header = QLabel("<b>Release Notes:</b>")
        layout.addWidget(notes_header)

        # Scrollable text browser for release notes
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)  # Allow clicking links

        # Convert markdown to HTML
        formatted_notes = self._markdown_to_html(notes if notes else 'No release notes available.')
        text_browser.setHtml(formatted_notes)

        layout.addWidget(text_browser)

        # Note for non-frozen executables
        if not self.is_frozen():
            note_label = QLabel('<p style="color: #666;"><i>Note: Auto-install is only available for compiled executables.</i></p>')
            note_label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(note_label)

        # Checkbox for startup checks
        checkbox = QCheckBox("Check for updates on startup")
        checkbox.setChecked(self.check_updates_on_startup)  # Set current state
        layout.addWidget(checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Add appropriate buttons based on whether we can auto-install
        if self.is_frozen() and asset_url:
            download_install_btn = QPushButton("Download && Install")
            download_install_btn.setDefault(True)
            manual_btn = QPushButton("Manual Download")
            later_btn = QPushButton("Later")

            button_layout.addWidget(download_install_btn)
            button_layout.addWidget(manual_btn)
            button_layout.addWidget(later_btn)

            download_install_btn.clicked.connect(dialog.accept)
            manual_btn.clicked.connect(lambda: dialog.done(2))
            later_btn.clicked.connect(dialog.reject)
        else:
            download_btn = QPushButton("Download")
            download_btn.setDefault(True)
            later_btn = QPushButton("Later")

            button_layout.addWidget(download_btn)
            button_layout.addWidget(later_btn)

            download_btn.clicked.connect(dialog.accept)
            later_btn.clicked.connect(dialog.reject)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # Show dialog and handle result
        result = dialog.exec()

        # Save checkbox state (always save, whether checked or unchecked)
        self.check_updates_on_startup = checkbox.isChecked()
        self.settings.setValue("check_updates_on_startup", checkbox.isChecked())

        # Handle button clicks
        if result == QDialog.DialogCode.Accepted:
            if self.is_frozen() and asset_url:
                # Download and install
                self.download_update(asset_url)
            else:
                # Open browser to download page
                import webbrowser
                webbrowser.open(url)
        elif result == 2:  # Manual download button
            import webbrowser
            webbrowser.open(url)

    def download_update(self, url):
        """Download the update file"""
        try:
            # Show progress (simple approach - could be enhanced with progress bar)
            asset_name = self.get_platform_asset_name()
            download_path = os.path.join(tempfile.gettempdir(), asset_name)

            # Use certifi for SSL verification if available
            if HAS_CERTIFI:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
            else:
                ssl_context = ssl.create_default_context()

            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'ModScan-Tool')

            with urllib.request.urlopen(req, context=ssl_context) as response:
                with open(download_path, 'wb') as out_file:
                    out_file.write(response.read())

            # Install the update
            self.install_update(download_path)

        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Download Failed",
                f"Failed to download update:\n{str(e)}"
            )

    def install_update(self, new_executable_path):
        """Install the downloaded update and restart"""
        import zipfile
        import tarfile

        system = platform.system()

        # For macOS, we need the .app bundle path, not the executable inside
        if system == "Darwin":
            current_exe = self.get_app_bundle_path()
        else:
            current_exe = self.get_executable_path()

        extract_dir = os.path.join(tempfile.gettempdir(), "modscan_update")

        # Extract archive if needed
        if system == "Darwin" and new_executable_path.endswith('.zip'):
            # Extract zip for macOS
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(new_executable_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            # Find the .app bundle
            app_name = "ModScan Tool.app"
            extracted_app = os.path.join(extract_dir, app_name)
            if os.path.exists(extracted_app):
                new_executable_path = extracted_app

        elif system == "Linux" and new_executable_path.endswith('.tar.gz'):
            # Extract tar.gz for Linux
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(new_executable_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_dir)
            # Find the executable
            for item in os.listdir(extract_dir):
                item_path = os.path.join(extract_dir, item)
                if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                    new_executable_path = item_path
                    break

        if system == "Windows":
            # Extract zip if needed
            if new_executable_path.endswith('.zip'):
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(new_executable_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                # Find the extracted folder
                folder_name = "ModScan-Tool-Windows"
                extracted_folder = os.path.join(extract_dir, folder_name)
                if os.path.exists(extracted_folder):
                    new_executable_path = extracted_folder

            updater_script = os.path.join(tempfile.gettempdir(), "update_modscan.bat")
            with open(updater_script, 'w') as f:
                # Use robocopy for directory or move for single file
                if os.path.isdir(new_executable_path):
                    f.write(f"""@echo off
timeout /t 2 /nobreak > nul
rmdir /s /q "{current_exe}"
robocopy "{new_executable_path}" "{current_exe}" /E /MOVE
start "" "{current_exe}\\ModScan Tool.exe"
rmdir /s /q "{extract_dir}"
del "%~f0"
""")
                else:
                    f.write(f"""@echo off
timeout /t 2 /nobreak > nul
move /y "{new_executable_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")
            subprocess.Popen(['cmd', '/c', updater_script], shell=False)

        elif system == "Darwin":
            # For macOS, use shell script (most reliable for frozen apps)
            updater_script = os.path.expanduser('~/Desktop/modscan_updater.sh')

            # Set up logging based on user preference
            if self.update_debug_logging:
                log_file = os.path.expanduser('~/Desktop/update_debug.txt')
                log_redirect = f'exec > "{log_file}" 2>&1'
                echo_cmd = "echo"
            else:
                log_redirect = '# Logging disabled'
                echo_cmd = ": #"  # No-op command

            with open(updater_script, 'w') as f:
                f.write(f"""#!/bin/bash
{log_redirect}
{echo_cmd} "=== Update started at $(date) ==="
{echo_cmd} "Current app: {current_exe}"
{echo_cmd} "New app: {new_executable_path}"
{echo_cmd} "Temp dir: {extract_dir}"
{echo_cmd} ""

# Wait for app to quit
{echo_cmd} "Waiting for app to fully terminate..."
sleep 3

# Check if process is still running and wait for it to exit
MAX_WAIT=30
WAITED=0
while pgrep -x "ModScan Tool" > /dev/null 2>&1; do
    {echo_cmd} "  App still running, waiting... ($WAITED seconds)"
    sleep 1
    WAITED=$((WAITED + 1))
    if [ $WAITED -ge $MAX_WAIT ]; then
        {echo_cmd} "  Timeout waiting for app to quit, forcing..."
        pkill -9 "ModScan Tool"
        sleep 2
        break
    fi
done
{echo_cmd} "App process terminated (waited $WAITED seconds)"
sleep 2

# Remove old app
{echo_cmd} "Removing old app..."
rm -rf "{current_exe}"
{echo_cmd} "Old app removed"

# Move new app
{echo_cmd} "Moving new app..."
mv "{new_executable_path}" "{current_exe}"
{echo_cmd} "New app moved"

# Set permissions and remove quarantine
{echo_cmd} "Setting permissions..."
chmod -R +x "{current_exe}"
{echo_cmd} "Removing quarantine attributes..."
xattr -cr "{current_exe}" 2>&1
{echo_cmd} "Permissions and attributes set"

# Wait
sleep 2

# Launch - use AppleScript which runs in GUI context
{echo_cmd} "Launching app using AppleScript..."

osascript <<EOF
tell application "Finder"
    open POSIX file "{current_exe}"
    activate
end tell
EOF

RESULT=$?
{echo_cmd} "AppleScript launch result: $RESULT"

sleep 2

# Check if app is running
{echo_cmd} "Checking if app is running..."
if ps aux | grep "ModScan Tool" | grep -v grep > /dev/null; then
    {echo_cmd} "✓ App is running!"
else
    {echo_cmd} "✗ App is not running"
fi
{echo_cmd} "Process check done"

# Cleanup
sleep 2
{echo_cmd} "Cleaning up..."
rm -rf "{extract_dir}"
rm -f "$0"
{echo_cmd} "Done at $(date)"
""")
            os.chmod(updater_script, 0o755)

            # Execute the script in background
            subprocess.Popen(['/bin/bash', updater_script],
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           start_new_session=True,
                           close_fds=True)

        elif system == "Linux":
            updater_script = os.path.join(tempfile.gettempdir(), "update_modscan.sh")
            with open(updater_script, 'w') as f:
                f.write(f"""#!/bin/bash
sleep 2
mv -f "{new_executable_path}" "{current_exe}"
chmod +x "{current_exe}"
"{current_exe}" &
rm -rf "{extract_dir}"
rm "$0"
""")
            os.chmod(updater_script, 0o755)
            subprocess.Popen(['/bin/bash', updater_script])

        QApplication.quit()
