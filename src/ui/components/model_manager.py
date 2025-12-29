import customtkinter as ctk
from tkinter import ttk, messagebox
from src.services.comfy_service import ComfyService
from src.config.manager import config_manager

class ModelManagerFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.comfy_path = config_manager.get("comfy_path")

        ctk.CTkLabel(self, text="Model Manager", font=("Arial", 16, "bold")).pack(pady=10)

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(main_frame, show="tree")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.tree.heading("#0", text="Models")

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="ns", padx=10, pady=10)

        ctk.CTkButton(button_frame, text="Add Model", state="disabled").pack(fill="x", pady=5)
        ctk.CTkButton(button_frame, text="Delete Selected", command=self.delete_selected).pack(fill="x", pady=5)
        ctk.CTkButton(button_frame, text="Move Selected", state="disabled").pack(fill="x", pady=5)
        ctk.CTkButton(button_frame, text="Refresh", command=self.populate_tree).pack(side="bottom", fill="x", pady=10)

        self.populate_tree()

    def populate_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        model_structure = ComfyService.get_models_structure(self.comfy_path)
        for dir_name, files in model_structure.items():
            dir_id = self.tree.insert("", "end", text=dir_name, open=True)
            for file_name in files:
                self.tree.insert(dir_id, "end", text=file_name)

    def delete_selected(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Delete", "No item selected.")
            return

        selected_id = selected_item[0]
        parent_id = self.tree.parent(selected_id)

        # We only allow deleting files (models), not folders.
        if not parent_id:
            messagebox.showwarning("Delete", "Cannot delete model type folders.")
            return

        model_type = self.tree.item(parent_id, "text")
        filename = self.tree.item(selected_id, "text")

        if messagebox.askyesno("Delete", f"Are you sure you want to delete {filename}?"):
            try:
                ComfyService.delete_model_file(self.comfy_path, model_type, filename)
                self.populate_tree()
                messagebox.showinfo("Delete", f"{filename} deleted successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {e}")
