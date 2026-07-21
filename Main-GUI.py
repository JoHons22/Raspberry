import json
import sys
import threading
import subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox


class PiTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Raspberry Pi 4B Modular Tester")
        self.root.geometry("1100x750")

        self.base_dir = Path(__file__).resolve().parent
        self.config_path = self.base_dir / "tests.json"

        self.tests = self.load_tests()
        self.test_vars = {}
        self.results = []

        self.is_running = False
        self.stop_requested = False

        self.selection_controls = []
        self.run_controls = []

        self.total_tests_to_run = 0
        self.completed_tests = 0

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

    def infer_category(self, test):
        """
        Uses the category from tests.json if available.
        If no category is provided, it guesses a category from the test name.
        """

        if "category" in test:
            return test["category"]

        name = test.get("name", "").lower()

        if "uart" in name or "spi" in name:
            return "Communication Tests"
        elif "wi-fi" in name or "wifi" in name or "network" in name:
            return "Network Tests"
        elif "audio" in name or "led" in name:
            return "Audio / Visual Tests"
        elif "gpio" in name or "servo" in name:
            return "GPIO Tests"
        else:
            return "General Tests"

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

        self.category_notebook = ttk.Notebook(left_frame)
        self.category_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.build_category_tabs()

        select_all_button = ttk.Button(
            left_frame,
            text="Select All",
            command=self.select_all
        )
        select_all_button.pack(fill="x", padx=8, pady=4)
        self.selection_controls.append(select_all_button)

        clear_selection_button = ttk.Button(
            left_frame,
            text="Clear Selection",
            command=self.clear_selection
        )
        clear_selection_button.pack(fill="x", padx=8, pady=4)
        self.selection_controls.append(clear_selection_button)

        run_selected_button = ttk.Button(
            left_frame,
            text="Run Selected",
            command=self.run_selected_tests
        )
        run_selected_button.pack(fill="x", padx=8, pady=12)
        self.run_controls.append(run_selected_button)

        run_auto_button = ttk.Button(
            left_frame,
            text="Run All Automatic Tests",
            command=self.run_all_automatic_tests
        )
        run_auto_button.pack(fill="x", padx=8, pady=4)
        self.run_controls.append(run_auto_button)

        self.stop_button = ttk.Button(
            left_frame,
            text="Stop After Current Test",
            command=self.request_stop,
            state="disabled"
        )
        self.stop_button.pack(fill="x", padx=8, pady=4)

        save_button = ttk.Button(
            left_frame,
            text="Save Results",
            command=self.save_results
        )
        save_button.pack(fill="x", padx=8, pady=12)
        self.run_controls.append(save_button)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        instructions_frame = ttk.LabelFrame(right_frame, text="Instructions")
        instructions_frame.pack(fill="x", padx=5, pady=5)

        self.instructions_box = tk.Text(
            instructions_frame,
            height=7,
            wrap="word"
        )
        self.instructions_box.pack(fill="x", padx=5, pady=5)
        self.instructions_box.insert("end", "Select a test to view setup instructions.")

        progress_frame = ttk.LabelFrame(right_frame, text="Progress")
        progress_frame.pack(fill="x", padx=5, pady=5)

        self.progress_label = ttk.Label(
            progress_frame,
            text="Progress: 0 of 0 tests complete"
        )
        self.progress_label.pack(anchor="w", padx=5, pady=3)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            value=0
        )
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        results_frame = ttk.LabelFrame(right_frame, text="Results")
        results_frame.pack(fill="both", expand=True, padx=5, pady=5)

        table_frame = ttk.Frame(results_frame)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("Time", "Test", "Status", "Details")
        self.results_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10
        )

        self.results_table.heading("Time", text="Time")
        self.results_table.heading("Test", text="Test")
        self.results_table.heading("Status", text="Status")
        self.results_table.heading("Details", text="Details")

        self.results_table.column("Time", width=155, minwidth=130, stretch=False)
        self.results_table.column("Test", width=220, minwidth=180, stretch=True)
        self.results_table.column("Status", width=90, minwidth=80, stretch=False)
        self.results_table.column("Details", width=600, minwidth=350, stretch=True)

        y_scroll = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.results_table.yview
        )

        x_scroll = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.results_table.xview
        )

        self.results_table.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )

        self.results_table.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.results_table.bind(
            "<<TreeviewSelect>>",
            self.update_full_details_from_selection
        )

        self.setup_result_tags()

        details_frame = ttk.LabelFrame(right_frame, text="Full Details")
        details_frame.pack(fill="both", expand=True, padx=5, pady=5)

        details_text_frame = ttk.Frame(details_frame)
        details_text_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.full_details_box = tk.Text(
            details_text_frame,
            height=8,
            wrap="word"
        )

        details_scroll = ttk.Scrollbar(
            details_text_frame,
            orient="vertical",
            command=self.full_details_box.yview
        )

        self.full_details_box.configure(yscrollcommand=details_scroll.set)

        self.full_details_box.grid(row=0, column=0, sticky="nsew")
        details_scroll.grid(row=0, column=1, sticky="ns")

        details_text_frame.rowconfigure(0, weight=1)
        details_text_frame.columnconfigure(0, weight=1)

        details_button_frame = ttk.Frame(details_frame)
        details_button_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            details_button_frame,
            text="Show Selected Details",
            command=self.show_selected_details_popup
        ).pack(side="left", padx=5)

        ttk.Button(
            details_button_frame,
            text="Copy Selected Details",
            command=self.copy_selected_details
        ).pack(side="left", padx=5)

        self.status_label = ttk.Label(self.root, text="Ready")
        self.status_label.pack(pady=5)

    def build_category_tabs(self):
        categories = {}

        for test in self.tests:
            category = self.infer_category(test)

            if category not in categories:
                categories[category] = []

            categories[category].append(test)

        for category_name, category_tests in categories.items():
            tab = ttk.Frame(self.category_notebook)
            self.category_notebook.add(tab, text=category_name)

            for test in category_tests:
                var = tk.BooleanVar(value=False)

                checkbox = ttk.Checkbutton(
                    tab,
                    text=test["name"],
                    variable=var,
                    command=self.update_instructions
                )
                checkbox.pack(anchor="w", padx=8, pady=4)

                self.test_vars[test["name"]] = var
                self.selection_controls.append(checkbox)

    def setup_result_tags(self):
        self.results_table.tag_configure("PASS", background="#d8f5d0")
        self.results_table.tag_configure("FAIL", background="#f8d0d0")
        self.results_table.tag_configure("ERROR", background="#f8d0d0")
        self.results_table.tag_configure("WARN", background="#fff3bf")
        self.results_table.tag_configure("SKIP", background="#e0e0e0")
        self.results_table.tag_configure("RUNNING", background="#d7e9ff")
        self.results_table.tag_configure("STOPPED", background="#e0e0e0")

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

            if test.get("skip_gui_setup_prompt", False):
                self.instructions_box.insert(
                    "end",
                    "This test handles its own switch/setup prompts internally.\n"
                )
            else:
                self.instructions_box.insert(
                    "end",
                    "Switch/setup checklist will be shown before this test runs.\n"
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

    def get_automatic_tests(self):
        """
        Automatic tests are tests that do not need manual observation
        and do not handle internal pop-ups.
        """
        automatic_tests = []

        for test in self.tests:
            requires_observation = test.get("requires_observation", False)
            has_internal_prompts = test.get("skip_gui_setup_prompt", False)

            if not requires_observation and not has_internal_prompts:
                automatic_tests.append(test)

        return automatic_tests

    def select_all(self):
        if self.is_running:
            return

        for var in self.test_vars.values():
            var.set(True)

        self.update_instructions()

    def clear_selection(self):
        if self.is_running:
            return

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

        self.start_test_run(selected_tests)

    def run_all_automatic_tests(self):
        automatic_tests = self.get_automatic_tests()

        if not automatic_tests:
            messagebox.showwarning(
                "No Automatic Tests",
                "No automatic tests are available."
            )
            return

        self.start_test_run(automatic_tests)

    def start_test_run(self, selected_tests):
        if self.is_running:
            messagebox.showwarning(
                "Testing Already Running",
                "A test run is already in progress."
            )
            return

        self.results = []
        self.results_table.delete(*self.results_table.get_children())
        self.set_full_details_text("")

        self.stop_requested = False
        self.is_running = True

        self.total_tests_to_run = len(selected_tests)
        self.completed_tests = 0
        self.update_progress_safe()

        self.set_controls_running_state(True)

        test_thread = threading.Thread(
            target=self.run_tests_thread,
            args=(selected_tests,),
            daemon=True
        )
        test_thread.start()

    def run_tests_thread(self, selected_tests):
        self.set_status("Running selected tests...")

        for test in selected_tests:
            if self.stop_requested:
                break

            test_name = test["name"]

            self.add_result_row_safe(
                test_name,
                "RUNNING",
                "Waiting for setup checklist confirmation..."
            )

            if test.get("skip_gui_setup_prompt", False):
                setup_confirmed = True
                self.update_last_temp_row_safe(
                    test_name,
                    "RUNNING",
                    "This test is handling its own switch/setup prompts."
                )
            else:
                self.set_status(f"Waiting for setup confirmation: {test_name}")

                setup_confirmed = self.confirm_setup_checklist(test)

                if not setup_confirmed:
                    result = {
                        "name": test_name,
                        "status": "SKIP",
                        "details": "Test skipped because the setup/switch checklist was not confirmed."
                    }

                    result = self.add_timestamp_to_result(result)
                    self.results.append(result)
                    self.completed_tests += 1
                    self.refresh_results_table_safe()
                    self.update_progress_safe()
                    continue

            if self.stop_requested:
                break

            self.set_status(f"Running test: {test_name}")
            self.update_last_temp_row_safe(
                test_name,
                "RUNNING",
                "Test in progress..."
            )

            result = self.run_test_file(test)

            if self.should_ask_for_observation(test, result):
                self.set_status(f"Waiting for manual confirmation: {test_name}")
                result = self.ask_for_manual_confirmation(test, result)

            result = self.add_timestamp_to_result(result)
            self.results.append(result)

            self.completed_tests += 1
            self.refresh_results_table_safe()
            self.update_progress_safe()

        if self.stop_requested:
            self.set_status("Testing stopped after current test")
        else:
            self.set_status("Testing complete")

        self.is_running = False
        self.set_controls_running_state_safe(False)

    def run_test_file(self, test):
        test_name = test["name"]
        test_file = self.base_dir / test["file"]
        timeout = test.get("timeout", 30)

        test_args = test.get("args", [])

        if not test_file.exists():
            return {
                "name": test_name,
                "status": "ERROR",
                "details": f"Test file not found: {test_file}"
            }

        try:
            command = [sys.executable, str(test_file)] + test_args

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
                    "details": stderr or "No output returned from test file"
                }

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

    def confirm_setup_checklist(self, test):
        """
        Shows switch-position confirmation pop-ups before running a test.

        If the test has 'switch_steps' in tests.json, each step gets its own pop-up.
        If not, it falls back to the older 'switch_checklist' field.
        """

        test_name = test.get("name", "Unknown Test")

        switch_steps = test.get("switch_steps", [])

        if not switch_steps:
            old_checklist = test.get("switch_checklist", [])

            if old_checklist:
                switch_steps = [
                    "\n".join([f"• {item}" for item in old_checklist])
                ]
            else:
                switch_steps = [
                    (
                        "• Placeholder: Set the switch bank for this test.\n"
                        "• Placeholder: Confirm GPIO ports are routed to the proper test peripheral.\n"
                        "• Specific switch positions will be added later."
                    )
                ]

        for step_number, step_text in enumerate(switch_steps, start=1):
            response_event = threading.Event()
            response_holder = {}

            def show_popup():
                message = (
                    f"Before running: {test_name}\n\n"
                    f"Switch Setup Step {step_number} of {len(switch_steps)}:\n\n"
                    f"{step_text}\n\n"
                    "All wiring is automatic. Only update the switch positions.\n\n"
                    "Click Yes after the switches are set correctly.\n"
                    "Click No to skip this test."
                )

                response_holder["confirmed"] = messagebox.askyesno(
                    "Switch Position Confirmation",
                    message
                )

                response_event.set()

            self.root.after(0, show_popup)
            response_event.wait()

            if not response_holder.get("confirmed", False):
                return False

        return True

    def should_ask_for_observation(self, test, result):
        if not test.get("requires_observation", False):
            return False

        status = result.get("status", "ERROR")

        return status in ["PASS", "WARN"]

    def ask_for_manual_confirmation(self, test, result):
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

    def add_timestamp_to_result(self, result):
        updated_result = dict(result)
        updated_result["timestamp"] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        return updated_result

    def add_result_row_safe(self, name, status, details):
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        def add_row():
            if self.results_table.exists("temp_running"):
                self.results_table.delete("temp_running")

            self.results_table.insert(
                "",
                "end",
                iid="temp_running",
                values=(timestamp, name, status, details),
                tags=(status,)
            )

        self.root.after(0, add_row)

    def update_last_temp_row_safe(self, name, status, details):
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        def update_row():
            if self.results_table.exists("temp_running"):
                self.results_table.item(
                    "temp_running",
                    values=(timestamp, name, status, details),
                    tags=(status,)
                )

        self.root.after(0, update_row)

    def refresh_results_table_safe(self):
        self.root.after(0, self.refresh_results_table)

    def refresh_results_table(self):
        self.results_table.delete(*self.results_table.get_children())

        for index, result in enumerate(self.results):
            status = result.get("status", "ERROR")

            self.results_table.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    result.get("timestamp", ""),
                    result.get("name", "Unknown Test"),
                    status,
                    result.get("details", "No details")
                ),
                tags=(status,)
            )

        if self.results:
            last_index = str(len(self.results) - 1)
            self.results_table.selection_set(last_index)
            self.results_table.focus(last_index)
            self.results_table.see(last_index)
            self.display_result_details(self.results[-1])

    def update_full_details_from_selection(self, event=None):
        selected = self.results_table.selection()

        if not selected:
            return

        item_id = selected[0]

        try:
            index = int(item_id)
            if 0 <= index < len(self.results):
                self.display_result_details(self.results[index])
                return
        except ValueError:
            pass

        values = self.results_table.item(item_id, "values")

        if len(values) >= 4:
            text = (
                f"Time: {values[0]}\n"
                f"Test: {values[1]}\n"
                f"Status: {values[2]}\n\n"
                f"Details:\n{values[3]}"
            )
            self.set_full_details_text(text)

    def display_result_details(self, result):
        text = (
            f"Time: {result.get('timestamp', '')}\n"
            f"Test: {result.get('name', 'Unknown Test')}\n"
            f"Status: {result.get('status', 'ERROR')}\n\n"
            f"Details:\n{result.get('details', 'No details')}"
        )

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

        item_id = selected[0]

        try:
            index = int(item_id)
            if 0 <= index < len(self.results):
                result = self.results[index]
                return (
                    f"Time: {result.get('timestamp', '')}\n"
                    f"Test: {result.get('name', 'Unknown Test')}\n"
                    f"Status: {result.get('status', 'ERROR')}\n\n"
                    f"Details:\n{result.get('details', 'No details')}"
                )
        except ValueError:
            pass

        return self.full_details_box.get("1.0", "end").strip()

    def show_selected_details_popup(self):
        detail_text = self.get_selected_detail_text()

        if not detail_text:
            messagebox.showwarning(
                "No Result Selected",
                "Please select a result row first."
            )
            return

        messagebox.showinfo("Full Test Details", detail_text)

    def copy_selected_details(self):
        detail_text = self.get_selected_detail_text()

        if not detail_text:
            messagebox.showwarning(
                "No Result Selected",
                "Please select a result row first."
            )
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(detail_text)
        self.root.update()

        messagebox.showinfo(
            "Copied",
            "Selected test details copied to clipboard."
        )

    def update_progress_safe(self):
        self.root.after(0, self.update_progress)

    def update_progress(self):
        if self.total_tests_to_run <= 0:
            percent = 0
        else:
            percent = int((self.completed_tests / self.total_tests_to_run) * 100)

        self.progress_bar["value"] = percent

        self.progress_label.config(
            text=(
                f"Progress: {self.completed_tests} of "
                f"{self.total_tests_to_run} tests complete"
            )
        )

    def request_stop(self):
        if self.is_running:
            self.stop_requested = True
            self.set_status(
                "Stop requested. The current test will finish, then testing will stop."
            )

    def set_controls_running_state(self, running):
        state = "disabled" if running else "normal"

        for control in self.selection_controls:
            try:
                control.config(state=state)
            except Exception:
                pass

        for control in self.run_controls:
            try:
                control.config(state=state)
            except Exception:
                pass

        if running:
            self.stop_button.config(state="normal")
        else:
            self.stop_button.config(state="disabled")

    def set_controls_running_state_safe(self, running):
        self.root.after(0, lambda: self.set_controls_running_state(running))

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

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_file = self.base_dir / f"pi_test_results_{timestamp}.txt"

        with open(output_file, "w") as file:
            file.write("Raspberry Pi 4B Test Results\n")
            file.write("=" * 40 + "\n")
            file.write(f"Saved: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}\n")
            file.write("=" * 40 + "\n\n")

            for result in self.results:
                file.write(f"Time: {result.get('timestamp', '')}\n")
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
