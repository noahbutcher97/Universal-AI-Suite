import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, navigate_callback):
        super().__init__(master, width=220, corner_radius=0)
        self.navigate_callback = navigate_callback
        
        self.logo = ctk.CTkLabel(self, text="Universal\nAI Suite", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo.pack(pady=(30, 20))
        
        self.create_nav_btn("Dashboard", "overview")
        self.create_nav_btn("Dev Tools (CLI)", "devtools")
        self.create_nav_btn("ComfyUI Studio", "comfyui")
        self.create_nav_btn("Settings & Keys", "settings")
        
        self.exit_btn = ctk.CTkButton(self, text="Exit", fg_color="transparent", border_width=1, command=master.quit)
        self.exit_btn.pack(side="bottom", pady=20, padx=20, fill="x")

    def create_nav_btn(self, text, view_name):
        btn = ctk.CTkButton(
            self, 
            text=text, 
            height=40, 
            anchor="w", 
            fg_color="transparent", 
            text_color=("gray10", "gray90"), 
            hover_color=("gray70", "gray30"),
            command=lambda: self.navigate_callback(view_name)
        )
        btn.pack(fill="x", padx=10, pady=5)
