import customtkinter as ctk

class UseCaseCard(ctk.CTkFrame):
    def __init__(self, master, use_case_id, title, description, icon, command=None, selected=False):
        super().__init__(master, corner_radius=10, border_width=2 if selected else 0, border_color="#1f6aa5" if selected else None)
        
        self.use_case_id = use_case_id
        self.command = command
        self.selected = selected
        
        # Layout
        self.grid_columnconfigure(1, weight=1)
        
        # Icon
        self.icon_lbl = ctk.CTkLabel(self, text=icon, font=("Arial", 32))
        self.icon_lbl.grid(row=0, column=0, rowspan=2, padx=15, pady=15)
        
        # Title
        self.title_lbl = ctk.CTkLabel(self, text=title, font=("Arial", 16, "bold"))
        self.title_lbl.grid(row=0, column=1, sticky="w", pady=(15, 0), padx=5)
        
        # Description
        self.desc_lbl = ctk.CTkLabel(self, text=description, font=("Arial", 12), text_color="gray70", wraplength=300, justify="left")
        self.desc_lbl.grid(row=1, column=1, sticky="w", pady=(0, 15), padx=5)
        
        # Make clickable
        self.bind("<Button-1>", self.on_click)
        self.icon_lbl.bind("<Button-1>", self.on_click)
        self.title_lbl.bind("<Button-1>", self.on_click)
        self.desc_lbl.bind("<Button-1>", self.on_click)
        
    def on_click(self, event=None):
        if self.command:
            self.command(self.use_case_id)

    def set_selected(self, selected):
        self.selected = selected
        self.configure(border_width=2 if selected else 0, border_color="#1f6aa5" if selected else None)
