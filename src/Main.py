import threading
import socket
import sys
import os

from PySide6.QtWidgets import QApplication
from CrossPatch import CrossPatchWindow
import Util
import Config # This will now set up config paths on import
import PakInspector
import Localization
from Localization import tr
import webbrowser
import subprocess
import platform

SINGLE_INSTANCE_PORT = 38471 # A random, hopefully unused port
if __name__ == "__main__":
    # Try to bind to a port to enforce a single instance
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
    except OSError:
        # Port is already in use, another instance is running.
        # Send the command-line argument to the running instance.
        if len(sys.argv) > 1:
            try:
                client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_sock.connect(("127.0.0.1", SINGLE_INSTANCE_PORT))
                # Send the URL argument
                client_sock.sendall(sys.argv[1].encode('utf-8'))
                client_sock.close()
                print("Sent URL to running instance.")
            except Exception as e:
                print(f"Could not send URL to running instance: {e}")
        # Exit this new instance
        sys.exit(0)

    # This is the primary instance.
    Config.register_url_protocol()

    app = QApplication(sys.argv)
    Localization.ensure_initialized()
    Localization.install_qt_translations(app)
    # Apply a dark theme
    try:
        import qdarktheme
        app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    except ImportError:
        print("qdarktheme not found. Using default system theme.")

    # --- Ensure .NET 8 runtime is available for the pak parser ---
    def _has_dotnet_8():
        """Return True if a .NET runtime 8.x is present (checked via `dotnet --list-runtimes`)."""
        try:
            proc = subprocess.run(["dotnet", "--list-runtimes"], capture_output=True, text=True,
                                  check=True, timeout=5, **PakInspector._subprocess_flags())
            out = proc.stdout + proc.stderr
            # Look for Microsoft.NETCore.App 8.* or similar runtime entries
            for line in out.splitlines():
                if "Microsoft.NETCore.App" in line or "Microsoft.AspNetCore.App" in line:
                    # line format: Name Version [path]
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ver = parts[1]
                        if ver.startswith("8.") or ver.startswith("8"):
                            return True
            return False
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # If we have a self-contained parser executable for this platform, the
    # .NET runtime is not required. Only prompt for dotnet if no native parser
    # is present.
    # parser_works() actually launches it: the bundled parser is
    # framework-dependent, so merely finding the file proves nothing.
    if not _has_dotnet_8() and not PakInspector.parser_works():
        # Prompt the user to install .NET 8 before proceeding. We show this
        # dialog before creating the main window so the user must choose.
        from PySide6.QtWidgets import QMessageBox

        # The parser is only needed for pak analysis and conflict detection, so
        # let people keep using CrossPatch instead of forcing them to quit.
        box = QMessageBox(None)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(tr("dotnet.title"))
        box.setText(tr("dotnet.body"))
        download_btn = box.addButton(tr("dotnet.download"), QMessageBox.AcceptRole)
        continue_btn = box.addButton(tr("dotnet.continue"), QMessageBox.DestructiveRole)
        box.addButton(tr("dotnet.exit"), QMessageBox.RejectRole)
        box.setDefaultButton(download_btn)
        box.exec()
        clicked = box.clickedButton()

        if clicked is continue_btn:
            print(".NET 8 runtime not detected; continuing without pak analysis.")
        else:
            if clicked is download_btn:
                # Open the .NET 8 runtime download page (runtime-specific) to reduce confusion.
                runtime_url = "https://dotnet.microsoft.com/en-us/download/dotnet/8.0/runtime"
                if platform.system() == "Windows":
                    runtime_url = "https://dotnet.microsoft.com/en-us/download/dotnet/thank-you/runtime-desktop-8.0.21-windows-x64-installer"
                try:
                    webbrowser.open(runtime_url)
                except Exception as e:
                    print(f"Could not open the download page: {e}")
            print(".NET 8 runtime not detected; exiting.")
            sys.exit(1)

    # A crash in here used to close the packaged app instantly with no message,
    # leaving users with nothing to report. Show the error instead.
    try:
        window = CrossPatchWindow(instance_socket=sock)
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            tr("startup.failed.title"),
            tr("startup.failed.body", error=e, traceback=traceback.format_exc()),
        )
        sys.exit(1)

    # Handle initial command-line argument if app was launched with one
    if len(sys.argv) > 1:
        url = sys.argv[1]
        window.handle_protocol_url(url)

    # Start the thread that checks for app updates, unless disabled by an environment variable.
    if os.environ.get("CROSSPATCH_DISABLE_UPDATES") != "1":
        threading.Thread(target=lambda: Util.check_for_updates_pyside(window), daemon=True).start()
    else:
        print("Auto-updater is disabled via CROSSPATCH_DISABLE_UPDATES environment variable.")

    window.show()
    sys.exit(app.exec())
