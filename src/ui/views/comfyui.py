import customtkinter as ctk
from tkinter import filedialog, ttk
import threading
import subprocess
import os
import requests
import sys
from src.config.manager import config_manager
from src.services.comfy_service import ComfyService
from src.services.system_service import SystemService

class ComfyUIFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(self, text="ComfyUI Studio", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        # Path config
        path_frame = ctk.CTkFrame(self)
        path_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(path_frame, text="Install Location:").pack(side="left", padx=10)
        self.comfy_path_lbl = ctk.CTkLabel(path_frame, text=config_manager.get("comfy_path"), text_color="cyan")
        self.comfy_path_lbl.pack(side="left", padx=10)
        ctk.CTkButton(path_frame, text="Change", width=80, command=self.change_comfy_path).pack(side="right", padx=10)
        
        # Wizard
        wiz = ctk.CTkFrame(self)
        wiz.pack(fill="x", pady=20)
        ctk.CTkLabel(wiz, text="Installation Wizard", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkButton(wiz, text="✨ Build Installation Manifest", height=50, fg_color="#6A0dad", command=self.open_wizard).pack(pady=20, fill="x", padx=40)

        # #TODO: Add ComfyUI lifecycle management features.
        # The current UI only supports the initial installation. Key features
        # for a robust tool would include updating and uninstalling.
        #
        # Suggested implementation:
        # 1. Add "Update ComfyUI" and "Uninstall ComfyUI" buttons.
        # 2. Update: Should run `git pull` in the core and manager directories,
        #    and potentially update other custom nodes. This should be a
        #    service-layer function.
        # 3. Uninstall: Should provide a confirmation dialog and then remove
        #    the entire ComfyUI directory. This should also be a service-layer
        #    function.

    def change_comfy_path(self):
        p = filedialog.askdirectory(initialdir=config_manager.get("comfy_path"))
        if p:
            config_manager.set("comfy_path", p)
            self.comfy_path_lbl.configure(text=p)

    def open_wizard(self):
        win = ctk.CTkToplevel(self)
        win.title("Setup Wizard")
        win.geometry("600x700")
        
        gpu, vram = SystemService.get_gpu_info()
        ctk.CTkLabel(win, text=f"Detected: {gpu} ({vram} GB)", text_color="yellow").pack(pady=10)
        
        ctk.CTkLabel(win, text="Art Style").pack(anchor="w", padx=20)
        style_var = ctk.StringVar(value="General")
        ctk.CTkSegmentedButton(win, values=["Photorealistic", "Anime", "General"], variable=style_var).pack(fill="x", padx=20)
        
        ctk.CTkLabel(win, text="Media Type").pack(anchor="w", padx=20, pady=(10,0))
        media_var = ctk.StringVar(value="Image")
        ctk.CTkSegmentedButton(win, values=["Image", "Video", "Mixed"], variable=media_var).pack(fill="x", padx=20)
        
        consist_var = ctk.BooleanVar()
        ctk.CTkCheckBox(win, text="Consistency (IPAdapter)", variable=consist_var).pack(anchor="w", padx=20, pady=10)
        
        edit_var = ctk.BooleanVar()
        ctk.CTkCheckBox(win, text="Editing (ControlNet)", variable=edit_var).pack(anchor="w", padx=20, pady=5)
        
        def review():
            ans = {
                "style": style_var.get(), 
                "media": media_var.get(), 
                "consistency": consist_var.get(), 
                "editing": edit_var.get()
            }
            manifest = ComfyService.generate_manifest(ans, config_manager.get("comfy_path"))
            self.show_manifest_review(win, manifest)
            
        ctk.CTkButton(win, text="Next: Review Manifest", command=review).pack(side="bottom", fill="x", padx=20, pady=20)

    def show_manifest_review(self, parent, manifest):
        for w in parent.winfo_children(): w.destroy()
        parent.title("Review Manifest")
        
        ctk.CTkLabel(parent, text="Installation Manifest", font=("Arial", 18, "bold")).pack(pady=10)
        
        tree_frame = ctk.CTkFrame(parent)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        tree = ttk.Treeview(tree_frame, columns=("dest"), show="tree headings")
        tree.heading("#0", text="Component / Model")
        tree.heading("dest", text="Destination Folder")
        tree.column("#0", width=250)
        tree.column("dest", width=300)
        tree.pack(fill="both", expand=True)
        
        base_path = config_manager.get("comfy_path")
        for item in manifest:
            short_dest = item['dest'].replace(base_path, "...")
            tree.insert("", "end", text=item['name'], values=(short_dest,))
            
        def execute():
            parent.destroy()
            self.run_install_process(manifest)
            
        ctk.CTkButton(parent, text="Confirm & Install", fg_color="green", height=50, command=execute).pack(fill="x", padx=20, pady=20)

        # #TODO: Add a "Cancel" or "Back" button to the manifest review.
        # The user is currently locked into the installation once they reach
        # this screen. A "Back" button would improve usability.

    def run_install_process(self, manifest):
        # #TODO: Implement a cancellation mechanism for the installation process.
        # Long-running downloads or clones cannot be cancelled by the user.
        #
        # Suggested implementation:
        # 1. Use a threading.Event object that can be checked in the loop.
        # 2. Add a "Cancel" button to the activity center for in-progress tasks.
        # 3. When the button is clicked, set the event. The loop in `process()`
        #    should check `if event.is_set(): break` and perform cleanup.
        def process():
            for item in manifest:
                task_id = f"install_{item['name'].replace(' ', '_')}"
                self.app.add_activity(task_id, f"Processing: {item['name']}")
                
                if not os.path.exists(item['dest']): 
                    os.makedirs(item['dest'], exist_ok=True)
                
                if item['type'] == "clone":
                    if not os.path.exists(os.path.join(item['dest'], ".git")):
                        self.app.update_activity(task_id, 0.5) 
                        # #TODO: Add robust error handling for subprocess calls.
                        # (This is the same issue as in devtools.py)
                        subprocess.call(["git", "clone", item['url'], item['dest']], stdout=subprocess.DEVNULL)
                    
                elif item['type'] == "download":
                    fname = item['url'].split('/')[-1]
                    dest_file = os.path.join(item['dest'], fname)
                    if not ComfyService.verify_file(dest_file, item.get("hash")):
                        try:
                            # #TODO: Handle download errors more gracefully.
                            # A failed download should be clearly marked as failed in
                            # the UI, and the user should be notified. The current
                            # implementation just prints to console.
                            response = requests.get(item['url'], stream=True, timeout=10)
                            response.raise_for_status()
                            total_size = int(response.headers.get('content-length', 0))
                            downloaded = 0
                            
                            with open(dest_file, 'wb') as f:
                                for data in response.iter_content(chunk_size=1024*1024): # 1MB chunks
                                    downloaded += len(data)
                                    f.write(data)
                                    if total_size > 0:
                                        progress = downloaded / total_size
                                        self.app.update_activity(task_id, progress)
                        except Exception as e:
                            print(f"Download FAILED: {e}")
                            # Mark as failed in UI here
                
                self.app.update_activity(task_id, 1.0)
                self.app.complete_activity(task_id)
            
            messagebox.showinfo("Success", "Installation complete!")

        threading.Thread(target=process, daemon=True).start()
        messagebox.showinfo("Started", "Installation started in the Activity Center.")
