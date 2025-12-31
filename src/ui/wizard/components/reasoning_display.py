import customtkinter as ctk

class ReasoningDisplay(ctk.CTkFrame):
    def __init__(self, master, reasoning_list):
        super().__init__(master, fg_color="transparent")
        
        ctk.CTkLabel(self, text="Why this recommendation?", font=("Arial", 12, "bold"), text_color="gray80").pack(anchor="w", pady=(0, 5))
        
        for reason in reasoning_list:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text="•", text_color="#4cc9f0", width=15).pack(side="left", anchor="n")
            ctk.CTkLabel(row, text=reason, font=("Arial", 12), text_color="gray70", justify="left", wraplength=450).pack(side="left", fill="x")
