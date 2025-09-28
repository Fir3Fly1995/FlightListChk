import tkinter as tk
from tkinter import ttk, filedialog
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
GITHUB_REPO = "Fir3Fly1995/FlightListChk" # Your GitHub repository
EXE_FILENAME = "FlightList.exe"

# --- NEW CONFIG FILE ---
SIM_PATH_FILE = os.path.join(MAIN_FOLDER, 'sim_path.txt')

class ChecklistLauncher(bst.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("Flight Checklist Launcher")
        self.geometry("420x340") # Slightly larger window
        
        # Ensure the main directory structure exists immediately
        os.makedirs(MAIN_FOLDER, exist_ok=True)
        os.makedirs(LISTS_DIR, exist_ok=True)
        
        # Load the saved flight simulator path
        self.flight_sim_path = ""
        self._load_sim_path()

        self.create_widgets()

    def _load_sim_path(self):
        """Loads the saved Flight Simulator executable path from the file."""
        try:
            with open(SIM_PATH_FILE, 'r') as f:
                path = f.read().strip()
                if os.path.exists(path):
                    self.flight_sim_path = path
        except FileNotFoundError:
            # File doesn't exist yet, path remains empty
            pass
        except Exception as e:
            print(f"Error loading sim path: {e}")
            self.flight_sim_path = "" # Reset on error

    def _select_and_save_sim_path(self):
        """Opens a file dialog for the user to select the sim executable and saves the path."""
        # Use initialdir hint if a path was previously attempted or common locations
        initial_dir = os.path.dirname(self.flight_sim_path) if self.flight_sim_path else 'C:\\Program Files'
        
        selected_path = filedialog.askopenfilename(
            title="Select Your Flight Simulator Executable (e.g., X-Plane.exe, MSFS.exe)",
            initialdir=initial_dir,
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")]
        )

        if selected_path:
            self.flight_sim_path = selected_path
            # Save the new path
            try:
                with open(SIM_PATH_FILE, 'w') as f:
                    f.write(selected_path)
                self.status_var.set(f"Sim path set: {os.path.basename(selected_path)}")
            except Exception as e:
                self.status_var.set(f"Error saving path: {e}")
            
            # Re-run status check to update the initial message label
            self.status_var.set(self.get_initial_status())
        else:
            self.status_var.set("Flight Simulator path selection cancelled.")


    def get_initial_status(self):
        """Returns the appropriate status message on startup."""
        exe_status = "Local FlightList.exe found." if os.path.exists(EXE_PATH) else "No local FlightList.exe found."
        sim_status = "Sim path configured." if self.flight_sim_path and os.path.exists(self.flight_sim_path) else "Sim path NOT set."
        return f"{exe_status} | {sim_status}"


    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill='both', expand=True)

        ttk.Label(main_frame, text="Flight Checklist Launcher", font=('Inter', 18, 'bold'), bootstyle="primary").pack(pady=(0, 20))
        
        # Set Flight Sim Path Button (New)
        ttk.Button(
            main_frame,
            text="Set Flight Sim Path",
            command=self._select_and_save_sim_path,
            bootstyle="warning-outline", # Orange for visibility
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

        # Let's Fly Button (Now triggers the update prompt)
        ttk.Button(
            main_frame,
            text="Let's Fly!",
            command=self.prompt_and_launch, # New command handles the decision flow
            bootstyle="success",
            width=25
        ).pack(pady=10)

        self.status_var = tk.StringVar(value=self.get_initial_status())
        ttk.Label(main_frame, textvariable=self.status_var, bootstyle="secondary", wraplength=400).pack(pady=10)


    def prompt_and_launch(self):
        """Displays the update/launch prompt before proceeding."""
        
        if os.path.exists(EXE_PATH):
             # Ask the user for their preference using custom buttons
             answer = Messagebox.show_question(
                title="Update Check",
                message="Would you like to check for and download the latest version, or just launch the version you currently have?",
                buttons=[
                    ("Update & Fly", "update"),
                    ("Just Fly", "launch")
                ],
                parent=self
            )
             
             if answer == "update":
                # If they choose update, download first, then launch
                success = self._download_update_core()
                if success:
                    self._launch_app_core()
             elif answer == "launch":
                # If they choose just launch, skip download
                self._launch_app_core()

        else:
            # If the EXE doesn't exist, skip the prompt and force download/launch
            self.status_var.set("No local file found. Automatically downloading and launching...")
            self.update_idletasks()
            success = self._download_update_core()
            if success:
                self._launch_app_core()

    def _download_update_core(self):
        """
        Fetches the latest FlightList.exe from the GitHub Releases API.
        Returns True on success, False otherwise.
        """
        self.status_var.set("Checking GitHub for the latest release...")
        self.update_idletasks()
        
        API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        
        try:
            # 1. Get the latest release metadata
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status() # Raises HTTPError for bad status codes (4xx or 5xx)
            release_info = response.json()

            # 2. Find the FlightList.exe asset
            download_url = None
            for asset in release_info.get('assets', []):
                if asset['name'] == EXE_FILENAME:
                    download_url = asset['browser_download_url']
                    break
            
            if not download_url:
                self.status_var.set(f"Error: {EXE_FILENAME} asset not found in latest release.")
                return False

            # 3. Download the executable file
            self.status_var.set("Downloading new version...")
            self.update_idletasks()
            
            # Use stream=True for potentially large files
            file_response = requests.get(download_url, stream=True, timeout=30)
            file_response.raise_for_status()

            # 4. Save the file to the local path in binary mode
            with open(EXE_PATH, 'wb') as f:
                # Write file in chunks to handle memory efficiently
                for chunk in file_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            version = release_info.get('tag_name', 'Unknown')
            self.status_var.set(f"Update complete! Version {version} downloaded.")
            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.status_var.set("Error: Repository or release not found. Check GITHUB_REPO variable.")
        except requests.exceptions.ConnectionError:
            self.status_var.set("Error: Network connection failed. Check your internet connection.")
        except requests.exceptions.Timeout:
            self.status_var.set("Error: Request timed out. GitHub server may be slow.")
        except Exception as e:
            self.status_var.set(f"An unexpected error occurred during update: {type(e).__name__}: {e}")
        
        return False

    def _launch_app_core(self):
        """
        Launches the Flight Simulator, then the checklist app, then closes the launcher.
        """
        if os.path.exists(EXE_PATH):
            
            # 1. Launch Flight Simulator (using the loaded path)
            sim_launched = False
            if self.flight_sim_path:
                self.status_var.set("1. Launching Flight Simulator...")
                self.update_idletasks()
                
                if os.path.exists(self.flight_sim_path):
                    try:
                        subprocess.Popen([self.flight_sim_path])
                        self.status_var.set("Flight Sim launched. 2. Launching FlightList.exe...")
                        sim_launched = True
                    except Exception as e:
                        self.status_var.set(f"Error launching Flight Sim: {e}. 2. Launching Checklist anyway.")
                else:
                    self.status_var.set(f"WARNING: Sim path not found on disk. 2. Launching Checklist only.")
            
            if not sim_launched:
                 self.status_var.set("1. Skipped Flight Sim launch (Path not set or invalid). 2. Launching FlightList.exe...")
                 self.update_idletasks()


            # 2. Launch FlightList.exe
            try:
                # Use Popen to launch the exe and not block the Tkinter thread
                subprocess.Popen([EXE_PATH])
                
                # 3. Close the launcher entirely
                self.status_var.set("3. Launch successful. Closing launcher...")
                self.after(500, self.destroy) # Close launcher after a short delay
            except OSError as e:
                self.status_var.set(f"Error launching checklist app: {e}")
            except Exception as e:
                self.status_var.set(f"Unknown error launching checklist app: {e}")
        else:
            self.status_var.set("Error: FlightList.exe not found and download failed.")

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
                # Use os.startfile on Windows
                os.startfile(LISTS_DIR)
            else:
                # Fallback for non-Windows systems (e.g., Mac or Linux)
                opener = 'xdg-open' if sys.platform.startswith('linux') else 'open'
                subprocess.Popen([opener, LISTS_DIR])
            # The get_initial_status updates the status bar at launch, so we only update on error or action success
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
