import customtkinter as ctk

class ProgressPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.label = ctk.CTkLabel(self, text="Waiting to start...", font=("Arial", 12))
        self.label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(fill="x", padx=10, pady=(0, 10))
        self.progress_bar.set(0)
        
        # Log view (collapsible logic could go here, simplified for now)
        self.log_box = ctk.CTkTextbox(self, height=150, font=("Consolas", 10))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_box.configure(state="disabled")

    def update_progress(self, item_name, progress):
        self.label.configure(text=f"Installing: {item_name}...")
        self.progress_bar.set(progress)
        
    def add_log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        
    def set_status(self, text):
        self.label.configure(text=text)

