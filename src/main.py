import sys
import os
import traceback
from tkinter import messagebox

# Add project root to path (one level up from this file)
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from src.utils.logger import log
from src.config.manager import config_manager

def main():
    try:
        log.info("Starting AI Universal Suite...")
        
        # Migrate legacy keys if any (One-time check)
        config_manager.migrate_legacy_keys()
        
        # Import UI (Lazy load to allow splash if needed later)
        from src.ui.app import App
        
        app = App()
        app.mainloop()
        
        log.info("Application exited normally.")
        
    except Exception as e:
        log.critical(f"Unhandled exception: {e}")
        traceback.print_exc()
        try:
            messagebox.showerror("Critical Error", f"An error occurred:\n{e}\n\nCheck logs for details.")
        except:
            print("Could not show error message box.")

if __name__ == "__main__":
    main()

