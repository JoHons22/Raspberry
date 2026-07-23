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

CAPTURE_WIDTH = 640
CAPTURE_HEIGHT = 480
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


def find_camera_commands():
    """
    Finds the available Raspberry Pi camera command set.

    Newer Raspberry Pi OS versions use rpicam-*.
    Older Raspberry Pi OS versions may use libcamera-*.
    """

    if shutil.which("rpicam-still"):
        return {
            "tool_set": "rpicam",
            "still": "rpicam-still",
            "hello": "rpicam-hello" if shutil.which("rpicam-hello") else None
        }

    if shutil.which("libcamera-still"):
        return {
            "tool_set": "libcamera",
            "still": "libcamera-still",
            "hello": "libcamera-hello" if shutil.which("libcamera-hello") else None
        }

    return None


def list_detected_cameras(camera_tools):
    """
    Uses rpicam-hello/libcamera-hello to list detected cameras when available.
    """

    hello_command = camera_tools.get("hello")

    if hello_command is None:
        return {
            "status": "WARN",
            "details": "Camera listing command was not found. Capture test will still run."
        }

    command = [hello_command, "--list-cameras"]

    code, stdout, stderr = run_command(command)

    combined_output = (stdout + "\n" + stderr).strip()

    if code != 0:
        return {
            "status": "FAIL",
            "details": f"Camera list command failed. Output: {combined_output}"
        }

    lowered_output = combined_output.lower()

    if "no cameras available" in lowered_output or "no cameras found" in lowered_output:
        return {
            "status": "FAIL",
            "details": f"No CSI camera was detected. Output: {combined_output}"
        }

    return {
        "status": "PASS",
        "details": combined_output if combined_output else "Camera list command completed successfully."
    }


def capture_test_image(camera_tools):
    """
    Captures a still PNG image from the CSI camera.
    """

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_FILE.exists():
        try:
            OUTPUT_FILE.unlink()
        except Exception:
            pass

    still_command = camera_tools["still"]

    command = [
        still_command,
        "--nopreview",
        "-t", str(CAPTURE_TIMEOUT_MS),
        "--width", str(CAPTURE_WIDTH),
        "--height", str(CAPTURE_HEIGHT),
        "--encoding", "png",
        "-o", str(OUTPUT_FILE)
    ]

    code, stdout, stderr = run_command(command)

    combined_output = (stdout + "\n" + stderr).strip()

    if code != 0:
        return {
            "status": "FAIL",
            "details": f"Camera capture command failed. Output: {combined_output}"
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
            f"Image captured successfully. "
            f"File: {OUTPUT_FILE} "
            f"Size: {file_size} bytes."
        )
    }


class CameraConfirmationDialog:
    def __init__(self, root, image_path):
        self.root = root
        self.image_path = image_path
        self.user_result = "WARN"

        self.root.title("CSI Camera Image Confirmation")
        self.root.geometry("760x650")
        self.root.resizable(False, False)

        # Keep this window above the main GUI
        self.root.attributes("-topmost", True)

        self.photo = None
        self.build_ui()

    def build_ui(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(
            main_frame,
            text="CSI Camera Port Test",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=5)

        instruction_label = ttk.Label(
            main_frame,
            text=(
                "A test image was captured from the CSI camera port.\n"
                "Confirm whether the image below looks like a valid camera image."
            ),
            justify="center"
        )
        instruction_label.pack(pady=5)

        image_frame = ttk.Frame(main_frame)
        image_frame.pack(pady=10)

        try:
            original_photo = tk.PhotoImage(file=str(self.image_path))

            # Keep image visible by saving it as an instance variable.
            # The capture size is already 640x480, so it should fit in the window.
            self.photo = original_photo

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
            wraplength=700,
            justify="center"
        )
        file_label.pack(pady=5)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side="bottom", pady=10)

        pass_btn = ttk.Button(
            btn_frame,
            text="Pass - Image Looks Correct",
            command=self.pass_test
        )
        pass_btn.pack(side="left", padx=10)

        fail_btn = ttk.Button(
            btn_frame,
            text="Fail - Image Is Bad",
            command=self.fail_test
        )
        fail_btn.pack(side="left", padx=10)

    def pass_test(self):
        self.user_result = "PASS"
        self.root.destroy()

    def fail_test(self):
        self.user_result = "FAIL"
        self.root.destroy()


def ask_user_to_confirm_image(image_path):
    """
    Opens a Tkinter window showing the captured camera image.
    The user chooses PASS or FAIL.
    """

    try:
        root = tk.Tk()
        dialog = CameraConfirmationDialog(root, image_path)
        root.mainloop()

        return dialog.user_result

    except Exception as e:
        messagebox.showerror(
            "Camera Confirmation Error",
            f"Could not open camera confirmation window.\n\nError: {e}"
        )

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
        print("This test checks whether the Raspberry Pi can detect and capture from the CSI camera.")
        print("The captured image will be shown for manual confirmation.")
        print()

        camera_tools = find_camera_commands()

        if camera_tools is None:
            result = {
                "name": TEST_NAME,
                "status": "ERROR",
                "details": (
                    "No Raspberry Pi camera command was found. "
                    "Install the camera tools first. Try: sudo apt install rpicam-apps"
                )
            }

            print(json.dumps(result))
            sys.exit(1)

        print(f"Using camera tool set: {camera_tools['tool_set']}")
        print(f"Still capture command: {camera_tools['still']}")
        print()

        list_result = list_detected_cameras(camera_tools)

        print("Camera detection result:")
        print(list_result["details"])
        print()

        if list_result["status"] == "FAIL":
            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": list_result["details"]
            }

            print(json.dumps(result))
            sys.exit(1)

        capture_result = capture_test_image(camera_tools)

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
                    "The camera was detected, an image was captured, and the user confirmed the image looked correct. "
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
