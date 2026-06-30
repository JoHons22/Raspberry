import json
import math
import struct
import subprocess

TEST_NAME = "Audio Playback Test"

DURATION_SECONDS = 5
FREQUENCY_HZ = 440
SAMPLE_RATE = 44100
CHANNELS = 2
AMPLITUDE = 18000


def generate_tone():
    """
    Generate a stereo 16-bit PCM sine wave in memory.
    No audio file is needed.
    """
    total_samples = int(DURATION_SECONDS * SAMPLE_RATE)
    fade_samples = int(0.05 * SAMPLE_RATE)

    audio_data = bytearray()

    for i in range(total_samples):
        fade = 1.0

        # Small fade-in and fade-out to avoid popping
        if i < fade_samples:
            fade = i / fade_samples
        elif i > total_samples - fade_samples:
            fade = (total_samples - i) / fade_samples

        sample = AMPLITUDE * fade * math.sin(
            2 * math.pi * FREQUENCY_HZ * i / SAMPLE_RATE
        )

        packed_sample = struct.pack("<h", int(sample))

        # Stereo: left and right channels
        audio_data.extend(packed_sample)
        audio_data.extend(packed_sample)

    return bytes(audio_data)


def main():
    result = {
        "name": TEST_NAME,
        "status": "ERROR",
        "details": "Audio test did not complete."
    }

    try:
        print("AUDIO PLAYBACK TEST")
        print("===================")
        print("Generating test tone in software.")
        print(f"Frequency: {FREQUENCY_HZ} Hz")
        print(f"Duration: {DURATION_SECONDS} seconds")
        print("No audio file is required.")
        print()

        audio_data = generate_tone()

        command = [
            "aplay",
            "-D", "default",
            "-f", "S16_LE",
            "-r", str(SAMPLE_RATE),
            "-c", str(CHANNELS)
        ]

        completed = subprocess.run(
            command,
            input=audio_data,
            capture_output=True,
            timeout=DURATION_SECONDS + 5
        )

        if completed.returncode == 0:
            result = {
                "name": TEST_NAME,
                "status": "WARN",
                "details": (
                    f"Generated and played a {DURATION_SECONDS}-second "
                    f"{FREQUENCY_HZ} Hz test tone. Manual listening confirmation is required."
                )
            }
            print("AUDIO TEST: PLAYBACK COMMAND PASSED")

        else:
            stderr = completed.stderr.decode(errors="ignore").strip()
            stdout = completed.stdout.decode(errors="ignore").strip()

            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": stderr or stdout or "Audio playback command failed."
            }
            print("AUDIO TEST: FAIL")

    except subprocess.TimeoutExpired:
        result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": "Audio playback timed out."
        }

    except Exception as e:
        result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": str(e)
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
