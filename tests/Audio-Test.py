import json
import subprocess
import wave
import math
import struct
from pathlib import Path

TEST_NAME = "Audio Playback Test"

# Audio file location
# If this file does not exist, the script will create a simple test tone.
AUDIO_FILE = Path(__file__).resolve().parent / "test_audio.wav"


def create_test_tone(filename, duration=2.0, frequency=440, sample_rate=44100):
    """
    Creates a short WAV test tone if no audio file is available.
    """
    amplitude = 16000
    total_samples = int(duration * sample_rate)

    with wave.open(str(filename), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(total_samples):
            sample = amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)
            wav_file.writeframes(struct.pack("<h", int(sample)))


def run_command(command, timeout=10):
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        return completed.returncode, completed.stdout.strip(), completed.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def main():
    result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "Audio test did not complete."
    }

    try:
        print("AUDIO PLAYBACK TEST")
        print("===================")

        # Create a test tone if the file does not already exist
        if not AUDIO_FILE.exists():
            print(f"No audio file found at {AUDIO_FILE}")
            print("Creating 2-second test tone...")
            create_test_tone(AUDIO_FILE)

        print(f"Playing audio file: {AUDIO_FILE}")

        # Play WAV file using aplay
        code, stdout, stderr = run_command(
            ["aplay", str(AUDIO_FILE)],
            timeout=10
        )

        if code == 0:
            result = {
                "name": TEST_NAME,
                "status": "WARN",
                "details": (
                    "Audio file was played successfully by software. "
                    "Manual listening confirmation is required to verify speaker/headphone output."
                )
            }
            print("AUDIO TEST: PLAYBACK COMMAND PASSED")

        else:
            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": stderr or stdout or "Audio playback command failed."
            }
            print("AUDIO TEST: FAIL")

    except Exception as e:
        result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": str(e)
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
