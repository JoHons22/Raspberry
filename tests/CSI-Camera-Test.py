import json
import shutil
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

TEST_NAME = "CSI Camera Port Test"

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "camera_test_output"
OUTPUT_FILE = OUTPUT_DIR / "csi_camera_test.png"

# Smaller image keeps the confirmation window usable on the Pi display.
CAPTURE_WIDTH = 320
CAPTURE_HEIGHT = 240

CAPTURE_TIMEOUT_MS = 2000
COMMAND_TIMEOUT_SECONDS = 20


def run_command(command, timeout=COMMAND_TIMEOUT_SECONDS):
    """
    Runs a terminal command and returns:
    return_code, stdout, stderr
    """
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout
        )

        return completed.returncode, completed.stdout.strip(), completed.stderr.strip()

    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out."

    except Exception as e:
        return 1, "", str(e)


def find_camera_command():
    """
    Finds the available legacy Raspberry Pi camera command.
    This version uses the legacy camera stack with raspistill.
    """
    if shutil.which("raspistill"):
        return "raspistill"

    return None


def check_legacy_camera_status():
    """
    Checks whether the legacy camera stack reports a supported and detected camera.
    Expected successful output usually looks similar to:
    supported=1 detected=1
    """
    if not shutil.which("vcgencmd"):
        return {
            "status": "WARN",
            "details": "vcgencmd was not found. Skipping legacy camera detection check."
        }

    code, stdout, stderr = run_command(["vcgencmd", "get_camera"])

    combined_output = (stdout + "\n" + stderr).strip()

    if code != 0:
        return {
            "status": "WARN",
            "details": f"vcgencmd get_camera failed. Output: {combined_output}"
        }

    lowered_output = combined_output.lower()

    if "detected=1" in lowered_output:
        return {
            "status": "PASS",
            "details": combined_output
        }

    if "detected=0" in lowered_output:
        return {
            "status": "FAIL",
            "details": (
                "Legacy camera stack is available, but no camera was detected. "
                f"Output: {combined_output}"
            )
        }

    return {
        "status": "WARN",
        "details": f"Camera status check returned unexpected output: {combined_output}"
    }


def capture_test_image_legacy(camera_command):
    """
    Captures a still PNG image using the legacy raspistill command.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_FILE.exists():
        try:
            OUTPUT_FILE.unlink()
        except Exception:
            pass

    command = [
        camera_command,
        "-n",                         # No preview window
        "-t", str(CAPTURE_TIMEOUT_MS),
        "-w", str(CAPTURE_WIDTH),
        "-h", str(CAPTURE_HEIGHT),
        "-e", "png",                  # Save as PNG so Tkinter can display it
        "-o", str(OUTPUT_FILE)
    ]

    code, stdout, stderr = run_command(command)

    combined_output = (stdout + "\n" + stderr).strip()

    if code != 0:
        return {
            "status": "FAIL",
            "details": f"Legacy camera capture command failed. Output: {combined_output}"
        }

    if not OUTPUT_FILE.exists():
        return {
            "status": "FAIL",
            "details": "Camera command completed, but no image file was created."
        }

    file_size = OUTPUT_FILE.stat().st_size

    if file_size < 1024:
        return {
            "status": "FAIL",
            "details": f"Image file was created but is too small: {file_size} bytes."
        }

    return {
        "status": "PASS",
        "details": (
            f"Image captured successfully using legacy raspistill. "
            f"File: {OUTPUT_FILE} "
            f"Size: {file_size} bytes."
        )
    }


class CameraConfirmationDialog:
    def __init__(self, root, image_path):
        self.root = root
        self.image_path = image_path
        self.user_result = "WARN"
        self.photo = None

        self.root.title("CSI Camera Confirmation")
        self.root.geometry("520x460")
        self.root.minsize(480, 420)
        self.root.resizable(True, True)

        # Keep this window above the main GUI
        self.root.attributes("-topmost", True)

        # If user closes the window without choosing, return WARN
        self.root.protocol("WM_DELETE_WINDOW", self.close_without_choice)

        self.build_ui()

    def build_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(
            main_frame,
            text="CSI Camera Port Test",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=4)

        instruction_label = ttk.Label(
            main_frame,
            text=(
                "The image below was captured from the CSI camera port.\n"
                "Select Pass if the image is visible and looks correct."
            ),
            justify="center",
            wraplength=460
        )
        instruction_label.pack(pady=4)

        # Put buttons near the top so they are always easy to find.
        top_button_frame = ttk.Frame(main_frame)
        top_button_frame.pack(pady=6)

        ttk.Button(
            top_button_frame,
            text="PASS - Image Looks Correct",
            command=self.pass_test
        ).pack(side="left", padx=8)

        ttk.Button(
            top_button_frame,
            text="FAIL - Image Is Bad",
            command=self.fail_test
        ).pack(side="left", padx=8)

        image_frame = ttk.LabelFrame(main_frame, text="Captured Image", padding=8)
        image_frame.pack(pady=8)

        try:
            self.photo = tk.PhotoImage(file=str(self.image_path))

            image_label = ttk.Label(image_frame, image=self.photo)
            image_label.pack()

        except Exception as e:
            error_label = ttk.Label(
                image_frame,
                text=f"Could not display captured image.\nError: {e}",
                justify="center"
            )
            error_label.pack(pady=30)

        file_label = ttk.Label(
            main_frame,
            text=f"Saved image: {self.image_path}",
            wraplength=460,
            justify="center"
        )
        file_label.pack(pady=4)

        # Duplicate buttons at the bottom too.
        bottom_button_frame = ttk.Frame(main_frame)
        bottom_button_frame.pack(side="bottom", pady=8)

        ttk.Button(
            bottom_button_frame,
            text="PASS",
            command=self.pass_test
        ).pack(side="left", padx=10)

        ttk.Button(
            bottom_button_frame,
            text="FAIL",
            command=self.fail_test
        ).pack(side="left", padx=10)

    def pass_test(self):
        self.user_result = "PASS"
        self.root.destroy()

    def fail_test(self):
        self.user_result = "FAIL"
        self.root.destroy()

    def close_without_choice(self):
        self.user_result = "WARN"
        self.root.destroy()


def ask_user_to_confirm_image(image_path):
    """
    Opens a Tkinter window showing the captured camera image.
    The user chooses PASS or FAIL.
    """
    try:
        root = tk.Tk()
        dialog = CameraConfirmationDialog(root, image_path)

        # Make sure the window comes forward
        root.lift()
        root.focus_force()

        root.mainloop()

        return dialog.user_result

    except Exception as e:
        try:
            messagebox.showerror(
                "Camera Confirmation Error",
                f"Could not open camera confirmation window.\n\nError: {e}"
            )
        except Exception:
            pass

        return "ERROR"


def main():
    result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "CSI camera test did not complete."
    }

    try:
        print("CSI CAMERA PORT TEST")
        print("====================")
        print("This test checks the CSI camera port using the legacy Raspberry Pi camera stack.")
        print("The captured image will be shown for manual confirmation.")
        print()

        camera_command = find_camera_command()

        if camera_command is None:
            result = {
                "name": TEST_NAME,
                "status": "ERROR",
                "details": (
                    "No legacy Raspberry Pi camera command was found. "
                    "The test expected raspistill because this Pi is using the legacy camera stack. "
                    "Try running: which raspistill"
                )
            }

            print(json.dumps(result))
            sys.exit(1)

        print(f"Using legacy camera command: {camera_command}")
        print()

        detection_result = check_legacy_camera_status()

        print("Legacy camera detection result:")
        print(detection_result["details"])
        print()

        if detection_result["status"] == "FAIL":
            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": detection_result["details"]
            }

            print(json.dumps(result))
            sys.exit(1)

        capture_result = capture_test_image_legacy(camera_command)

        print("Camera capture result:")
        print(capture_result["details"])
        print()

        if capture_result["status"] != "PASS":
            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": capture_result["details"]
            }

            print(json.dumps(result))
            sys.exit(1)

        user_confirmation = ask_user_to_confirm_image(OUTPUT_FILE)

        if user_confirmation == "PASS":
            result = {
                "name": TEST_NAME,
                "status": "PASS",
                "details": (
                    "CSI camera port test passed. "
                    "The legacy camera stack detected the camera, captured an image, "
                    "and the user confirmed the image looked correct. "
                    f"{capture_result['details']}"
                )
            }

            print(json.dumps(result))
            sys.exit(0)

        if user_confirmation == "FAIL":
            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": (
                    "CSI camera port test failed by user confirmation. "
                    "The camera captured an image file, but the user reported that the image did not look correct. "
                    f"{capture_result['details']}"
                )
            }

            print(json.dumps(result))
            sys.exit(1)

        if user_confirmation == "ERROR":
            result = {
                "name": TEST_NAME,
                "status": "ERROR",
                "details": (
                    "The image was captured, but the confirmation window could not be opened. "
                    f"{capture_result['details']}"
                )
            }

            print(json.dumps(result))
            sys.exit(1)

        result = {
            "name": TEST_NAME,
            "status": "WARN",
            "details": (
                "The image was captured, but the confirmation window was closed without selecting Pass or Fail. "
                f"{capture_result['details']}"
            )
        }

        print(json.dumps(result))
        sys.exit(0)

    except Exception as e:
        result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": str(e)
        }

        print(json.dumps(result))
        sys.exit(1)


if __name__ == "__main__":
    main()
