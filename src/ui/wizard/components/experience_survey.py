import customtkinter as ctk

class ExperienceSurvey(ctk.CTkFrame):
    def __init__(self, master, on_next):
        super().__init__(master, fg_color="transparent")
        self.on_next = on_next
        
        ctk.CTkLabel(self, text="Customize Your Experience", font=("Arial", 20, "bold")).pack(pady=(20, 30))
        
        # AI Experience
        self.ai_var = ctk.IntVar(value=3)
        self._build_slider_group("How familiar are you with AI tools?", self.ai_var, ["Newcomer", "Dabbler", "User", "Advanced", "Pro"])
        
        # Tech Experience
        self.tech_var = ctk.IntVar(value=3)
        self._build_slider_group("Technical Proficiency", self.tech_var, ["Non-Tech", "Basic", "Comfortable", "Dev", "Expert"])
        
        ctk.CTkButton(self, text="Next", height=40, command=self.on_continue).pack(pady=40, ipadx=20)
        
    def _build_slider_group(self, title, variable, labels):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=50, pady=20)
        
        ctk.CTkLabel(f, text=title, font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        slider = ctk.CTkSlider(f, from_=1, to=5, number_of_steps=4, variable=variable)
        slider.pack(fill="x", pady=5)
        
        # Labels row
        lbls = ctk.CTkFrame(f, fg_color="transparent")
        lbls.pack(fill="x")
        lbls.grid_columnconfigure((0,1,2,3,4), weight=1)
        
        for i, txt in enumerate(labels):
            ctk.CTkLabel(lbls, text=txt, font=("Arial", 10)).grid(row=0, column=i)

    def on_continue(self):
        self.on_next(self.ai_var.get(), self.tech_var.get())
