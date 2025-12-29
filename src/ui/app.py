import customtkinter as ctk
from src.config.manager import config_manager
from src.ui.components.sidebar import Sidebar
from src.ui.components.activity_center import ActivityCenter
from src.ui.views.overview import OverviewFrame
from src.ui.views.devtools import DevToolsFrame
from src.ui.views.comfyui import ComfyUIFrame
from src.ui.views.settings import SettingsFrame

class App(ctk.CTk):
    """
    The main application class for the AI Universal Suite.
    This class sets up the main window, sidebar, content area, and activity center.
    It also handles navigation between different views.
    """
    def __init__(self):
        super().__init__()
        
        # Config Theme
        ctk.set_appearance_mode(config_manager.get("theme", "Dark"))
        ctk.set_default_color_theme("blue")
        
        self.title("Universal AI Suite")
        self.geometry("1200x800")
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0) # For Activity Center
        
        # Sidebar
        self.sidebar = Sidebar(self, self.navigate)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        # Content Area
        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Activity Center (Bottom Panel)
        self.activity_center = ActivityCenter(self)
        self.activity_center.grid(row=1, column=1, sticky="ew")
        
        # Initialize Frames
        self.frames = {
            "overview": OverviewFrame(self.content_area, self),
            "devtools": DevToolsFrame(self.content_area, self),
            "comfyui": ComfyUIFrame(self.content_area, self),
            "settings": SettingsFrame(self.content_area, self)
        }
        
        # Show Start Frame
        self.current_frame = None
        self.navigate("overview")

    def navigate(self, name):
        """Switches the view in the main content area."""
        if self.current_frame:
            self.current_frame.pack_forget()
        
        self.current_frame = self.frames.get(name)
        if self.current_frame:
            self.current_frame.pack(fill="both", expand=True)

    def add_activity(self, task_id, name):
        """Thread-safely adds a new task to the activity center."""
        self.after(0, lambda: self.activity_center.add_task(task_id, name))

    def update_activity(self, task_id, progress):
        """Thread-safely updates the progress of a task."""
        self.after(0, lambda: self.activity_center.update_task(task_id, progress))

    def complete_activity(self, task_id):
        """Thread-safely marks a task as complete and removes it after a delay."""
        self.after(1000, lambda: self.activity_center.remove_task(task_id))
