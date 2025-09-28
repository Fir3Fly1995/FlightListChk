import tkinter as tk
from tkinter import ttk, filedialog
import ttkbootstrap as bst
from ttkbootstrap.dialogs import Messagebox
import os
import sys
import subprocess
import requests
from packaging.version import parse as parse_version
from datetime import datetime

# --- Configuration ---
LOCAL_APPDATA = os.getenv('LOCALAPPDATA')
APP_FOLDER = os.path.join(LOCAL_APPDATA, 'FLTCHKLST')
MAIN_FOLDER = os.path.join(APP_FOLDER, 'Main')
EXE_PATH = os.path.join(MAIN_FOLDER, 'FlightList.exe')
LISTS_DIR = os.path.join(APP_FOLDER, 'Lists')
SIM_PATH_FILE = os.path.join(MAIN_FOLDER, 'sim_path.txt')
VERSION_FILE = os.path.join(MAIN_FOLDER, 'version.txt') # Local file to store current version

GITHUB_REPO = "Fir3Fly1995/FlightListChk"
EXE_FILENAME = "FlightList.exe"

# GitHub RAW Content Links (Assumes manifest and exe are in the root of the main branch)
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/"
MANIFEST_URL = GITHUB_RAW_BASE + "manifest.txt"
EXE_DOWNLOAD_URL = GITHUB_RAW_BASE + EXE_FILENAME

# Sentinel value to permanently skip the Sim Path prompt
SKIP_PROMPT_SIM_LAUNCH = "DO_NOT_PROMPT_AGAIN"


class ChecklistLauncher(bst.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Flight Checklist Launcher")
        self.geometry("420x340")
        
        # Ensure the main directory structure exists
        os.makedirs(MAIN_FOLDER, exist_ok=True)
        os.makedirs(LISTS_DIR, exist_ok=True)
        
        # Initialize paths and versions (Version is now a dict: {'date': datetime, 'message': str})
        self.flight_sim_path = ""
        # Default local version is a date far in the past
        self.local_version_info = {'date': datetime(2000, 1, 1), 'message': 'Initial Install'}
        self.remote_version_info = None # Will be set by _check_for_update
        self.is_offline = False # Tracks if manifest check failed
        self.skip_sim_prompt = False # Tracks if the user selected 'Don't remind me again'
        
        self._load_sim_path()
        self._load_local_version()
        self._check_for_update() # Check for update immediately on launch

        self.create_widgets()
    
    # --- Version and Path Management ---

    def _parse_version_info(self, content):
        """Parses 'DD/MM/YYYY - Message' into a datetime object and message string."""
        if not content:
            return None
        
        try:
            # Assuming manifest is multi-line, only use the first line for version
            line = content.split('\n')[0].strip()
            date_str, message = line.split(' - ', 1)
            date_obj = datetime.strptime(date_str, '%d/%m/%Y')
            return {'date': date_obj, 'message': message}
        except Exception:
            # Return None if parsing fails
            return None

    def _load_local_version(self):
        """Loads the local version string and parses it."""
        try:
            with open(VERSION_FILE, 'r') as f:
                content = f.read().strip()
                parsed_info = self._parse_version_info(content)
                if parsed_info:
                    self.local_version_info = parsed_info
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error loading local version: {e}")

    def _save_local_version(self, version_info):
        """Saves the version info dictionary to the local version file."""
        date_str = version_info['date'].strftime('%d/%m/%Y')
        content = f"{date_str} - {version_info['message']}"
        try:
            with open(VERSION_FILE, 'w') as f:
                f.write(content)
            self.local_version_info = version_info
        except Exception as e:
            print(f"Error saving local version: {e}")

    def _load_sim_path(self):
        """Loads the saved Flight Simulator executable path from the file."""
        try:
            with open(SIM_PATH_FILE, 'r') as f:
                path = f.read().strip()
                if path == SKIP_PROMPT_SIM_LAUNCH:
                    self.skip_sim_prompt = True
                    self.flight_sim_path = "" # Path is technically unset, but we skip prompting
                elif os.path.exists(path):
                    self.flight_sim_path = path
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error loading sim path: {e}")
            self.flight_sim_path = ""
    
    def _save_sim_path(self, path):
        """Saves the flight sim path or the skip prompt sentinel."""
        try:
            with open(SIM_PATH_FILE, 'w') as f:
                f.write(path)
            if path == SKIP_PROMPT_SIM_LAUNCH:
                self.skip_sim_prompt = True
                self.flight_sim_path = ""
            else:
                self.flight_sim_path = path
                self.skip_sim_prompt = False # Reset if they set a path
        except Exception as e:
            self.status_var.set(f"Error saving path: {e}")

    def _select_and_save_sim_path(self):
        """Opens a file dialog for the user to select the sim executable and saves the path."""
        initial_dir = os.path.dirname(self.flight_sim_path) if self.flight_sim_path and os.path.exists(os.path.dirname(self.flight_sim_path)) else 'C:\\Program Files'
        
        selected_path = filedialog.askopenfilename(
            title="Select Your Flight Simulator Executable (e.g., X-Plane.exe, MSFS.exe)",
            initialdir=initial_dir,
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")]
        )

        if selected_path:
            self._save_sim_path(selected_path)
            self.status_var.set(f"Sim path set: {os.path.basename(selected_path)}")
            self.status_var.set(self.get_initial_status())
        else:
            self.status_var.set("Flight Simulator path selection cancelled.")

    def _check_for_update(self):
        """Checks the remote manifest.txt for the latest version and message."""
        try:
            response = requests.get(MANIFEST_URL, timeout=5)
            response.raise_for_status()
            
            remote_info = self._parse_version_info(response.text)
            
            if remote_info:
                self.remote_version_info = remote_info
                self.is_offline = False
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch manifest (Offline?): {e}")
            self.remote_version_info = None
            self.is_offline = True
        except Exception as e:
            print(f"Unexpected error during update check: {e}")
            self.remote_version_info = None
            self.is_offline = False


    # --- UI Status and Layout ---

    def get_initial_status(self):
        """Returns the appropriate status message on startup."""
        local_date_str = self.local_version_info['date'].strftime('%d/%m/%Y')
        sim_path_valid = self.flight_sim_path and os.path.exists(self.flight_sim_path)
        sim_status = "Sim Path Set" if sim_path_valid else "Sim Path NOT Set"
        
        # Check if EXE is present
        exe_status = "Flight List.exe Found" if os.path.exists(EXE_PATH) else "Flight List.exe MISSING"

        if self.is_offline:
            return f"Offline/Connection Failed | Local Version: {local_date_str} | {exe_status} | {sim_status}"
            
        needs_update = self.remote_version_info and self.remote_version_info['date'] > self.local_version_info['date']
        
        if needs_update:
            update_date_str = self.remote_version_info['date'].strftime('%d/%m/%Y')
            update_status_message = f"UPDATE AVAILABLE ({update_date_str}: {self.remote_version_info['message']})"
            return f"{update_status_message} | {exe_status} | {sim_status}"
        else:
            return f"Online (Up to Date) | Local Version: {local_date_str} | {exe_status} | {sim_status}"

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill='both', expand=True)

        ttk.Label(main_frame, text="Flight Checklist Launcher", font=('Inter', 18, 'bold'), bootstyle="primary").pack(pady=(0, 20))
        
        # Set Flight Sim Path Button
        ttk.Button(
            main_frame,
            text="Set Flight Sim Path",
            command=self._select_and_save_sim_path,
            bootstyle="warning-outline",
            width=25
        ).pack(pady=5)
        
        # Open Lists Folder Button
        ttk.Button(
            main_frame,
            text="Open Lists Folder",
            command=self.open_lists_folder,
            bootstyle="info-outline",
            width=25
        ).pack(pady=5)

        # Let's Fly Button (Triggers decision flow: Launch or Prompt)
        ttk.Button(
            main_frame,
            text="Let's Fly!",
            command=self.handle_launch,
            bootstyle="success",
            width=25
        ).pack(pady=10)

        # Status Label
        self.status_var = tk.StringVar(value=self.get_initial_status())
        # Highlight status if an update is available
        status_style = "warning" if "UPDATE AVAILABLE" in self.status_var.get() else "secondary"
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, bootstyle=status_style, wraplength=380, justify='center')
        self.status_label.pack(pady=10)


    # --- Core Logic ---

    def handle_launch(self):
        """
        Launches immediately if no update is needed or if offline.
        Shows the manual update prompt if an update is available.
        """
        
        needs_update = self.remote_version_info and self.remote_version_info['date'] > self.local_version_info['date']
        local_exe_exists = os.path.exists(EXE_PATH)
        
        if not local_exe_exists:
            # Case 1: No local file (First run or deleted) -> Must download and launch
            self.status_var.set("FlightList.exe not found locally. Downloading required file...")
            self.update_idletasks()
            success = self._download_update_core()
            if success:
                self._launch_app_core()
            else:
                self.status_var.set("FATAL: Failed to download FlightList.exe. Cannot launch.")
        
        elif needs_update:
            # Case 2: Update is available -> Show the prompt for user control
            self._show_update_prompt()
            
        else:
            # Case 3: Local file exists, up-to-date, or offline check failed -> Just launch
            self.status_var.set("Launching local version...")
            self.update_idletasks()
            self._launch_app_core()
    
    def _show_update_prompt(self):
        """
        Custom dialog to let the user decide between updating or just launching.
        """
        remote_date_str = self.remote_version_info['date'].strftime('%d/%m/%Y')
        
        dialog = tk.Toplevel(self)
        dialog.title("Update Available!")
        dialog.geometry("420x200")
        dialog.configure(bg=bst.Style().colors.get('bg'))
        dialog.transient(self) # Keep dialog on top of the main window
        dialog.grab_set() # Modal behavior
        
        # Center the dialog
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_reqwidth() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_reqheight() // 2)
        dialog.geometry(f"+{x}+{(y)}")

        # Function to clean up and proceed
        def perform_action(action):
            dialog.destroy()
            self._handle_launch_action(action)

        # Content Frame
        content_frame = ttk.Frame(dialog, padding=15)
        content_frame.pack(fill='both', expand=True)

        ttk.Label(content_frame, text="An update is available! Your control:", font=('Inter', 12, 'bold'), bootstyle="primary").pack(pady=(0, 5))
        
        message = f"New Version ({remote_date_str}) Changelog:\n\n{self.remote_version_info['message']}\n\nChoose 'Update & Fly' to get the latest file."
        ttk.Label(content_frame, text=message, wraplength=380, bootstyle="secondary", justify='left').pack(pady=(0, 10), fill='x')
        
        # Button Frame
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(pady=5)

        ttk.Button(button_frame, text="Update & Fly", command=lambda: perform_action("update"), bootstyle="success").pack(side='left', padx=10)
        
        ttk.Button(button_frame, text="Just Fly", command=lambda: perform_action("launch"), bootstyle="secondary").pack(side='left', padx=10)

        dialog.protocol("WM_DELETE_WINDOW", lambda: perform_action("launch")) # Treat manual close as 'Just Fly'
        self.wait_window(dialog) # Block until the dialog is destroyed


    def _handle_launch_action(self, action):
        """Processes the outcome of the update prompt."""
        if action == "update":
            success = self._download_update_core()
            if success:
                self._launch_app_core()
        elif action == "launch":
            self._launch_app_core()

    
    def _download_update_core(self):
        """
        Fetches the latest FlightList.exe and manifest version from the GitHub raw repository.
        Returns True on success, False otherwise.
        """
        self.status_var.set("Downloading latest FlightList.exe...")
        self.update_idletasks()
        
        try:
            # 1. Download the executable file
            file_response = requests.get(EXE_DOWNLOAD_URL, stream=True, timeout=30)
            file_response.raise_for_status()

            # 2. Save the file to the local path in binary mode
            with open(EXE_PATH, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 3. Update the local version tag only after successful download and save
            if self.remote_version_info:
                # Save the new remote manifest info to local version.txt
                self._save_local_version(self.remote_version_info)
                remote_date_str = self.remote_version_info['date'].strftime('%d/%m/%Y')
                self.status_var.set(f"Update complete! Installed version from {remote_date_str}.")
            else:
                self.status_var.set("Download complete, but manifest was inaccessible. Version not saved.")

            # Update the main status label's color after successful update
            self.status_label.config(bootstyle="secondary")
            
            return True

        except requests.exceptions.HTTPError as e:
            self.status_var.set(f"HTTP Error: Could not download EXE from raw repo ({e.response.status_code}).")
        except requests.exceptions.ConnectionError:
            self.status_var.set("Error: Network connection failed during download.")
        except requests.exceptions.Timeout:
            self.status_var.set("Error: Download request timed out.")
        except Exception as e:
            self.status_var.set(f"An unexpected error occurred during update: {type(e).__name__}: {e}")
        
        return False

    def _show_sim_path_prompt(self, launch_checklist_process):
        """
        Custom dialog to prompt the user to set the Flight Sim path, with option to skip permanently.
        """
        # We need a non-blocking way to get the result from the file dialog back to the Toplevel
        self.sim_prompt_result = None
        
        dialog = tk.Toplevel(self)
        dialog.title("Flight Simulator Path Missing")
        dialog.geometry("450x250")
        dialog.configure(bg=bst.Style().colors.get('bg'))
        dialog.transient(self)
        dialog.grab_set()
        
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (dialog.winfo_reqwidth() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (dialog.winfo_reqheight() // 2)
        dialog.geometry(f"+{x}+{(y)}")

        skip_var = tk.IntVar(value=0)
        
        def handle_set_now():
            dialog.destroy()
            self._select_and_save_sim_path() # Opens file dialog and saves path
            # After setting, relaunch core flow to launch the sim (as checklist is already running)
            self._launch_sim_and_exit()
        
        def handle_not_now():
            if skip_var.get() == 1:
                self._save_sim_path(SKIP_PROMPT_SIM_LAUNCH)
            dialog.destroy()
            self.status_var.set("Sim launch skipped by user. Closing launcher...")
            self.after(500, self.destroy)
        
        content_frame = ttk.Frame(dialog, padding=15)
        content_frame.pack(fill='both', expand=True)

        ttk.Label(content_frame, text="Flight Simulator Path is Not Set", font=('Inter', 12, 'bold'), bootstyle="warning").pack(pady=(0, 10))
        
        message = "The launcher cannot start your Flight Simulator (e.g., MSFS, X-Plane). Would you like to set the path now?"
        ttk.Label(content_frame, text=message, wraplength=420, bootstyle="secondary").pack(pady=(0, 15))
        
        # Checkbox for Don't Remind Me Again
        ttk.Checkbutton(
            content_frame,
            text="Don't remind me again",
            variable=skip_var,
            bootstyle="square-toggle"
        ).pack(pady=5)
        
        # Button Frame
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Set Now", command=handle_set_now, bootstyle="success").pack(side='left', padx=10)
        ttk.Button(button_frame, text="Not Now", command=handle_not_now, bootstyle="secondary").pack(side='left', padx=10)
        
        # Set a protocol to treat window close as "Not Now"
        dialog.protocol("WM_DELETE_WINDOW", handle_not_now)
        self.wait_window(dialog)

    def _launch_sim_and_exit(self):
        """
        Launches the Flight Simulator (if path is valid) and then closes the launcher.
        This is called after the Checklist app is already running.
        """
        if self.flight_sim_path and os.path.exists(self.flight_sim_path):
            self.status_var.set("Launching Flight Simulator...")
            self.update_idletasks()
            try:
                # Launch the sim non-blocking
                subprocess.Popen([self.flight_sim_path])
                self.status_var.set("Flight Sim launched. Closing launcher...")
            except Exception as e:
                self.status_var.set(f"Error launching Flight Sim: {e}. Closing launcher.")
        else:
            self.status_var.set("Sim path remains unset or invalid. Closing launcher...")
            
        # 3. Close the launcher entirely
        self.after(500, self.destroy) # Close launcher after a short delay

    def _launch_app_core(self):
        """
        Launches the Checklist app first, handles the Sim path prompt, then launches the Sim.
        """
        if not os.path.exists(EXE_PATH):
            self.status_var.set("Error: FlightList.exe not found. Cannot launch.")
            return

        # 1. Launch FlightList.exe first
        self.status_var.set("1. Launching FlightList.exe...")
        self.update_idletasks()
        try:
            # Launch the checklist app non-blocking
            subprocess.Popen([EXE_PATH])
        except Exception as e:
            self.status_var.set(f"Error launching checklist app: {e}. Aborting launch sequence.")
            return

        # 2. Check Sim Path and Prompt if necessary
        sim_path_valid = self.flight_sim_path and os.path.exists(self.flight_sim_path)
        
        if not sim_path_valid and not self.skip_sim_prompt:
            # Show the prompt dialog. This call is blocking until the user selects an option.
            self.status_var.set("Sim path missing. Awaiting user input...")
            self.update_idletasks()
            self._show_sim_path_prompt(subprocess.Popen)
        else:
            # 3. Launch Sim (or just exit if sim path is set/skip is active)
            self._launch_sim_and_exit()


    def open_lists_folder(self):
        """Shows instructions and opens the Lists folder."""
        
        instructions = (
            "1. Create **aircraft folders** (e.g., 'Airbus A320').\n"
            "2. Inside the aircraft folder, create your checklist files, numbered sequentially (e.g., '01 Cold and Dark.txt', '02 Taxi.txt').\n"
            "3. Ensure files are saved as **.txt**.\n"
            "4. Close this window and click 'Let's Fly!' to load your lists."
        )

        Messagebox.show_info(
            title="Checklist Setup Instructions",
            message=instructions,
            parent=self
        )
        
        try:
            if sys.platform == "win32":
                os.startfile(LISTS_DIR)
            else:
                opener = 'xdg-open' if sys.platform.startswith('linux') else 'open'
                subprocess.Popen([opener, LISTS_DIR])
            self.status_var.set(f"Opened folder: {LISTS_DIR}")
        except Exception as e:
            self.status_var.set(f"Error opening folder: {e}. Check if path exists.")


if __name__ == "__main__":
    try:
        # Check for external dependencies first
        import ttkbootstrap as bst
        import requests 
        from packaging.version import parse as parse_version
        from datetime import datetime
    except ImportError:
        print("Required libraries ('requests', 'ttkbootstrap', 'packaging', and 'datetime') are missing. Install with: pip install requests ttkbootstrap packaging")
        sys.exit(1)

    app = ChecklistLauncher()
    app.mainloop()
