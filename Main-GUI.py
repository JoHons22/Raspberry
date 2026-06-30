import json
import sys
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


class PiTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Raspberry Pi 4B Modular Tester")
        self.root.geometry("950x600")

        self.base_dir = Path(__file__).resolve().parent
        self.config_path = self.base_dir / "tests.json"

        self.tests = self.load_tests()
        self.test_vars = {}
        self.results = []

        self.build_gui()

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

            enabled_tests = [
                test for test in all_tests
                if test.get("enabled", True)
            ]

            return enabled_tests

        except Exception as e:
            messagebox.showerror("Config Error", str(e))
            return []

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

        ttk.Button(
            left_frame,
            text="Select All",
            command=self.select_all
        ).pack(fill="x", padx=8, pady=4)

        ttk.Button(
            left_frame,
            text="Clear Selection",
            command=self.clear_selection
        ).pack(fill="x", padx=8, pady=4)

        ttk.Button(
            left_frame,
            text="Run Selected",
            command=self.run_selected_tests
        ).pack(fill="x", padx=8, pady=12)

        ttk.Button(
            left_frame,
            text="Save Results",
            command=self.save_results
        ).pack(fill="x", padx=8, pady=4)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        instructions_frame = ttk.LabelFrame(right_frame, text="Instructions")
        instructions_frame.pack(fill="x", padx=5, pady=5)

        self.instructions_box = tk.Text(
            instructions_frame,
            height=8,
            wrap="word"
        )
        self.instructions_box.pack(fill="x", padx=5, pady=5)
        self.instructions_box.insert("end", "Select a test to view setup instructions.")

        results_frame = ttk.LabelFrame(right_frame, text="Results")
        results_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("Test", "Status", "Details")
        self.results_table = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings"
        )

        self.results_table.heading("Test", text="Test")
        self.results_table.heading("Status", text="Status")
        self.results_table.heading("Details", text="Details")

        self.results_table.column("Test", width=220)
        self.results_table.column("Status", width=90)
        self.results_table.column("Details", width=550)

        self.results_table.pack(fill="both", expand=True, padx=5, pady=5)

        self.status_label = ttk.Label(self.root, text="Ready")
        self.status_label.pack(pady=5)

    def update_instructions(self):
        self.instructions_box.delete("1.0", "end")

        selected_tests = self.get_selected_tests()

        if not selected_tests:
            self.instructions_box.insert(
                "end",
                "Select a test to view setup instructions."
            )
            return

        for test in selected_tests:
            self.instructions_box.insert("end", f"{test['name']}:\n")
            self.instructions_box.insert(
                "end",
                f"{test.get('instructions', 'No instructions provided.')}\n"
            )

            if test.get("requires_observation", False):
                self.instructions_box.insert(
                    "end",
                    "Manual confirmation required after this test runs.\n"
                )

            self.instructions_box.insert("end", "\n")

    def get_selected_tests(self):
        selected = []

        for test in self.tests:
            test_name = test["name"]

            if self.test_vars[test_name].get():
                selected.append(test)

        return selected

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
            messagebox.showwarning(
                "No Tests Selected",
                "Please select at least one test."
            )
            return

        self.results = []
        self.results_table.delete(*self.results_table.get_children())

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

            self.add_result_row_safe(
                test_name,
                "RUNNING",
                "Test in progress..."
            )

            result = self.run_test_file(test)

            if self.should_ask_for_observation(test, result):
                self.set_status(f"Waiting for manual confirmation: {test_name}")
                result = self.ask_for_manual_confirmation(test, result)

            self.results.append(result)
            self.refresh_results_table_safe()

        self.set_status("Testing complete")

    def run_test_file(self, test):
        test_name = test["name"]
        test_file = self.base_dir / test["file"]
        timeout = test.get("timeout", 30)

        if not test_file.exists():
            return {
                "name": test_name,
                "status": "ERROR",
                "details": f"Test file not found: {test_file}"
            }

        try:
            completed = subprocess.run(
                [sys.executable, str(test_file)],
                text=True,
                capture_output=True,
                timeout=timeout
            )

            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()

            if not stdout:
                return {
                    "name": test_name,
                    "status": "ERROR",
                    "details": stderr or "No output returned from test file"
                }

            # Test files can print debug text, but the final line must be JSON.
            last_line = stdout.splitlines()[-1]

            try:
                result = json.loads(last_line)
            except json.JSONDecodeError:
                return {
                    "name": test_name,
                    "status": "ERROR",
                    "details": f"Invalid JSON output from test. Last line was: {last_line}"
                }

            result.setdefault("name", test_name)
            result.setdefault("status", "ERROR")
            result.setdefault("details", "No details provided")

            return result

        except subprocess.TimeoutExpired:
            return {
                "name": test_name,
                "status": "ERROR",
                "details": f"Test timed out after {timeout} seconds"
            }

        except Exception as e:
            return {
                "name": test_name,
                "status": "ERROR",
                "details": str(e)
            }

    def should_ask_for_observation(self, test, result):
        """
        Only ask for manual observation if the test config requires it
        and the software part of the test did not already fail/error.
        """
        if not test.get("requires_observation", False):
            return False

        status = result.get("status", "ERROR")

        return status in ["PASS", "WARN"]

    def ask_for_manual_confirmation(self, test, result):
        """
        Opens a pop-up asking the user if the observed test output passed.
        This is used for tests like LEDs and audio where software can run the test,
        but a person must confirm the physical result.
        """

        response_event = threading.Event()
        response_holder = {}

        def show_popup():
            test_name = result.get("name", test.get("name", "Unknown Test"))
            details = result.get("details", "No details provided.")

            prompt = test.get(
                "observation_prompt",
                f"Did the observed output for {test_name} pass?"
            )

            message = (
                f"{prompt}\n\n"
                f"Test details:\n{details}\n\n"
                "Click Yes if the physical output worked correctly.\n"
                "Click No if the physical output did not work correctly."
            )

            response_holder["passed"] = messagebox.askyesno(
                "Manual Test Confirmation",
                message
            )

            response_event.set()

        self.root.after(0, show_popup)
        response_event.wait()

        user_confirmed_pass = response_holder.get("passed", False)

        updated_result = dict(result)
        original_details = updated_result.get("details", "")

        if user_confirmed_pass:
            updated_result["status"] = "PASS"
            updated_result["details"] = (
                f"{original_details} Manual observation: PASS."
            )
        else:
            updated_result["status"] = "FAIL"
            updated_result["details"] = (
                f"{original_details} Manual observation: FAIL."
            )

        return updated_result

    def add_result_row_safe(self, name, status, details):
        self.root.after(
            0,
            lambda: self.results_table.insert(
                "",
                "end",
                values=(name, status, details)
            )
        )

    def refresh_results_table_safe(self):
        self.root.after(0, self.refresh_results_table)

    def refresh_results_table(self):
        self.results_table.delete(*self.results_table.get_children())

        for result in self.results:
            self.results_table.insert(
                "",
                "end",
                values=(
                    result.get("name", "Unknown Test"),
                    result.get("status", "ERROR"),
                    result.get("details", "No details")
                )
            )

    def set_status(self, text):
        self.root.after(
            0,
            lambda: self.status_label.config(text=text)
        )

    def save_results(self):
        if not self.results:
            messagebox.showwarning(
                "No Results",
                "No test results to save."
            )
            return

        output_file = self.base_dir / "pi_test_results.txt"

        with open(output_file, "w") as file:
            file.write("Raspberry Pi 4B Test Results\n")
            file.write("=" * 40 + "\n\n")

            for result in self.results:
                file.write(f"Test: {result.get('name', 'Unknown')}\n")
                file.write(f"Status: {result.get('status', 'ERROR')}\n")
                file.write(f"Details: {result.get('details', '')}\n")
                file.write("-" * 40 + "\n")

        messagebox.showinfo(
            "Results Saved",
            f"Results saved to:\n{output_file}"
        )


def main():
    root = tk.Tk()
    app = PiTesterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
