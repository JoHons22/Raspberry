import json
import sys
import threading
import subprocess
import logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# Set up logging to track test bench failures
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class PiTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Raspberry Pi 4B Modular Tester")
        self.root.geometry("1100x720")

        self.base_dir = Path(__file__).resolve().parent
        self.config_path = self.base_dir / "tests.json"

        self.tests = self.load_tests()
        self.test_vars = {}
        self.results = {}  # Changed to dict mapping test_name -> result for stable lookups

        self.build_gui()
        self.setup_styles()

    def load_tests(self):
        if not self.config_path.exists():
            messagebox.showerror(
                "Missing Config",
                f"Could not find tests.json at:\n{self.config_path}"
            )
            return []
        try:
            with open(self.config_path, "r") as file:
                all_tests = json.load(file)
            return [test for test in all_tests if test.get("enabled", True)]
        except Exception as e:
            messagebox.showerror("Config Error", f"Failed to parse JSON: {str(e)}")
            return []

    def setup_styles(self):
        """Configure color tags for Pass/Fail/Running visual cues"""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure Treeview Row Background Colors based on Status Tags
        self.results_table.tag_configure("PASS", background="#d4edda", foreground="#155724")
        self.results_table.tag_configure("FAIL", background="#f8d7da", foreground="#721c24")
        self.results_table.tag_configure("WARN", background="#fff3cd", foreground="#856404")
        self.results_table.tag_configure("ERROR", background="#f8d7da", foreground="#721c24")
        self.results_table.tag_configure("RUNNING", background="#e2e3e5", foreground="#383d41")

    def build_gui(self):
        title = ttk.Label(
            self.root,
            text="Raspberry Pi 4B All-In-One Tester",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=10)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ttk.LabelFrame(main_frame, text="Available Tests")
        left_frame.pack(side="left", fill="y", padx=5, pady=5)

        for test in self.tests:
            var = tk.BooleanVar(value=False)
            checkbox = ttk.Checkbutton(
                left_frame,
                text=test["name"],
                variable=var,
                command=self.update_instructions
            )
            checkbox.pack(anchor="w", padx=8, pady=4)
            self.test_vars[test["name"]] = var

        ttk.Button(left_frame, text="Select All", command=self.select_all).pack(fill="x", padx=8, pady=4)
        ttk.Button(left_frame, text="Clear Selection", command=self.clear_selection).pack(fill="x", padx=8, pady=4)
        
        self.run_btn = ttk.Button(left_frame, text="Run Selected", command=self.run_selected_tests)
        self.run_btn.pack(fill="x", padx=8, pady=12)
        
        ttk.Button(left_frame, text="Save Results", command=self.save_results).pack(fill="x", padx=8, pady=4)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        instructions_frame = ttk.LabelFrame(right_frame, text="Instructions")
        instructions_frame.pack(fill="x", padx=5, pady=5)

        self.instructions_box = tk.Text(instructions_frame, height=7, wrap="word")
        self.instructions_box.pack(fill="x", padx=5, pady=5)
        self.instructions_box.insert("end", "Select a test to view setup instructions.")

        results_frame = ttk.LabelFrame(right_frame, text="Results")
        results_frame.pack(fill="both", expand=True, padx=5, pady=5)

        table_frame = ttk.Frame(results_frame)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("Test", "Status", "Details")
        self.results_table = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)

        self.results_table.heading("Test", text="Test")
        self.results_table.heading("Status", text="Status")
        self.results_table.heading("Details", text="Details")

        self.results_table.column("Test", width=200, minwidth=150, stretch=False)
        self.results_table.column("Status", width=90, minwidth=80, stretch=False)
        self.results_table.column("Details", width=500, minwidth=300, stretch=True)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.results_table.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.results_table.xview)

        self.results_table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.results_table.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.results_table.bind("<<TreeviewSelect>>", self.update_full_details_from_selection)

        details_frame = ttk.LabelFrame(right_frame, text="Full Details")
        details_frame.pack(fill="both", expand=True, padx=5, pady=5)

        details_text_frame = ttk.Frame(details_frame)
        details_text_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.full_details_box = tk.Text(details_text_frame, height=8, wrap="word")
        details_scroll = ttk.Scrollbar(details_text_frame, orient="vertical", command=self.full_details_box.yview)
        self.full_details_box.configure(yscrollcommand=details_scroll.set)

        self.full_details_box.grid(row=0, column=0, sticky="nsew")
        details_scroll.grid(row=0, column=1, sticky="ns")

        details_text_frame.rowconfigure(0, weight=1)
        details_text_frame.columnconfigure(0, weight=1)

        details_button_frame = ttk.Frame(details_frame)
        details_button_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(details_button_frame, text="Show Selected Details", command=self.show_selected_details_popup).pack(side="left", padx=5)
        ttk.Button(details_button_frame, text="Copy Selected Details", command=self.copy_selected_details).pack(side="left", padx=5)

        self.status_label = ttk.Label(self.root, text="Ready")
        self.status_label.pack(pady=5)

    def update_instructions(self):
        self.instructions_box.delete("1.0", "end")
        selected_tests = self.get_selected_tests()

        if not selected_tests:
            self.instructions_box.insert("end", "Select a test to view setup instructions.")
            return

        for test in selected_tests:
            self.instructions_box.insert("end", f"{test['name']}:\n", "bold")
            self.instructions_box.insert("end", f"{test.get('instructions', 'No instructions provided.')}\n\n")

    def get_selected_tests(self):
        return [test for test in self.tests if self.test_vars[test["name"]].get()]

    def select_all(self):
        for var in self.test_vars.values():
            var.set(True)
        self.update_instructions()

    def clear_selection(self):
        for var in self.test_vars.values():
            var.set(False)
        self.update_instructions()

    def run_selected_tests(self):
        selected_tests = self.get_selected_tests()
        if not selected_tests:
            messagebox.showwarning("No Tests Selected", "Please select at least one test.")
            return

        self.results.clear()
        self.results_table.delete(*self.results_table.get_children())
        self.set_full_details_text("")
        self.run_btn.config(state="disabled")

        # Pre-populate table with elements using stable IIDs matching the test name
        for test in selected_tests:
            self.results_table.insert(
                "", "end", iid=test["name"], 
                values=(test["name"], "PENDING", "Waiting to start..."),
                tags=("RUNNING",)
            )

        test_thread = threading.Thread(
            target=self.run_tests_thread,
            args=(selected_tests,),
            daemon=True
        )
        test_thread.start()

    def run_tests_thread(self, selected_tests):
        self.set_status("Running selected tests...")

        for test in selected_tests:
            test_name = test["name"]
            
            self.update_row_safe(test_name, "RUNNING", "Test execution active...", "RUNNING")
            logging.info(f"Starting hardware test: {test_name}")

            result = self.run_test_file(test)

            if self.should_ask_for_observation(test, result):
                self.set_status(f"Waiting for manual confirmation: {test_name}")
                result = self.ask_for_manual_confirmation(test, result)

            self.results[test_name] = result
            
            # Instantly update specific row without recreating the whole table layout
            status = result.get("status", "ERROR")
            self.update_row_safe(test_name, test_name, status, result.get("details", ""), status)
            logging.info(f"Finished test {test_name} with status: {status}")

        self.set_status("Testing complete")
        self.root.after(0, lambda: self.run_btn.config(state="normal"))

    def run_test_file(self, test):
        test_name = test["name"]
        test_file = self.base_dir / test["file"]
        timeout = test.get("timeout", 30)

        if not test_file.exists():
            return {"name": test_name, "status": "ERROR", "details": f"Test file not found at: {test_file}"}

        try:
            completed = subprocess.run(
                [sys.executable, str(test_file)],
                text=True, capture_output=True, timeout=timeout
            )
            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()

            if not stdout:
                return {"name": test_name, "status": "ERROR", "details": stderr or "No standard output returned from test executable."}

            last_line = stdout.splitlines()[-1]
            try:
                result = json.loads(last_line)
            except json.JSONDecodeError:
                return {
                    "name": test_name, "status": "ERROR",
                    "details": f"Failed to parse JSON. Last line returned: {last_line}\nFull Standard Out:\n{stdout}"
                }

            result.setdefault("name", test_name)
            result.setdefault("status", "ERROR")
            result.setdefault("details", "No details provided")
            return result

        except subprocess.TimeoutExpired:
            return {"name": test_name, "status": "ERROR", "details": f"Test dropped execution: timed out after {timeout}s"}
        except Exception as e:
            return {"name": test_name, "status": "ERROR", "details": f"Exception encountered: {str(e)}"}

    def should_ask_for_observation(self, test, result):
        return test.get("requires_observation", False) and result.get("status", "ERROR") in ["PASS", "WARN"]

    def ask_for_manual_confirmation(self, test, result):
        response_event = threading.Event()
        response_holder = {}

        def show_popup():
            test_name = result.get("name", test.get("name", "Unknown Test"))
            details = result.get("details", "No details provided.")
            prompt = test.get("observation_prompt", f"Did the observed output for {test_name} pass?")

            message = f"{prompt}\n\nInternal Log Details:\n{details}\n\nSelect 'Yes' if physical hardware reacted properly."
            response_holder["passed"] = messagebox.askyesno("Manual Test Confirmation", message)
            response_event.set()

        self.root.after(0, show_popup)
        response_event.wait()

        updated_result = dict(result)
        if response_holder.get("passed", False):
            updated_result["status"] = "PASS"
            updated_result["details"] += " (User Confirmed Physical PASS)"
        else:
            updated_result["status"] = "FAIL"
            updated_result["details"] += " (User Reported Physical FAILURE)"
        return updated_result

    def update_row_safe(self, iid, name, status, details, tag="RUNNING"):
        """Safely target and edit a single specific row inside the active thread context"""
        self.root.after(
            0, lambda: self.results_table.item(iid, values=(name, status, details), tags=(tag,))
        )

    def update_full_details_from_selection(self, event=None):
        selected = self.results_table.selection()
        if not selected:
            return
        
        test_name = selected[0]
        if test_name in self.results:
            self.display_result_details(self.results[test_name])
        else:
            # Handle elements still pending or active in execution queue
            values = self.results_table.item(test_name, "values")
            if len(values) >= 3:
                text = f"Test Name: {values[0]}\nCurrent Status: {values[1]}\n\nStatus Context:\n{values[2]}"
                self.set_full_details_text(text)

    def display_result_details(self, result):
        text = f"Test Name: {result.get('name')}\nFinal Status: {result.get('status')}\n\nDetailed Output Log:\n{result.get('details')}"
        self.set_full_details_text(text)

    def set_full_details_text(self, text):
        self.full_details_box.config(state="normal")
        self.full_details_box.delete("1.0", "end")
        self.full_details_box.insert("end", text)
        self.full_details_box.config(state="disabled")

    def get_selected_detail_text(self):
        selected = self.results_table.selection()
        if not selected:
            return ""
        test_name = selected[0]
        if test_name in self.results:
            r = self.results[test_name]
            return f"Test: {r.get('name')}\nStatus: {r.get('status')}\nDetails: {r.get('details')}"
        return self.full_details_box.get("1.0", "end").strip()

    def show_selected_details_popup(self):
        txt = self.get_selected_detail_text()
        if not txt:
            messagebox.showwarning("No Selection", "Please select a test result first.")
            return
        messagebox.showinfo("Full Test Details", txt)

    def copy_selected_details(self):
        txt = self.get_selected_detail_text()
        if not txt:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        self.root.update()
        messagebox.showinfo("Copied", "Test detailed logs successfully copied to clipboard.")

    def set_status(self, text):
        self.root.after(0, lambda: self.status_label.config(text=text))

    def save_results(self):
        if not self.results:
            messagebox.showwarning("No Results", "No test data exists to save.")
            return

        output_file = self.base_dir / "pi_test_results.txt"
        try:
            with open(output_file, "w") as file:
                file.write("Raspberry Pi 4B Microcontroller Test Bench Report\n")
                file.write("=" * 55 + "\n\n")
                for name, res in self.results.items():
                    file.write(f"Hardware Feature : {name}\n")
                    file.write(f"Execution Status : {res.get('status')}\n")
                    file.write(f"Log Details      : {res.get('details')}\n")
                    file.write("-" * 55 + "\n")
            messagebox.showinfo("Saved Successfully", f"Log summary exported to:\n{output_file}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save log: {str(e)}")

def main():
    root = tk.Tk()
    app = PiTesterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
