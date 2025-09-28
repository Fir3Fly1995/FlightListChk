import tkinter as tk
from tkinter import ttk
import ttkbootstrap as bst
from ttkbootstrap.scrolled import ScrolledFrame
import os
import sys
import re # Added for flexible filename formatting
# Can be found at https://github.com/Fir3Fly1995/FlightListChk Please check the LICENCE.md for usage.
# --- Configuration ---
# Get the appropriate directory for app data
LOCAL_APPDATA = os.getenv('LOCALAPPDATA')
# Updated path to place Lists directly under FLTCHKLST: %Localappdata%/FLTCHKLST/Lists
LISTS_DIR = os.path.join(LOCAL_APPDATA, 'FLTCHKLST', 'Lists')
APP_TITLE = "Flight Checklist"

# Define a simple in-memory data structure for checklist state persistence:
# { 'AircraftName': { 'ChecklistFilename': { line_index: bool_checked, ... } } }
# This dictionary will now only store boolean values (True/False).
CHECKLIST_STATES = {}

def format_filename_for_display(filename):
    """
    Converts a raw filename (e.g., '01Cold_and_Dark.txt' or '01ColdandDark.txt')
    into a clean, readable display name (e.g., '01 Cold and Dark').
    """
    # 1. Strip extension and replace underscores with spaces
    base_name = filename.replace('.txt', '').replace('_', ' ')
    
    # 2. Insert a space after leading digits if a non-digit character immediately follows.
    # Regex: (\d+) captures leading digits, ([A-Za-z]) captures the first letter.
    # We replace '01Cold...' with '01 Cold...'.
    match = re.match(r'(\d+)([A-Za-z])', base_name)
    if match:
        digits = match.group(1)
        first_char = match.group(2)
        # Reconstruct: digits + space + first char + rest of string
        rest = base_name[len(digits) + len(first_char):]
        return f"{digits} {first_char}{rest}"
    
    # If no leading digits are found, return the base name
    return base_name

class FlightList(bst.Window):
    """
    Main application window for the interactive Flight Checklist.
    """
    def __init__(self):
        # Initialize the main window with the 'darkly' theme
        super().__init__(themename="darkly")
        self.title(APP_TITLE)
        self.geometry("800x600")

        # Public variable to track the currently loaded checklist
        self.current_aircraft = None
        self.current_filename = None
        self.current_filepath = None
        
        # New: List to hold the currently displayed tk.BooleanVar objects.
        # This prevents the variables from being garbage collected and allows
        # runtime checking of the current checklist state.
        self.active_vars = []

        # Ensure the base list directory exists (but no dummy files)
        self.setup_data_directory()
        
        # Build the main UI
        self.create_widgets()

        # Load the checklist structure (tabs and file lists)
        self.load_checklist_structure()

    def setup_data_directory(self):
        """
        Ensures the base Lists directory exists. 
        Dummy aircraft/checklist files are NO longer created here,
        as the user is expected to create them manually.
        """
        os.makedirs(LISTS_DIR, exist_ok=True)
        
        print(f"Checklist files expected in: {LISTS_DIR}")


    def create_widgets(self):
        """Build the main UI elements: Notebook for aircraft and a container for content."""
        
        # 1. Main Notebook (for Airbus/Boeing tabs)
        self.aircraft_notebook = ttk.Notebook(self)
        self.aircraft_notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 2. Checklist Display Frame (Will be updated dynamically)
        self.checklist_display_frame = ScrolledFrame(self, padding=10)
        self.checklist_display_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Title/Status label above the checklist area
        self.checklist_title_var = tk.StringVar(value="Select an aircraft checklist to begin.")
        ttk.Label(
            self.checklist_display_frame, 
            textvariable=self.checklist_title_var,
            font=('Inter', 14, 'bold'),
            bootstyle="primary"
        ).pack(fill='x', pady=(0, 10))
        
        # Container for the actual checklist checkboxes
        self.checklist_items_container = ttk.Frame(self.checklist_display_frame)
        self.checklist_items_container.pack(fill='both', expand=True)

        # 3. Control Bar (Uncheck All)
        control_frame = ttk.Frame(self)
        control_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Button(
            control_frame,
            text="Uncheck All Items",
            command=self.uncheck_all,
            # Use green 'success-outline' bootstyle
            bootstyle="success-outline" 
        ).pack(side='right', padx=5)


    def load_checklist_structure(self):
        """
        Scans the LISTS_DIR for aircraft folders and checklist files,
        building the Notebook tabs and selector Treeviews.
        """
        
        # Get all subdirectories (aircraft names)
        aircraft_folders = [d for d in os.listdir(LISTS_DIR) 
                            if os.path.isdir(os.path.join(LISTS_DIR, d))]
        
        if not aircraft_folders:
            # Display a clearer message if no aircraft folders are found
            self.checklist_title_var.set("No aircraft folders found. Use the Launcher's 'Open Lists Folder' button to add your checklists.")
            
            # Show placeholder message in the content area
            for widget in self.checklist_items_container.winfo_children():
                widget.destroy()
            ttk.Label(self.checklist_items_container, 
                      text="Please create manufacturer folders (e.g., 'Boeing 737') and add numbered .txt checklist files inside them.",
                      bootstyle="secondary").pack(padx=20, pady=20)
            return

        for aircraft in sorted(aircraft_folders):
            # Create a tab for each aircraft (e.g., "Airbus A320")
            aircraft_tab = ttk.Frame(self.aircraft_notebook)
            self.aircraft_notebook.add(aircraft_tab, text=aircraft)
            
            # Create a PanedWindow inside the tab to hold the file selector and a placeholder
            paned_window = ttk.PanedWindow(aircraft_tab, orient=tk.HORIZONTAL)
            paned_window.pack(fill='both', expand=True)

            # Left Pane: Checklist File Selector (Treeview)
            tree_frame = ttk.Frame(paned_window, width=250)
            
            tree = ttk.Treeview(
                tree_frame, 
                columns=('filename'), 
                show='headings', 
                selectmode='browse'
            )
            tree.heading('filename', text='Select Checklist')
            tree.column('filename', width=250, stretch=tk.YES)
            
            # Scrollbar for the Treeview
            tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=tree_scrollbar.set)
            
            tree.pack(side='left', fill='both', expand=True)
            tree_scrollbar.pack(side='right', fill='y')
            
            # Bind selection event to display the checklist
            tree.bind('<<TreeviewSelect>>', 
                      lambda e, a=aircraft, t=tree: self.on_tree_select(a, t))

            paned_window.add(tree_frame, weight=1)
            
            # Right Pane: Instructions (initially blank)
            instruction_frame = ttk.Frame(paned_window)
            ttk.Label(instruction_frame, 
                      text=f"Checklist items for {aircraft} will appear below the tabs.",
                      bootstyle="secondary").pack(padx=20, pady=20)
            paned_window.add(instruction_frame, weight=0) # Weight 0 because content is in the main frame

            # Populate the Treeview with checklist files
            # These are sorted alphabetically, so numbering (01, 02) is critical
            checklist_files = sorted([f for f in os.listdir(os.path.join(LISTS_DIR, aircraft)) 
                                       if f.endswith('.txt')])
            
            # Store the sorted list of files for progression logic
            CHECKLIST_STATES.setdefault(aircraft, {})['__ORDER__'] = checklist_files
            
            for filename in checklist_files:
                # NEW: Use the helper function to format the name for display
                display_name = format_filename_for_display(filename)
                tree.insert('', tk.END, text=display_name, values=(filename,))

            # Store the Treeview instance for later use (e.g., progression)
            CHECKLIST_STATES[aircraft]['__TREEVIEW__'] = tree


    def on_tree_select(self, aircraft, tree):
        """Handles checklist selection from the Treeview."""
        selected_item = tree.focus()
        if not selected_item:
            return

        filename = tree.item(selected_item, 'values')[0]
        filepath = os.path.join(LISTS_DIR, aircraft, filename)
        
        self.show_checklist(aircraft, filename, filepath, tree)


    def show_checklist(self, aircraft, filename, filepath, tree):
        """
        Loads the content of the selected checklist file and displays it
        with persistent checkboxes.
        """
        if self.current_filepath == filepath:
            return # Already showing this checklist

        self.current_aircraft = aircraft
        self.current_filename = filename
        self.current_filepath = filepath
        
        # NEW: Use the helper function to format the name for the title
        self.checklist_title_var.set(f"{aircraft} - {format_filename_for_display(filename)}")

        # Clear existing checklist items
        for widget in self.checklist_items_container.winfo_children():
            widget.destroy()

        # Reset the list of active BooleanVars for the new checklist
        self.active_vars = []

        # Initialize persistence structure for this checklist if it doesn't exist
        checklist_states_map = CHECKLIST_STATES.setdefault(aircraft, {}).setdefault(filename, {})
        
        try:
            with open(filepath, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
        except Exception as e:
            ttk.Label(self.checklist_items_container, 
                      text=f"Error loading file: {e}", 
                      bootstyle="danger").pack(padx=20, pady=20)
            return

        # Create checkboxes for each line
        for i, item in enumerate(lines):
            
            # Retrieve the boolean state from persistence, default to False
            initial_state = checklist_states_map.get(i, False)
            
            # Create a new tk.BooleanVar for the current session/display
            var = tk.BooleanVar(value=initial_state)
            
            # Store the variable reference to prevent garbage collection and for checking state
            self.active_vars.append(var)
            
            # The command needs to pass all context for updating the state and progression
            cmd = lambda idx=i, v=var: self.handle_checkbox_click(aircraft, filename, idx, v, len(lines), tree)
            
            chk = ttk.Checkbutton(
                self.checklist_items_container,
                text=item,
                variable=var,
                command=cmd,
                bootstyle="success", # CHANGED: Use standard checkbox style with 'success' color
                padding=5
            )
            chk.pack(fill='x', pady=2, padx=10, anchor='w')
            
            # Ensure the state map has an entry for this item (only the boolean value)
            checklist_states_map[i] = initial_state 

        # Scroll to top of the checklist
        self.checklist_display_frame.update_idletasks()
        self.checklist_display_frame.yview_moveto(0)


    def handle_checkbox_click(self, aircraft, filename, index, var, total_items, tree):
        """
        Updates the state, checks for completion, and handles progression.
        """
        new_state = var.get()
        
        # 1. Update the in-memory data model with the new boolean state
        checklist_states_map = CHECKLIST_STATES[aircraft][filename]
        checklist_states_map[index] = new_state
        
        # 2. Check for checklist completion by iterating through all active BooleanVars
        completed_count = sum(1 for active_var in self.active_vars if active_var.get())
        
        print(f"[{aircraft} / {filename}] Item {index+1}/{total_items} clicked. Completed: {completed_count}/{total_items}")

        if completed_count == total_items:
            # All items are checked, attempt progression
            if hasattr(self, 'status_var'):
                self.status_var.set("Checklist complete. Advancing to the next list...")
            self.after(500, lambda: self.progress_to_next_checklist(aircraft, filename, tree))
        else:
            if hasattr(self, 'status_var'):
                self.status_var.set(f"Progress: {completed_count}/{total_items} items checked.")


    def progress_to_next_checklist(self, aircraft, current_filename, tree):
        """
        Finds the next checklist file in the sequence and automatically selects it.
        """
        file_order = CHECKLIST_STATES[aircraft].get('__ORDER__', [])
        
        try:
            current_index = file_order.index(current_filename)
            next_index = current_index + 1
            
            if next_index < len(file_order):
                next_filename = file_order[next_index]
                
                # 1. Find the corresponding item ID in the Treeview
                children = tree.get_children()
                next_item_id = None
                for child_id in children:
                    # Treeview stores the filename in the 'values' tuple
                    if tree.item(child_id, 'values')[0] == next_filename:
                        next_item_id = child_id
                        break
                
                if next_item_id:
                    tree.selection_set(next_item_id) # Selects the item visually
                    tree.focus(next_item_id)       # Focuses the item
                    # The bound '<<TreeviewSelect>>' event will automatically call show_checklist
                    self.checklist_title_var.set(f"Checklist complete. Loading next list: {format_filename_for_display(next_filename)}")
                else:
                    self.checklist_title_var.set(f"Sequence complete for {aircraft}! All checklists finished.")

            else:
                self.checklist_title_var.set(f"Sequence complete for {aircraft}! All checklists finished.")
        
        except ValueError:
            print(f"Error: Current filename {current_filename} not found in sequence list.")


    def uncheck_all(self):
        """
        Resets the state of all checkboxes in the currently displayed checklist.
        """
        if not self.current_aircraft or not self.current_filename:
            return

        aircraft = self.current_aircraft
        filename = self.current_filename
        
        # Reset state in the data model
        checklist_states_map = CHECKLIST_STATES[aircraft].get(filename, {})

        # 1. Reset the UI variables
        for var in self.active_vars:
            var.set(False)

        # 2. Update the persistence map
        for index in checklist_states_map.keys():
            checklist_states_map[index] = False
            
        # Update the status
        self.checklist_title_var.set(f"All items in '{format_filename_for_display(filename)}' have been unchecked.")


if __name__ == "__main__":
    # Note: requests library is not needed for this file, only ttkbootstrap
    try:
        import ttkbootstrap as bst
    except ImportError:
        print("The 'ttkbootstrap' library is required. Please install it with: pip install ttkbootstrap")
        sys.exit(1)

    app = FlightList()
    app.mainloop()


# Created by Fir3Fly1995 - Hit me up on GitHub if there are issues! 
# 28/09/2025 - created the app for the first time
