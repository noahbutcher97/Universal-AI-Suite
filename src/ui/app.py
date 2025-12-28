import customtkinter as ctk
from src.config.manager import config_manager
from src.ui.components.sidebar import Sidebar
from src.ui.components.activity_center import ActivityCenter
from src.ui.views.overview import OverviewFrame
from src.ui.views.devtools import DevToolsFrame
from src.ui.views.comfyui import ComfyUIFrame
from src.ui.views.settings import SettingsFrame

class App(ctk.CTk):
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
        # Row 1 will be for the Activity Center
        self.grid_rowconfigure(1, weight=0)
        
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
        self.frames = {}
        self.frames["overview"] = OverviewFrame(self.content_area, self)
        self.frames["devtools"] = DevToolsFrame(self.content_area, self)
        self.frames["comfyui"] = ComfyUIFrame(self.content_area, self)
        self.frames["settings"] = SettingsFrame(self.content_area, self)
        
        # Show Start Frame
        self.current_frame = None
        self.navigate("overview")

    def navigate(self, name):
        if self.current_frame:
            self.current_frame.pack_forget()
        
        self.current_frame = self.frames.get(name)
        if self.current_frame:
            self.current_frame.pack(fill="both", expand=True)

    def add_activity(self, task_id, name):
        """Thread-safe way to add activity"""
        self.after(0, lambda: self.activity_center.add_task(task_id, name))

    def update_activity(self, task_id, progress):
        """Thread-safe way to update activity progress (0.0 to 1.0)"""
        self.after(0, lambda: self.activity_center.update_task(task_id, progress))

    def complete_activity(self, task_id):
        """Thread-safe way to remove/complete activity"""
        # Small delay so user sees 100%
        self.after(1000, lambda: self.activity_center.remove_task(task_id))
