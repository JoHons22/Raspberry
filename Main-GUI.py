import json
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


BASE_DIR = Path(__file__).resolve().parent
TESTS_JSON = BASE_DIR / "tests.json"


class PiTestBenchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Raspberry Pi Test Bench")
        self.root.geometry("1000x720")
        self.root.minsize(900, 620)

        self.tests = []
        self.selected_vars = {}
        self.result_details = {}
        self.stop_requested = False
        self.running = False

        self.load_tests()
        self.build_ui()

    def load_tests(self):
        if not TESTS_JSON.exists():
            messagebox.showerror(
                "Missing tests.json",
                f"Could not find tests.json at:\n{TESTS_JSON}"
            )
            self.tests = []
            return

        try:
            with open(TESTS_JSON, "r", encoding="utf-8") as file:
                self.tests = json.load(file)

            for test in self.tests:
                if "category" not in test:
                    test["category"] = self.infer_category(test)

        except Exception as e:
            messagebox.showerror(
                "tests.json Error",
                f"Could not load tests.json:\n{e}"
            )
            self.tests = []

    def infer_category(self, test):
        name = test.get("name", "").lower()

        if "audio" in name or "camera" in name or "csi" in name:
            return "Audio / Visual Tests"

        return "GPIO / Communication Tests"

    def build_ui(self):
        self.create_styles()

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(
            main_frame,
            text="Raspberry Pi Test Bench",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=(0, 8))

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="both", expand=True)

        self.create_test_selection_panel(top_frame)
        self.create_results_panel(top_frame)

        self.create_control_panel(main_frame)
        self.create_progress_panel(main_frame)
        self.create_details_panel(main_frame)

    def create_styles(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Treeview", rowheight=24)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

    def create_test_selection_panel(self, parent):
        selection_frame = ttk.LabelFrame(parent, text="Available Tests", padding=10)
        selection_frame.pack(side="left", fill="both", expand=False, padx=(0, 8))

        canvas = tk.Canvas(selection_frame, width=300, highlightthickness=0)
        scrollbar = ttk.Scrollbar(selection_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        categories = {}

        for test in self.tests:
            if not test.get("enabled", True):
                continue

            category = test.get("category", "Other Tests")
            categories.setdefault(category, []).append(test)

        for category, tests in categories.items():
            category_frame = ttk.LabelFrame(scrollable_frame, text=category, padding=8)
            category_frame.pack(fill="x", expand=True, padx=4, pady=6)

            for test in tests:
                var = tk.BooleanVar(value=False)
                self.selected_vars[test["name"]] = var

                checkbox = ttk.Checkbutton(
                    category_frame,
                    text=test["name"],
                    variable=var
                )
                checkbox.pack(anchor="w", pady=2)

    def create_results_panel(self, parent):
        results_frame = ttk.LabelFrame(parent, text="Results", padding=10)
        results_frame.pack(side="right", fill="both", expand=True)

        table_frame = ttk.Frame(results_frame)
        table_frame.pack(fill="both", expand=True)

        self.results_tree = ttk.Treeview(
            table_frame,
            columns=("test", "category", "status", "time"),
            show="headings",
            height=12
        )

        self.results_tree.heading("test", text="Test")
        self.results_tree.heading("category", text="Category")
        self.results_tree.heading("status", text="Status")
        self.results_tree.heading("time", text="Time")

        self.results_tree.column("test", width=240, anchor="w")
        self.results_tree.column("category", width=210, anchor="w")
        self.results_tree.column("status", width=90, anchor="center")
        self.results_tree.column("time", width=120, anchor="center")

        y_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.results_tree.yview
        )

        x_scrollbar = ttk.Scrollbar(
            results_frame,
            orient="horizontal",
            command=self.results_tree.xview
        )

        self.results_tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )

        self.results_tree.pack(side="left", fill="both", expand=True)
        y_scrollbar.pack(side="right", fill="y")
        x_scrollbar.pack(fill="x")

        self.results_tree.tag_configure("PASS", background="#d8f5d0")
        self.results_tree.tag_configure("FAIL", background="#f8d0d0")
        self.results_tree.tag_configure("ERROR", background="#f8d0d0")
        self.results_tree.tag_configure("WARN", background="#fff0b8")
        self.results_tree.tag_configure("SKIP", background="#e0e0e0")
        self.results_tree.tag_configure("STOPPED", background="#e0e0e0")
        self.results_tree.tag_configure("RUNNING", background="#d0e8ff")

        self.results_tree.bind("<<TreeviewSelect>>", self.show_selected_details)

    def create_control_panel(self, parent):
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill="x", pady=8)

        ttk.Button(
            control_frame,
            text="Select All",
            command=self.select_all_tests
        ).pack(side="left", padx=4)

        ttk.Button(
            control_frame,
            text="Clear Selection",
            command=self.clear_selection
        ).pack(side="left", padx=4)

        ttk.Button(
            control_frame,
            text="Run Selected",
            command=self.run_selected_tests
        ).pack(side="left", padx=4)

        ttk.Button(
            control_frame,
            text="Run All Automatic Tests",
            command=self.run_all_automatic_tests
        ).pack(side="left", padx=4)

        ttk.Button(
            control_frame,
            text="Stop After Current Test",
            command=self.stop_after_current
        ).pack(side="left", padx=4)

        ttk.Button(
            control_frame,
            text="Save Results",
            command=self.save_results
        ).pack(side="right", padx=4)

        ttk.Button(
            control_frame,
            text="Clear Results",
            command=self.clear_results
        ).pack(side="right", padx=4)

    def create_progress_panel(self, parent):
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill="x", pady=(0, 8))

        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack(anchor="w")

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", pady=4)

    def create_details_panel(self, parent):
        details_frame = ttk.LabelFrame(parent, text="Full Details", padding=8)
        details_frame.pack(fill="both", expand=False)

        text_frame = ttk.Frame(details_frame)
        text_frame.pack(fill="both", expand=True)

        self.details_text = tk.Text(
            text_frame,
            height=9,
            wrap="word",
            state="disabled"
        )

        details_scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.details_text.yview
        )

        self.details_text.configure(yscrollcommand=details_scrollbar.set)

        self.details_text.pack(side="left", fill="both", expand=True)
        details_scrollbar.pack(side="right", fill="y")

        details_button_frame = ttk.Frame(details_frame)
        details_button_frame.pack(fill="x", pady=(6, 0))

        ttk.Button(
            details_button_frame,
            text="Show Selected Details",
            command=self.show_selected_details
        ).pack(side="left", padx=4)

        ttk.Button(
            details_button_frame,
            text="Copy Details",
            command=self.copy_selected_details
        ).pack(side="left", padx=4)

    def select_all_tests(self):
        for var in self.selected_vars.values():
            var.set(True)

    def clear_selection(self):
        for var in self.selected_vars.values():
            var.set(False)

    def clear_results(self):
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        self.result_details.clear()
        self.set_details_text("")
        self.progress_label.config(text="Ready")
        self.progress_bar["value"] = 0

    def get_selected_tests(self):
        selected_tests = []

        for test in self.tests:
            if not test.get("enabled", True):
                continue

            test_name = test.get("name")

            if test_name in self.selected_vars and self.selected_vars[test_name].get():
                selected_tests.append(test)

        return selected_tests

    def get_automatic_tests(self):
        automatic_tests = []

        for test in self.tests:
            if not test.get("enabled", True):
                continue

            requires_observation = test.get("requires_observation", False)
            has_internal_prompts = test.get("skip_gui_setup_prompt", False)

            if not requires_observation and not has_internal_prompts:
                automatic_tests.append(test)

        return automatic_tests

    def run_selected_tests(self):
        selected_tests = self.get_selected_tests()

        if not selected_tests:
            messagebox.showwarning(
                "No Tests Selected",
                "Please select at least one test to run."
            )
            return

        self.start_test_thread(selected_tests)

    def run_all_automatic_tests(self):
        automatic_tests = self.get_automatic_tests()

        if not automatic_tests:
            messagebox.showwarning(
                "No Automatic Tests",
                "No automatic tests are available."
            )
            return

        self.start_test_thread(automatic_tests)

    def start_test_thread(self, tests_to_run):
        if self.running:
            messagebox.showwarning(
                "Tests Already Running",
                "A test sequence is already running."
            )
            return

        self.running = True
        self.stop_requested = False

        thread = threading.Thread(
            target=self.run_test_sequence,
            args=(tests_to_run,),
            daemon=True
        )
        thread.start()

    def stop_after_current(self):
        if self.running:
            self.stop_requested = True
            self.progress_label.config(text="Stop requested. Current test will finish first.")
        else:
            self.progress_label.config(text="No test is currently running.")

    def run_test_sequence(self, tests_to_run):
        total_tests = len(tests_to_run)

        self.root.after(0, lambda: self.setup_progress(total_tests))

        for index, test in enumerate(tests_to_run, start=1):
            if self.stop_requested:
                break

            test_name = test.get("name", "Unnamed Test")
            category = test.get("category", "Other Tests")

            self.root.after(
                0,
                lambda i=index, total=total_tests, name=test_name:
                self.progress_label.config(text=f"Running {i}/{total}: {name}")
            )

            self.root.after(
                0,
                lambda i=index - 1: self.update_progress(i)
            )

            if not test.get("skip_gui_setup_prompt", False):
                setup_ok = self.confirm_setup_checklist(test)

                if not setup_ok:
                    result = {
                        "name": test_name,
                        "status": "SKIP",
                        "details": "User skipped setup confirmation."
                    }

                    self.root.after(
                        0,
                        lambda r=result, c=category: self.add_result_to_table(r, c)
                    )
                    continue

            running_result = {
                "name": test_name,
                "status": "RUNNING",
                "details": "Test is currently running."
            }

            self.root.after(
                0,
                lambda r=running_result, c=category: self.add_result_to_table(r, c)
            )

            result = self.run_test_file(test)

            if test.get("requires_observation", False):
                result = self.handle_observation_prompt(test, result)

            self.root.after(
                0,
                lambda r=result, c=category: self.replace_last_running_result(r, c)
            )

        self.root.after(0, lambda: self.finish_test_sequence(total_tests))

    def setup_progress(self, total_tests):
        self.progress_bar["maximum"] = total_tests
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Starting tests...")

    def update_progress(self, value):
        self.progress_bar["value"] = value

    def finish_test_sequence(self, total_tests):
        self.running = False
        self.progress_bar["value"] = total_tests

        if self.stop_requested:
            self.progress_label.config(text="Stopped after current test.")
        else:
            self.progress_label.config(text="Test sequence complete.")

    def confirm_setup_checklist(self, test):
        switch_steps = test.get("switch_steps", [])

        if not switch_steps:
            old_checklist = test.get("switch_checklist", [])

            if old_checklist:
                switch_steps = [
                    "\n".join([f"• {item}" for item in old_checklist])
                ]

        if not switch_steps:
            return True

        for step_number, step_text in enumerate(switch_steps, start=1):
            response_holder = {"value": False}
            event = threading.Event()

            def ask_user():
                response_holder["value"] = messagebox.askyesno(
                    "Switch Setup Required",
                    (
                        f"{test.get('name', 'Test Setup')}\n\n"
                        f"Step {step_number} of {len(switch_steps)}:\n\n"
                        f"{step_text}\n\n"
                        "Click Yes when ready to continue.\n"
                        "Click No to skip this test."
                    )
                )
                event.set()

            self.root.after(0, ask_user)
            event.wait()

            if not response_holder["value"]:
                return False

        return True

    def handle_observation_prompt(self, test, result):
        status = result.get("status", "ERROR")

        if status in ["ERROR", "FAIL"]:
            return result

        prompt = test.get(
            "observation_prompt",
            "Did the test behave correctly?"
        )

        response_holder = {"value": False}
        event = threading.Event()

        def ask_user():
            response_holder["value"] = messagebox.askyesno(
                "Manual Observation Required",
                (
                    f"{test.get('name', 'Manual Test')}\n\n"
                    f"{prompt}\n\n"
                    "Click Yes for PASS.\n"
                    "Click No for FAIL."
                )
            )
            event.set()

        self.root.after(0, ask_user)
        event.wait()

        details = result.get("details", "")

        if response_holder["value"]:
            result["status"] = "PASS"
            result["details"] = details + " Manual observation confirmed PASS."
        else:
            result["status"] = "FAIL"
            result["details"] = details + " Manual observation confirmed FAIL."

        return result

    def run_test_file(self, test):
        test_name = test.get("name", "Unnamed Test")
        test_file = BASE_DIR / test.get("file", "")
        timeout = test.get("timeout", 30)
        test_args = test.get("args", [])

        if not test_file.exists():
            return {
                "name": test_name,
                "status": "ERROR",
                "details": f"Test file not found: {test_file}"
            }

        command = [sys.executable, str(test_file)] + test_args

        try:
            completed = subprocess.run(
                command,
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
                    "details": (
                        "Test did not return JSON output. "
                        f"STDERR: {stderr}"
                    )
                }

            last_line = stdout.splitlines()[-1]

            try:
                result = json.loads(last_line)
            except json.JSONDecodeError:
                return {
                    "name": test_name,
                    "status": "ERROR",
                    "details": (
                        "Could not parse final output line as JSON. "
                        f"Final line: {last_line} "
                        f"Full stdout: {stdout} "
                        f"STDERR: {stderr}"
                    )
                }

            if "name" not in result:
                result["name"] = test_name

            if "status" not in result:
                result["status"] = "ERROR"

            if "details" not in result:
                result["details"] = ""

            if completed.returncode != 0 and result["status"] == "PASS":
                result["status"] = "WARN"
                result["details"] += f" Test returned nonzero exit code: {completed.returncode}."

            if stderr:
                result["details"] += f" STDERR: {stderr}"

            return result

        except subprocess.TimeoutExpired:
            return {
                "name": test_name,
                "status": "ERROR",
                "details": f"Test timed out after {timeout} seconds."
            }

        except Exception as e:
            return {
                "name": test_name,
                "status": "ERROR",
                "details": str(e)
            }

    def add_result_to_table(self, result, category):
        result_name = result.get("name", "Unnamed Test")
        result_status = result.get("status", "ERROR")
        result_details = result.get("details", "")
        timestamp = datetime.now().strftime("%H:%M:%S")

        row_id = self.results_tree.insert(
            "",
            "end",
            values=(
                result_name,
                category,
                result_status,
                timestamp
            ),
            tags=(result_status,)
        )

        self.result_details[row_id] = result_details

        self.results_tree.selection_set(row_id)
        self.results_tree.see(row_id)
        self.show_selected_details()

    def replace_last_running_result(self, result, category):
        children = self.results_tree.get_children()

        if children:
            last_item = children[-1]
            values = self.results_tree.item(last_item, "values")

            if values and len(values) >= 3 and values[2] == "RUNNING":
                self.results_tree.delete(last_item)

                if last_item in self.result_details:
                    del self.result_details[last_item]

        self.add_result_to_table(result, category)

    def show_selected_details(self, event=None):
        selected_items = self.results_tree.selection()

        if not selected_items:
            return

        selected_item = selected_items[0]
        values = self.results_tree.item(selected_item, "values")

        if not values:
            return

        test_name = values[0]
        category = values[1]
        status = values[2]
        timestamp = values[3]

        details = self.result_details.get(selected_item, "No details available.")

        details_output = (
            f"Test: {test_name}\n"
            f"Category: {category}\n"
            f"Status: {status}\n"
            f"Time: {timestamp}\n\n"
            f"Details:\n{details}"
        )

        self.set_details_text(details_output)

    def set_details_text(self, text):
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("end", text)
        self.details_text.config(state="disabled")

    def copy_selected_details(self):
        selected_items = self.results_tree.selection()

        if not selected_items:
            messagebox.showwarning(
                "No Result Selected",
                "Select a result row first."
            )
            return

        selected_item = selected_items[0]
        values = self.results_tree.item(selected_item, "values")

        if not values:
            return

        test_name = values[0]
        category = values[1]
        status = values[2]
        timestamp = values[3]
        details = self.result_details.get(selected_item, "")

        copy_text = (
            f"Test: {test_name}\n"
            f"Category: {category}\n"
            f"Status: {status}\n"
            f"Time: {timestamp}\n\n"
            f"Details:\n{details}"
        )

        self.root.clipboard_clear()
        self.root.clipboard_append(copy_text)
        self.root.update()

    def save_results(self):
        children = self.results_tree.get_children()

        if not children:
            messagebox.showwarning(
                "No Results",
                "There are no results to save."
            )
            return

        default_name = datetime.now().strftime("pi_test_results_%Y-%m-%d_%H%M%S.txt")

        save_path = filedialog.asksaveasfilename(
            title="Save Test Results",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[
                ("Text Files", "*.txt"),
                ("All Files", "*.*")
            ]
        )

        if not save_path:
            return

        try:
            with open(save_path, "w", encoding="utf-8") as file:
                file.write("Raspberry Pi Test Bench Results\n")
                file.write("=" * 40 + "\n")
                file.write(f"Saved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                for item in children:
                    values = self.results_tree.item(item, "values")

                    if not values:
                        continue

                    test_name = values[0]
                    category = values[1]
                    status = values[2]
                    timestamp = values[3]
                    details = self.result_details.get(item, "")

                    file.write(f"Test: {test_name}\n")
                    file.write(f"Category: {category}\n")
                    file.write(f"Status: {status}\n")
                    file.write(f"Time: {timestamp}\n")
                    file.write("Details:\n")
                    file.write(details)
                    file.write("\n")
                    file.write("-" * 40 + "\n\n")

            messagebox.showinfo(
                "Results Saved",
                f"Results saved to:\n{save_path}"
            )

        except Exception as e:
            messagebox.showerror(
                "Save Error",
                f"Could not save results:\n{e}"
            )


def main():
    root = tk.Tk()
    app = PiTestBenchGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
