import json
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

BASE_DIR = Path(__file__).resolve().parent
CONTROL_SCRIPT = BASE_DIR / "OLED-Control.py"

TEST_NAME = "I2C OLED Test"


class OLEDInteractiveDialog:
    def __init__(self, root):
        self.root = root
        self.root.title("OLED Diagnostic Step Tool")
        self.root.geometry("460x240")
        self.root.resizable(False, False)

        # Keep this window pinned on top of the main test bench GUI
        self.root.attributes("-topmost", True)

        self.steps = ["solid", "checker1", "checker2", "off"]

        self.step_descriptions = [
            "1. Solid Bright Block\nCheck for dead pixels or missing lines.",
            "2. Checkerboard Pattern A\nCheck pixel isolation.",
            "3. Checkerboard Pattern B\nCheck inverse pixel isolation.",
            "4. All Pixels Off\nCheck for stuck-on pixels."
        ]

        self.current_index = 0
        self.error_message = ""
        self.user_result = "WARN"

        self.build_ui()
        self.update_hardware_screen()

    def build_ui(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)

        self.desc_label = ttk.Label(
            main_frame,
            text="",
            font=("Arial", 11, "bold"),
            wraplength=420,
            justify="center"
        )
        self.desc_label.pack(pady=10, fill="x")

        self.status_label = ttk.Label(
            main_frame,
            text="",
            wraplength=420,
            justify="center"
        )
        self.status_label.pack(pady=5, fill="x")

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side="bottom", fill="x", pady=8)

        self.back_btn = ttk.Button(
            btn_frame,
            text="◀ Back",
            command=self.prev_step
        )
        self.back_btn.pack(side="left", padx=5)

        self.next_btn = ttk.Button(
            btn_frame,
            text="Next ▶",
            command=self.next_step
        )
        self.next_btn.pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text="Fail",
            command=self.finish_fail
        ).pack(side="right", padx=5)

        ttk.Button(
            btn_frame,
            text="Pass",
            command=self.finish_pass
        ).pack(side="right", padx=5)

    def update_hardware_screen(self):
        self.desc_label.config(text=self.step_descriptions[self.current_index])

        self.back_btn.config(
            state="normal" if self.current_index > 0 else "disabled"
        )

        self.next_btn.config(
            state="normal" if self.current_index < len(self.steps) - 1 else "disabled"
        )

        current_mode = self.steps[self.current_index]

        completed = subprocess.run(
            [sys.executable, str(CONTROL_SCRIPT), current_mode],
            text=True,
            capture_output=True
        )

        if completed.returncode == 0:
            self.status_label.config(
                text=f"OLED command sent successfully: {current_mode}"
            )
        else:
            error_text = completed.stderr.strip() or completed.stdout.strip()
            self.error_message = error_text or "OLED control script failed."

            self.status_label.config(
                text=f"ERROR: {self.error_message}"
            )

            messagebox.showerror(
                "OLED Control Error",
                (
                    "The OLED control command failed.\n\n"
                    f"Step: {current_mode}\n"
                    f"Error: {self.error_message}"
                )
            )

    def next_step(self):
        if self.current_index < len(self.steps) - 1:
            self.current_index += 1
            self.update_hardware_screen()

    def prev_step(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_hardware_screen()

    def finish_pass(self):
        self.user_result = "PASS"
        self.root.destroy()

    def finish_fail(self):
        self.user_result = "FAIL"
        self.root.destroy()


def main():
    if not CONTROL_SCRIPT.exists():
        print(json.dumps({
            "name": TEST_NAME,
            "status": "ERROR",
            "details": f"Missing OLED control script at: {CONTROL_SCRIPT}"
        }))
        sys.exit(1)

    root = tk.Tk()
    app = OLEDInteractiveDialog(root)
    root.mainloop()

    if app.error_message:
        print(json.dumps({
            "name": TEST_NAME,
            "status": "ERROR",
            "details": f"OLED test had a control error: {app.error_message}"
        }))
        sys.exit(1)

    print(json.dumps({
        "name": TEST_NAME,
        "status": app.user_result,
        "details": (
            "OLED manual diagnostic cycle completed. "
            f"Operator selected {app.user_result}."
        )
    }))

    sys.exit(0)


if __name__ == "__main__":
    main()
