import customtkinter as ctk

class ActivityTask(ctk.CTkFrame):
    """A single row representing an active task (e.g. Downloading Flux)"""
    def __init__(self, master, task_name):
        super().__init__(master, fg_color="transparent")
        
        self.label = ctk.CTkLabel(self, text=task_name, font=("Arial", 12))
        self.label.pack(side="left", padx=10)
        
        self.progress = ctk.CTkProgressBar(self, width=200)
        self.progress.pack(side="left", padx=10)
        self.progress.set(0)
        
        self.status_pct = ctk.CTkLabel(self, text="0%", font=("Arial", 10, "bold"), width=40)
        self.status_pct.pack(side="left", padx=5)

    def update_progress(self, value):
        """value: float between 0 and 1"""
        self.progress.set(value)
        self.status_pct.configure(text=f"{int(value * 100)}%")

class ActivityCenter(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, height=150, corner_radius=0, border_width=1, border_color=("gray80", "gray20"))
        
        self.pack_propagate(False) # Keep fixed height
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(header, text="Activity Center", font=("Arial", 13, "bold")).pack(side="left")
        self.count_label = ctk.CTkLabel(header, text="(0 Active Tasks)", text_color="gray")
        self.count_label.pack(side="left", padx=10)
        
        # Tasks Container (Scrollable)
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tasks = {}

    def add_task(self, task_id, task_name):
        if task_id in self.tasks:
            return
        
        task_row = ActivityTask(self.scroll_frame, task_name)
        task_row.pack(fill="x", pady=2)
        self.tasks[task_id] = task_row
        self.update_count()

    def update_task(self, task_id, progress):
        if task_id in self.tasks:
            self.tasks[task_id].update_progress(progress)

    def remove_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id].destroy()
            del self.tasks[task_id]
            self.update_count()

    def update_count(self):
        count = len(self.tasks)
        self.count_label.configure(text=f"({count} Active Tasks)")
        if count == 0:
            # Maybe hide or minimize? For now just keep empty state
            pass
