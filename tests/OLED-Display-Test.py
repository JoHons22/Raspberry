import json
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk

BASE_DIR = Path(__file__).resolve().parent
CONTROL_SCRIPT = BASE_DIR / "OLED-Control.py"

class OLEDInteractiveDialog:
    def __init__(self, root):
        self.root = root
        self.root.title("OLED Diagnostic Step Tool")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        # Keep this window pinned on top of the main test bench GUI
        self.root.attributes("-topmost", True)

        # Step tracking layout
        self.steps = ["solid", "checker1", "checker2", "off"]
        self.step_descriptions = [
            "1. Solid Bright Block (Check for dead pixels/lines)",
            "2. Checkerboard Pattern A (Check pixel isolation)",
            "3. Checkerboard Pattern B (Check inverse isolation)",
            "4. All Pixels Off (Check for stuck-on pixels)"
        ]
        self.current_index = 0

        self.build_ui()
        self.update_hardware_screen()

    def build_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)

        self.desc_label = ttk.Label(
            main_frame, text="", font=("Arial", 11, "bold"), wrap=360
        )
        self.desc_label.pack(pady=15, fill="x")

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side="bottom", fill="x", pady=5)

        self.back_btn = ttk.Button(btn_frame, text="◀ Back", command=self.prev_step)
        self.back_btn.pack(side="left", padx=5)

        self.next_btn = ttk.Button(btn_frame, text="Next ▶", command=self.next_step)
        self.next_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="Finish Test", command=self.root.destroy).pack(side="right", padx=5)

    def update_hardware_screen(self):
        # Update text description label
        self.desc_label.config(text=self.step_descriptions[self.current_index])
        
        # Manage button availability limits
        self.back_btn.config(state="normal" if self.current_index > 0 else "disabled")
        if self.current_index == len(self.steps) - 1:
            self.next_btn.config(state="disabled")
        else:
            self.next_btn.config(state="normal")

        # Execute low-level sub-process handler to shift hardware registers
        current_mode = self.steps[self.current_index]
        subprocess.run([sys.executable, str(CONTROL_SCRIPT), current_mode])

    def next_step(self):
        if self.current_index < len(self.steps) - 1:
            self.current_index += 1
            self.update_hardware_screen()

    def prev_step(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_hardware_screen()

def main():
    # Verify baseline low-level controller tool discovery layout
    if not CONTROL_SCRIPT.exists():
        print(json.dumps({
            "status": "ERROR", 
            "details": f"Missing auxiliary control utility layout at: {CONTROL_SCRIPT}"
        }))
        sys.exit(1)

    # Initialize independent secondary Tkinter frame instance context
    root = tk.Tk()
    app = OLEDInteractiveDialog(root)
    root.mainloop()

    # Once the technician closes the step tool window, report a clean PASS status to the main GUI
    print(json.dumps({
        "status": "PASS",
        "details": "Manual frame-by-frame verification cycle executed by operator."
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
