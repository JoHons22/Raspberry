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


def get_ip_addresses():
    """
    Checks wlan0 for IPv4 and IPv6 addresses.
    Ignores link-local IPv6 addresses starting with fe80 because those do not prove internet access.
    """
    ipv4_addresses = []
    ipv6_addresses = []

    code, stdout, stderr = run_command(
        ["ip", "addr", "show", "dev", WIFI_INTERFACE],
        timeout=5
    )

    if code != 0:
        return ipv4_addresses, ipv6_addresses

    for line in stdout.splitlines():
        line = line.strip()

        if line.startswith("inet "):
            parts = line.split()
            ipv4_addresses.append(parts[1])

        elif line.startswith("inet6 "):
            parts = line.split()
            ipv6 = parts[1]

            # Ignore link-local IPv6 addresses
            if not ipv6.startswith("fe80"):
                ipv6_addresses.append(ipv6)

    return ipv4_addresses, ipv6_addresses


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
        print("This test accepts either IPv4 or IPv6.")
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

        # Check Wi-Fi link status
        code, stdout, stderr = run_command(
            ["iw", "dev", WIFI_INTERFACE, "link"],
            timeout=5
        )

        if code == 0 and "Connected to" in stdout:
            first_line = stdout.splitlines()[0]
            pass_details.append(f"Wi-Fi connected: {first_line}")
            print(stdout)
        else:
            fail_reasons.append("Wi-Fi is not connected to an access point")

        # Check for IPv4 or IPv6 address
        ipv4_addresses, ipv6_addresses = get_ip_addresses()

        if ipv4_addresses:
            pass_details.append(f"IPv4 address found: {ipv4_addresses[0]}")

        if ipv6_addresses:
            pass_details.append(f"IPv6 address found: {ipv6_addresses[0]}")

        if not ipv4_addresses and not ipv6_addresses:
            fail_reasons.append(f"No usable IPv4 or IPv6 address found on {WIFI_INTERFACE}")

        # General ping test.
        # This does NOT force IPv4. It allows the system to use IPv4 or IPv6.
        code, stdout, stderr = run_command(
            ["ping", "-I", WIFI_INTERFACE, "-c", "4", "-W", "2", "google.com"],
            timeout=12
        )

        if code == 0:
            pass_details.append("General ping to google.com passed using available IP version")
        else:
            fail_reasons.append("General ping to google.com failed")

        # Optional IPv4-specific test, only if IPv4 exists
        if ipv4_addresses:
            code, stdout, stderr = run_command(
                ["ping", "-4", "-I", WIFI_INTERFACE, "-c", "4", "-W", "2", "google.com"],
                timeout=12
            )

            if code == 0:
                pass_details.append("IPv4 ping passed")
            else:
                fail_reasons.append("IPv4 address exists, but IPv4 ping failed")

        # Optional IPv6-specific test, only if IPv6 exists
        if ipv6_addresses:
            code, stdout, stderr = run_command(
                ["ping", "-6", "-I", WIFI_INTERFACE, "-c", "4", "-W", "2", "google.com"],
                timeout=12
            )

            if code == 0:
                pass_details.append("IPv6 ping passed")
            else:
                fail_reasons.append("IPv6 address exists, but IPv6 ping failed")

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
