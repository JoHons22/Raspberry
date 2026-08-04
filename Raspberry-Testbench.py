import json
import subprocess
import sys
import threading
import textwrap
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk


BASE_DIR = Path(__file__).resolve().parent
TESTS_JSON = BASE_DIR / "tests.json"
RESULTS_FILE = BASE_DIR / "pi_test_results.txt"


class PiTestBenchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Raspberry Pi Test Bench")

        # Optimized for 800x480 touchscreen display
        self.root.geometry("800x480")
        self.root.minsize(780, 460)

        self.tests = []
        self.selected_vars = {}
        self.result_details = {}
        self.stop_requested = False
        self.running = False

        self.load_tests()
        self.build_ui()

    def show_touch_popup(
        self,
        title,
        message,
        popup_type="info",
        yes_text="Yes",
        no_text="No",
        ok_text="OK"
    ):
        """
        Custom popup sized for an 800x480 touchscreen.

        popup_type:
            "info"   -> one OK button
            "yesno"  -> Yes and No buttons
        """
        result = {"value": None}

        self.root.update_idletasks()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        popup_width = min(760, max(420, screen_width - 40))
        popup_height = min(410, max(300, screen_height - 70))

        popup_x = max(0, int((screen_width - popup_width) / 2))
        popup_y = max(0, int((screen_height - popup_height) / 2))

        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()
        popup.attributes("-topmost", True)

        main_frame = ttk.Frame(popup, padding=8)
        main_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(
            main_frame,
            text=title,
            font=("Arial", 12, "bold"),
            anchor="center"
        )
        title_label.pack(fill="x", pady=(0, 6))

        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True)

        message_text = tk.Text(
            text_frame,
            wrap="word",
            font=("Arial", 10),
            height=10,
            padx=6,
            pady=6
        )

        text_scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=message_text.yview
        )

        message_text.configure(yscrollcommand=text_scrollbar.set)
        message_text.insert("1.0", message)
        message_text.config(state="disabled")

        message_text.pack(side="left", fill="both", expand=True)
        text_scrollbar.pack(side="right", fill="y")

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(8, 0))

        def close_with_value(value):
            result["value"] = value
            popup.destroy()

        if popup_type == "yesno":
            button_frame.columnconfigure(0, weight=1)
            button_frame.columnconfigure(1, weight=1)

            yes_button = ttk.Button(
                button_frame,
                text=yes_text,
                command=lambda: close_with_value(True)
            )
            yes_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=8)

            no_button = ttk.Button(
                button_frame,
                text=no_text,
                command=lambda: close_with_value(False)
            )
            no_button.grid(row=0, column=1, sticky="ew", padx=(4, 0), ipady=8)

            popup.bind("<Return>", lambda event: close_with_value(True))
            popup.bind("<Escape>", lambda event: close_with_value(False))

            yes_button.focus_set()

        else:
            button_frame.columnconfigure(0, weight=1)

            ok_button = ttk.Button(
                button_frame,
                text=ok_text,
                command=lambda: close_with_value(True)
            )
            ok_button.grid(row=0, column=0, sticky="ew", padx=60, ipady=8)

            popup.bind("<Return>", lambda event: close_with_value(True))
            popup.bind("<Escape>", lambda event: close_with_value(True))

            ok_button.focus_set()

        def on_close():
            if popup_type == "yesno":
                close_with_value(False)
            else:
                close_with_value(True)

        popup.protocol("WM_DELETE_WINDOW", on_close)

        self.root.wait_window(popup)
        return result["value"]

    def load_tests(self):
        if not TESTS_JSON.exists():
            self.show_touch_popup(
                "Missing tests.json",
                f"Could not find tests.json at:\n\n{TESTS_JSON}"
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
            self.show_touch_popup(
                "tests.json Error",
                f"Could not load tests.json:\n\n{e}"
            )
            self.tests = []

    def infer_category(self, test):
        name = test.get("name", "").lower()

        if test.get("manual_only", False):
            return "Manual Hardware Tests"

        if "audio" in name or "camera" in name or "csi" in name or "hdmi" in name:
            return "Audio / Visual Tests"

        return "GPIO / Communication Tests"

    def build_ui(self):
        self.create_styles()

        outer_frame = ttk.Frame(self.root)
        outer_frame.pack(fill="both", expand=True)

        self.main_canvas = tk.Canvas(
            outer_frame,
            highlightthickness=0
        )

        self.main_scrollbar = ttk.Scrollbar(
            outer_frame,
            orient="vertical",
            command=self.main_canvas.yview
        )

        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)

        self.main_scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)

        self.scrollable_main_frame = ttk.Frame(self.main_canvas, padding=5)

        self.main_canvas_window = self.main_canvas.create_window(
            (0, 0),
            window=self.scrollable_main_frame,
            anchor="nw"
        )

        self.scrollable_main_frame.bind(
            "<Configure>",
            self.update_main_scroll_region
        )

        self.main_canvas.bind(
            "<Configure>",
            self.resize_main_canvas_window
        )

        self.root.bind_all("<MouseWheel>", self.on_mousewheel)
        self.root.bind_all("<Button-4>", self.on_mousewheel_linux)
        self.root.bind_all("<Button-5>", self.on_mousewheel_linux)

        title_label = ttk.Label(
            self.scrollable_main_frame,
            text="Raspberry Pi Test Bench",
            font=("Arial", 13, "bold")
        )
        title_label.pack(pady=(0, 3))

        top_frame = ttk.Frame(self.scrollable_main_frame)
        top_frame.pack(fill="x", expand=False)

        self.create_test_selection_panel(top_frame)
        self.create_results_panel(top_frame)

        self.create_control_panel(self.scrollable_main_frame)
        self.create_status_panel(self.scrollable_main_frame)
        self.create_details_panel(self.scrollable_main_frame)

    def update_main_scroll_region(self, event=None):
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def resize_main_canvas_window(self, event):
        self.main_canvas.itemconfig(
            self.main_canvas_window,
            width=event.width
        )

    def on_mousewheel(self, event):
        self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_mousewheel_linux(self, event):
        if event.num == 4:
            self.main_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.main_canvas.yview_scroll(1, "units")

    def create_styles(self):
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Treeview", rowheight=21, font=("Arial", 8))
        style.configure("Treeview.Heading", font=("Arial", 8, "bold"))
        style.configure("TButton", font=("Arial", 10), padding=(4, 6))
        style.configure("TCheckbutton", font=("Arial", 8))
        style.configure("TLabelframe.Label", font=("Arial", 9, "bold"))
        style.configure("TLabel", font=("Arial", 9))

    def create_test_selection_panel(self, parent):
        selection_frame = ttk.LabelFrame(parent, text="Available Tests", padding=4)
        selection_frame.pack(side="left", fill="both", expand=False, padx=(0, 5))

        canvas = tk.Canvas(
            selection_frame,
            width=225,
            height=145,
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(
            selection_frame,
            orient="vertical",
            command=canvas.yview
        )

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
            category_frame = ttk.LabelFrame(scrollable_frame, text=category, padding=4)
            category_frame.pack(fill="x", expand=True, padx=2, pady=3)

            for test in tests:
                var = tk.BooleanVar(value=False)
                self.selected_vars[test["name"]] = var

                checkbox = ttk.Checkbutton(
                    category_frame,
                    text=test["name"],
                    variable=var
                )
                checkbox.pack(anchor="w", pady=1)

    def create_results_panel(self, parent):
        results_frame = ttk.LabelFrame(parent, text="Results", padding=4)
        results_frame.pack(side="right", fill="both", expand=True)

        table_frame = ttk.Frame(results_frame)
        table_frame.pack(fill="both", expand=True)

        self.results_tree = ttk.Treeview(
            table_frame,
            columns=("test", "category", "status", "time"),
            show="headings",
            height=6
        )

        self.results_tree.heading("test", text="Test")
        self.results_tree.heading("category", text="Category")
        self.results_tree.heading("status", text="Status")
        self.results_tree.heading("time", text="Time")

        self.results_tree.column("test", width=150, anchor="w")
        self.results_tree.column("category", width=120, anchor="w")
        self.results_tree.column("status", width=65, anchor="center")
        self.results_tree.column("time", width=65, anchor="center")

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
        control_frame = ttk.LabelFrame(parent, text="Controls", padding=4)
        control_frame.pack(fill="x", pady=(4, 2))

        for col in range(4):
            control_frame.columnconfigure(col, weight=1)

        ttk.Button(
            control_frame,
            text="Select All",
            command=self.select_all_tests
        ).grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        ttk.Button(
            control_frame,
            text="Clear Selection",
            command=self.clear_selection
        ).grid(row=0, column=1, sticky="ew", padx=2, pady=2)

        ttk.Button(
            control_frame,
            text="Run Selected",
            command=self.run_selected_tests
        ).grid(row=0, column=2, sticky="ew", padx=2, pady=2)

        ttk.Button(
            control_frame,
            text="Save Results",
            command=self.save_results
        ).grid(row=0, column=3, sticky="ew", padx=2, pady=2)

    def create_status_panel(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", pady=(0, 2))

        self.progress_label = ttk.Label(status_frame, text="Ready")
        self.progress_label.pack(anchor="w")

    def create_details_panel(self, parent):
        details_frame = ttk.LabelFrame(parent, text="Full Details", padding=5)
        details_frame.pack(fill="x", expand=False, pady=(2, 5))

        text_frame = ttk.Frame(details_frame)
        text_frame.pack(fill="both", expand=True)

        self.details_text = tk.Text(
            text_frame,
            height=10,
            wrap="word",
            state="disabled",
            font=("Arial", 9)
        )

        details_scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.details_text.yview
        )

        self.details_text.configure(yscrollcommand=details_scrollbar.set)

        self.details_text.pack(side="left", fill="both", expand=True)
        details_scrollbar.pack(side="right", fill="y")

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

    def get_selected_tests(self):
        selected_tests = []

        for test in self.tests:
            if not test.get("enabled", True):
                continue

            test_name = test.get("name")

            if test_name in self.selected_vars and self.selected_vars[test_name].get():
                selected_tests.append(test)

        return selected_tests

    def run_selected_tests(self):
        selected_tests = self.get_selected_tests()

        if not selected_tests:
            self.show_touch_popup(
                "No Tests Selected",
                "Please select at least one test to run."
            )
            return

        self.start_test_thread(selected_tests)

    def start_test_thread(self, tests_to_run):
        if self.running:
            self.show_touch_popup(
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

            running_result = {
                "name": test_name,
                "status": "RUNNING",
                "details": "Test is currently running."
            }

            self.root.after(
                0,
                lambda r=running_result, c=category: self.add_result_to_table(r, c)
            )

            if test.get("manual_only", False):
                result = self.run_manual_test(test)

            else:
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
                            lambda r=result, c=category: self.replace_last_running_result(r, c)
                        )
                        continue

                result = self.run_test_file(test)

                if test.get("requires_observation", False):
                    result = self.handle_observation_prompt(test, result)

            self.root.after(
                0,
                lambda r=result, c=category: self.replace_last_running_result(r, c)
            )

        self.root.after(0, lambda: self.finish_test_sequence(total_tests))

    def setup_progress(self, total_tests):
        self.progress_label.config(text=f"Starting {total_tests} test(s)...")

    def finish_test_sequence(self, total_tests):
        self.running = False

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

        instructions = test.get("instructions", "")

        for step_number, step_text in enumerate(switch_steps, start=1):
            response_holder = {"value": False}
            event = threading.Event()

            def ask_user(
                step_number=step_number,
                step_text=step_text
            ):
                instruction_text = ""

                if instructions:
                    instruction_text = f"Instructions:\n{instructions}\n\n"

                response_holder["value"] = self.show_touch_popup(
                    "Switch Setup Required",
                    (
                        f"{test.get('name', 'Test Setup')}\n\n"
                        f"{instruction_text}"
                        f"Step {step_number} of {len(switch_steps)}:\n\n"
                        f"{step_text}\n\n"
                        "Press Continue when ready to run the test.\n"
                        "Press Skip to skip this test."
                    ),
                    popup_type="yesno",
                    yes_text="Continue",
                    no_text="Skip"
                )
                event.set()

            self.root.after(0, ask_user)
            event.wait()

            if not response_holder["value"]:
                return False

        return True

    def run_manual_test(self, test):
        test_name = test.get("name", "Manual Test")
        instructions = test.get("instructions", "")
        manual_steps = test.get("manual_steps", [])

        if not manual_steps:
            manual_steps = [instructions]

        passed_steps = 0
        failed_steps = 0
        skipped_steps = 0
        detail_lines = []

        for step_number, step_text in enumerate(manual_steps, start=1):
            if self.stop_requested:
                skipped_steps += 1
                detail_lines.append(
                    f"Step {step_number}: SKIP - Test sequence was stopped before this step."
                )
                continue

            response_holder = {"value": None}
            event = threading.Event()

            def ask_user(
                step_number=step_number,
                step_text=step_text
            ):
                response_holder["value"] = self.show_touch_popup(
                    "Manual Hardware Test",
                    (
                        f"{test_name}\n\n"
                        f"Step {step_number} of {len(manual_steps)}:\n\n"
                        f"{step_text}\n\n"
                        "Press PASS if this step worked correctly.\n"
                        "Press FAIL if this step did not work correctly."
                    ),
                    popup_type="yesno",
                    yes_text="PASS",
                    no_text="FAIL"
                )
                event.set()

            self.root.after(0, ask_user)
            event.wait()

            if response_holder["value"]:
                passed_steps += 1
                detail_lines.append(f"Step {step_number}: PASS - {step_text}")
            else:
                failed_steps += 1
                detail_lines.append(f"Step {step_number}: FAIL - {step_text}")

        if failed_steps > 0:
            overall_status = "FAIL"
        elif skipped_steps > 0 and passed_steps == 0:
            overall_status = "SKIP"
        elif skipped_steps > 0:
            overall_status = "WARN"
        elif passed_steps > 0:
            overall_status = "PASS"
        else:
            overall_status = "SKIP"

        return {
            "name": test_name,
            "status": overall_status,
            "details": (
                f"Manual hardware test completed. "
                f"PASS={passed_steps}, FAIL={failed_steps}, SKIP={skipped_steps}.\n"
                + "\n".join(detail_lines)
            )
        }

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
            response_holder["value"] = self.show_touch_popup(
                "Manual Observation Required",
                (
                    f"{test.get('name', 'Manual Test')}\n\n"
                    f"{prompt}\n\n"
                    "Press PASS if the test behaved correctly.\n"
                    "Press FAIL if the test did not behave correctly."
                ),
                popup_type="yesno",
                yes_text="PASS",
                no_text="FAIL"
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

    def write_wrapped_details(self, file, details, width=78):
        if not details:
            file.write("No additional details recorded.\n")
            return

        lines = []

        for raw_line in details.splitlines():
            if " | " in raw_line:
                parts = raw_line.split(" | ")
                lines.extend(parts)
            else:
                lines.append(raw_line)

        for line in lines:
            line = line.strip()

            if not line:
                file.write("\n")
                continue

            wrapped_lines = textwrap.wrap(
                line,
                width=width,
                replace_whitespace=False,
                drop_whitespace=True
            )

            if wrapped_lines:
                for wrapped_line in wrapped_lines:
                    file.write(f"{wrapped_line}\n")
            else:
                file.write(f"{line}\n")

    def save_results(self):
        children = self.results_tree.get_children()

        if not children:
            self.show_touch_popup(
                "No Results",
                "There are no results to save."
            )
            return

        overwrite_confirmed = self.show_touch_popup(
            "Overwrite Saved Results?",
            (
                "The test results will be saved to the same file every time:\n\n"
                f"{RESULTS_FILE}\n\n"
                "If an older saved results file already exists, it will be overwritten.\n\n"
                "This helps prevent the SD card from filling up with old report files.\n\n"
                "Do you want to continue?"
            ),
            popup_type="yesno",
            yes_text="Save",
            no_text="Cancel"
        )

        if not overwrite_confirmed:
            return

        try:
            results = []

            for item in children:
                values = self.results_tree.item(item, "values")

                if not values:
                    continue

                test_name = values[0]
                category = values[1]
                status = values[2]
                timestamp = values[3]
                details = self.result_details.get(item, "")

                results.append({
                    "test_name": test_name,
                    "category": category,
                    "status": status,
                    "timestamp": timestamp,
                    "details": details
                })

            status_counts = {
                "PASS": 0,
                "FAIL": 0,
                "ERROR": 0,
                "WARN": 0,
                "SKIP": 0,
                "STOPPED": 0,
                "RUNNING": 0
            }

            for result in results:
                status = result["status"]

                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts[status] = 1

            with open(RESULTS_FILE, "w", encoding="utf-8") as file:
                file.write("RASPBERRY PI TEST BENCH RESULTS\n")
                file.write("=" * 80 + "\n")
                file.write(f"Report Saved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write(f"Results File: {RESULTS_FILE}\n")
                file.write("=" * 80 + "\n\n")

                file.write("DEVICE / TECHNICIAN INFORMATION\n")
                file.write("-" * 80 + "\n")
                file.write("Raspberry Pi Serial Number: ______________________________\n")
                file.write("Technician Name:           ______________________________\n")
                file.write("Test Date:                 ______________________________\n")
                file.write("Signature:                 ______________________________\n")
                file.write("\n")

                file.write("SUMMARY\n")
                file.write("-" * 80 + "\n")
                file.write(f"Total Tests Recorded: {len(results)}\n")
                file.write(f"PASS:    {status_counts.get('PASS', 0)}\n")
                file.write(f"FAIL:    {status_counts.get('FAIL', 0)}\n")
                file.write(f"ERROR:   {status_counts.get('ERROR', 0)}\n")
                file.write(f"WARN:    {status_counts.get('WARN', 0)}\n")
                file.write(f"SKIP:    {status_counts.get('SKIP', 0)}\n")
                file.write("\n")

                file.write("RESULTS TABLE\n")
                file.write("-" * 80 + "\n")
                file.write(f"{'Test Name':<34} {'Status':<10} {'Time':<10} {'Category'}\n")
                file.write("-" * 80 + "\n")

                for result in results:
                    test_name = result["test_name"][:33]
                    status = result["status"]
                    timestamp = result["timestamp"]
                    category = result["category"][:22]

                    file.write(
                        f"{test_name:<34} {status:<10} {timestamp:<10} {category}\n"
                    )

                file.write("\n\n")

                file.write("DETAILED RESULTS\n")
                file.write("=" * 80 + "\n\n")

                for index, result in enumerate(results, start=1):
                    file.write(f"{index}. {result['test_name']}\n")
                    file.write("-" * 80 + "\n")
                    file.write(f"Category: {result['category']}\n")
                    file.write(f"Status:   {result['status']}\n")
                    file.write(f"Time:     {result['timestamp']}\n")
                    file.write("\nDetails:\n")

                    self.write_wrapped_details(file, result["details"], width=78)

                    file.write("\n")
                    file.write("=" * 80 + "\n\n")

                file.write("FINAL DOCUMENTATION SIGN-OFF\n")
                file.write("-" * 80 + "\n")
                file.write("All required tests have been reviewed and documented.\n\n")
                file.write("Technician Signature: ______________________________\n")
                file.write("Date:                 ______________________________\n")
                file.write("\n")
                file.write("END OF REPORT\n")

            self.show_touch_popup(
                "Results Saved",
                (
                    "Results were saved successfully.\n\n"
                    "The same file is overwritten each time to prevent old result files "
                    "from filling the SD card.\n\n"
                    f"File:\n{RESULTS_FILE}"
                )
            )

        except Exception as e:
            self.show_touch_popup(
                "Save Error",
                f"Could not save results:\n\n{e}"
            )


def main():
    root = tk.Tk()
    app = PiTestBenchGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
