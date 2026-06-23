import json
import subprocess
from pathlib import Path

TEST_NAME = "Wi-Fi Ping Test"
WIFI_INTERFACE = "wlan0"


def run_command(command, timeout=8):
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
        "details": "Wi-Fi test did not complete."
    }

    try:
        print("WI-FI PING TEST")
        print("===============")
        print(f"Testing Wi-Fi interface: {WIFI_INTERFACE}")
        print("This test checks wlan0, IP address, internet ping, and DNS.")
        print()

        fail_reasons = []
        pass_details = []

        # Check that wlan0 exists
        wlan_path = Path(f"/sys/class/net/{WIFI_INTERFACE}")

        if not wlan_path.exists():
            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": f"{WIFI_INTERFACE} not found. Wi-Fi adapter was not detected."
            }
            print(json.dumps(result))
            return

        pass_details.append(f"{WIFI_INTERFACE} detected")

        # Check Wi-Fi link status if iw is available
        code, stdout, stderr = run_command(["iw", "dev", WIFI_INTERFACE, "link"], timeout=5)

        if code == 0 and "Connected to" in stdout:
            first_line = stdout.splitlines()[0]
            pass_details.append(f"Wi-Fi connected: {first_line}")
            print(stdout)
        else:
            fail_reasons.append("Wi-Fi is not connected to an access point")

        # Check that wlan0 has an IPv4 address
        code, stdout, stderr = run_command(["ip", "-4", "addr", "show", "dev", WIFI_INTERFACE], timeout=5)

        if code == 0 and "inet " in stdout:
            ip_line = [line.strip() for line in stdout.splitlines() if "inet " in line][0]
            ip_address = ip_line.split()[1]
            pass_details.append(f"IPv4 address found: {ip_address}")
        else:
            fail_reasons.append(f"No IPv4 address found on {WIFI_INTERFACE}")

        # Ping Google DNS by IP address.
        # This checks internet access without depending on DNS.
        code, stdout, stderr = run_command(
            ["ping", "-I", WIFI_INTERFACE, "-c", "4", "-W", "2", "8.8.8.8"],
            timeout=12
        )

        if code == 0:
            pass_details.append("Ping to 8.8.8.8 passed")
        else:
            fail_reasons.append("Ping to 8.8.8.8 failed")

        # Ping google.com.
        # This checks both internet and DNS name resolution.
        code, stdout, stderr = run_command(
            ["ping", "-I", WIFI_INTERFACE, "-c", "4", "-W", "2", "google.com"],
            timeout=12
        )

        if code == 0:
            pass_details.append("Ping to google.com passed")
        else:
            fail_reasons.append("Ping to google.com failed. DNS or internet access may be unavailable.")

        print()
        print("FINAL RESULT")
        print("============")

        if not fail_reasons:
            result = {
                "name": TEST_NAME,
                "status": "PASS",
                "details": "; ".join(pass_details)
            }
            print("WI-FI TEST: PASS")
        else:
            result = {
                "name": TEST_NAME,
                "status": "FAIL",
                "details": "Passed: " + "; ".join(pass_details) + " | Failed: " + "; ".join(fail_reasons)
            }
            print("WI-FI TEST: FAIL")

    except Exception as e:
        result = {
            "name": TEST_NAME,
            "status": "ERROR",
            "details": str(e)
        }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
