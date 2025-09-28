import tkinter as tk
from tkinter import ttk
import ttkbootstrap as bst
from ttkbootstrap.dialogs import Messagebox
import os
import sys
import subprocess
import requests

# --- Configuration ---
LOCAL_APPDATA = os.getenv('LOCALAPPDATA')
APP_FOLDER = os.path.join(LOCAL_APPDATA, 'FLTCHKLST')
MAIN_FOLDER = os.path.join(APP_FOLDER, 'Main')
EXE_PATH = os.path.join(MAIN_FOLDER, 'FlightList.exe')
LISTS_DIR = os.path.join(APP_FOLDER, 'Lists') # Target for user-created lists
GITHUB_REPO = "Fir3Fly1995/FlightListChk"
EXE_FILENAME = "FlightList.exe"

class ChecklistLauncher(bst.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Flight Checklist Launcher")
        self.geometry("400x300")
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill='both', expand=True)

        ttk.Label(main_frame, text="Flight Checklist Launcher", font=('Inter', 18, 'bold'), bootstyle="primary").pack(pady=(0, 20))

        # Update Button
        ttk.Button(
            main_frame,
            text="Check for Update",
            command=self.download_update,
            bootstyle="info-outline",
            width=25
        ).pack(pady=10)

        # Open Lists Folder Button
        ttk.Button(
            main_frame,
            text="Open Lists Folder",
            command=self.open_lists_folder,
            bootstyle="secondary-outline",
            width=25
        ).pack(pady=10)

        # Let's Fly Button
        ttk.Button(
            main_frame,
            text="Let's Fly!",
            command=self.launch_app,
            bootstyle="success",
            width=25
        ).pack(pady=10)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(main_frame, textvariable=self.status_var, bootstyle="secondary").pack(pady=20)

        # Ensure the main directory structure exists
        os.makedirs(MAIN_FOLDER, exist_ok=True)
        os.makedirs(LISTS_DIR, exist_ok=True)
        
        # Create a dummy exe for initial testing if not present
        if not os.path.exists(EXE_PATH):
            with open(EXE_PATH, 'w') as f:
                f.write('Dummy executable content for testing.')
            self.status_var.set("Dummy FlightList.exe created for first run.")

    def download_update(self):
        self.status_var.set("Checking for updates...")
        self.update_idletasks()
        
        # Placeholder for real GitHub API and download logic
        try:
            # Simulate a request check
            requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest", timeout=5)
            self.status_var.set("Update simulated: New version of FlightList.exe downloaded successfully.")
        except requests.exceptions.RequestException as e:
            self.status_var.set(f"Update check failed (No network/GitHub error). Using local EXE.")
        except Exception as e:
             self.status_var.set(f"An unexpected error occurred during update: {e}")

    def launch_app(self):
        if os.path.exists(EXE_PATH):
            self.status_var.set("Launching FlightList.exe...")
            try:
                # Use Popen to launch the exe and not block the Tkinter thread
                subprocess.Popen([EXE_PATH])
                self.after(2000, self.destroy) # Close launcher after 2 seconds
            except OSError as e:
                self.status_var.set(f"Error launching app: {e}")
            except Exception as e:
                self.status_var.set(f"Unknown error launching app: {e}")
        else:
            self.status_var.set("Error: FlightList.exe not found. Please update.")

    def open_lists_folder(self):
        """Shows instructions and opens the Lists folder."""
        
        instructions = (
            "Create the **manufacturer plane folders** (e.g., 'Airbus A320', 'Boeing 737'). "
            "Place your lists inside these folders, numbered '01_' to 'xx_' followed by the procedure, "
            "and save them as a **.txt file**. Return and launch the app to use your checklists."
        )

        # Use Messagebox for the instructional popup
        Messagebox.show_info(
            title="Checklist Setup Instructions",
            message=instructions,
            parent=self # Attach to the main window
        )
        
        # Now open the folder
        try:
            if sys.platform == "win32":
                os.startfile(LISTS_DIR)
            else:
                # Fallback for non-Windows systems (e.g., Mac or Linux)
                subprocess.Popen(['xdg-open' if sys.platform.startswith('linux') else 'open', LISTS_DIR])
            self.status_var.set(f"Opened folder: {LISTS_DIR}")
        except Exception as e:
            self.status_var.set(f"Error opening folder: {e}. Check if path exists.")


if __name__ == "__main__":
    try:
        import ttkbootstrap as bst
        import requests 
    except ImportError:
        print("Required libraries ('requests' and 'ttkbootstrap') are missing. Install with: pip install requests ttkbootstrap")
        sys.exit(1)

    app = ChecklistLauncher()
    app.mainloop()
