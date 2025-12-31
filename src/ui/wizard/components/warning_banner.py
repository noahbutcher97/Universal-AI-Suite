import customtkinter as ctk

class WarningBanner(ctk.CTkFrame):
    def __init__(self, master, warnings):
        super().__init__(master, fg_color="#3a1c1c", corner_radius=6, border_width=1, border_color="#e63946")
        
        if not warnings:
            self.destroy()
            return
            
        icon = ctk.CTkLabel(self, text="⚠️", font=("Arial", 20))
        icon.pack(side="left", padx=10, pady=10, anchor="n")
        
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="x", expand=True, pady=10, padx=(0, 10))
        
        ctk.CTkLabel(content, text="Issues Detected", font=("Arial", 12, "bold"), text_color="#ff9999").pack(anchor="w")
        
        for w in warnings:
            ctk.CTkLabel(content, text=f"• {w}", font=("Arial", 11), text_color="#ffcccc", justify="left", wraplength=400).pack(anchor="w")
