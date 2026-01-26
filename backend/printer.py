"""
Bambu X1C printer integration.

This module handles:
1. Slicing STL files using OrcaSlicer CLI
2. Uploading sliced files to the printer via FTPS
3. Starting prints via MQTT commands

Requirements:
- Printer must have Developer Mode enabled
- User provides: IP address, Access Code, Serial Number
"""

import os
import json
import ssl
import ftplib
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# Try to import bambulabs_api, fall back to manual implementation if not available
try:
    import bambulabs_api as bl
    HAS_BAMBU_API = True
except ImportError:
    HAS_BAMBU_API = False
    import paho.mqtt.client as mqtt


class PrinterError(Exception):
    """Error during printer operations."""
    pass


# Security: Define allowed directories for file operations
MAPS_DIR = Path(os.environ.get("MAPS_DIR", "/data/maps"))
PROFILES_DIR = Path(__file__).parent / "profiles"


def find_orcaslicer() -> Optional[str]:
    """Find OrcaSlicer executable."""
    # Check environment variable first
    orca_path = os.environ.get("ORCASLICER_PATH")
    if orca_path and os.path.exists(orca_path):
        return orca_path

    # Common installation locations
    locations = [
        "/usr/local/bin/orca-slicer",
        "/opt/OrcaSlicer/orca-slicer",
        "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer",
        os.path.expanduser("~/.local/bin/orca-slicer"),
    ]

    for loc in locations:
        if os.path.exists(loc):
            return loc

    # Try PATH
    try:
        result = subprocess.run(
            ["which", "orca-slicer"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass

    return None


def slice_to_3mf(stl_path: str, output_path: str, profile_path: Optional[str] = None) -> str:
    """
    Slice an STL file to 3MF using OrcaSlicer CLI.

    This standalone function doesn't require printer configuration.

    Args:
        stl_path: Path to input STL file
        output_path: Path for output 3MF file
        profile_path: Optional path to slicing profile JSON

    Returns:
        Path to the sliced 3MF file

    Raises:
        PrinterError: If slicing fails or OrcaSlicer not found
    """
    orca_path = find_orcaslicer()
    if orca_path is None:
        raise PrinterError(
            "OrcaSlicer not found. Install from https://github.com/SoftFever/OrcaSlicer"
        )

    cmd = [orca_path, "--export-3mf", output_path]

    if profile_path and os.path.exists(profile_path):
        cmd.extend(["--load-settings", profile_path])

    cmd.append(stl_path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            raise PrinterError(f"OrcaSlicer failed: {result.stderr}")

        return output_path

    except subprocess.TimeoutExpired:
        raise PrinterError("Slicing timed out after 5 minutes")
    except FileNotFoundError:
        raise PrinterError(f"OrcaSlicer not found at {orca_path}")


def validate_file_path(file_path: str, allowed_dir: Path) -> Path:
    """
    Security: Validate that a file path is within the allowed directory.

    Args:
        file_path: Path to validate
        allowed_dir: Directory that must contain the file

    Returns:
        Resolved Path object

    Raises:
        PrinterError: If path is outside allowed directory
    """
    path = Path(file_path)
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(allowed_dir.resolve()):
            raise PrinterError(f"Access denied: file must be within {allowed_dir}")
        return resolved
    except ValueError:
        raise PrinterError("Access denied: invalid file path")


class BambuPrinter:
    """
    Client for Bambu Lab X1C printer.

    Handles:
    - File upload via FTPS (port 990)
    - Print commands via MQTT (port 8883)
    """

    def __init__(self, ip: str, access_code: str, serial: str):
        """
        Initialize printer connection.

        Args:
            ip: Printer's IP address
            access_code: 8-digit LAN access code from printer settings
            serial: Printer serial number
        """
        self.ip = ip
        self.access_code = access_code
        self.serial = serial
        self.mqtt_client = None

    def slice_stl(
        self,
        stl_path: str,
        output_path: str,
        profile_path: Optional[str] = None
    ) -> str:
        """
        Slice an STL file to 3MF using OrcaSlicer CLI.

        Args:
            stl_path: Path to input STL file
            output_path: Path for output 3MF file
            profile_path: Optional path to slicing profile JSON

        Returns:
            Path to the sliced 3MF file
        """
        # Check if OrcaSlicer is available
        orca_path = self._find_orcaslicer()
        if orca_path is None:
            raise PrinterError(
                "OrcaSlicer not found. Install from https://github.com/SoftFever/OrcaSlicer"
            )

        # Build command
        cmd = [
            orca_path,
            "--export-3mf", output_path,
        ]

        if profile_path and os.path.exists(profile_path):
            cmd.extend(["--load-settings", profile_path])

        cmd.append(stl_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                raise PrinterError(f"OrcaSlicer failed: {result.stderr}")

            return output_path

        except subprocess.TimeoutExpired:
            raise PrinterError("Slicing timed out after 5 minutes")
        except FileNotFoundError:
            raise PrinterError(f"OrcaSlicer not found at {orca_path}")

    def _find_orcaslicer(self) -> Optional[str]:
        """Find OrcaSlicer executable."""
        return find_orcaslicer()

    def upload_file(self, local_path: str, remote_filename: Optional[str] = None) -> str:
        """
        Upload a file to the printer via FTPS.

        Args:
            local_path: Path to local file
            remote_filename: Optional filename on printer (defaults to local filename)

        Returns:
            Remote path on printer
        """
        if remote_filename is None:
            remote_filename = os.path.basename(local_path)

        remote_path = f"/cache/{remote_filename}"

        try:
            # Create FTP_TLS connection
            ftp = ftplib.FTP_TLS()
            ftp.connect(self.ip, 990, timeout=30)

            # Login with printer credentials
            ftp.login("bblp", self.access_code)

            # Switch to secure data connection
            ftp.prot_p()

            # Upload file
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)

            ftp.quit()

            return remote_path

        except ftplib.all_errors as e:
            raise PrinterError(f"FTP upload failed: {e}")

    def start_print(self, file_path: str, plate: int = 1) -> dict:
        """
        Start a print job on the printer.

        Args:
            file_path: Path to file on printer (e.g., /cache/model.3mf)
            plate: Plate number to print (default 1)

        Returns:
            Response from printer
        """
        if HAS_BAMBU_API:
            return self._start_print_bambu_api(file_path)
        else:
            return self._start_print_mqtt(file_path, plate)

    def _start_print_bambu_api(self, file_path: str) -> dict:
        """Start print using bambulabs_api library."""
        try:
            printer = bl.Printer(self.ip, self.access_code, self.serial)
            printer.connect()

            # Start the print
            result = printer.start_print(file_path)

            printer.disconnect()
            return {"status": "print_started", "result": result}

        except Exception as e:
            raise PrinterError(f"Failed to start print: {e}")

    def _start_print_mqtt(self, file_path: str, plate: int = 1) -> dict:
        """Start print using raw MQTT commands."""
        import time
        import uuid

        # Extract filename from path
        filename = os.path.basename(file_path)

        # Build the print command
        command = {
            "print": {
                "sequence_id": str(int(time.time())),
                "command": "project_file",
                "param": f"Metadata/plate_{plate}.gcode",
                "subtask_name": filename,
                "url": f"file://{file_path}",
                "timelapse": False,
                "bed_leveling": True,
                "flow_cali": True,
                "vibration_cali": True,
                "layer_inspect": False,
                "use_ams": True,
            }
        }

        # Connect and send via MQTT
        try:
            response = {"status": "pending"}

            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    # Subscribe to response topic
                    client.subscribe(f"device/{self.serial}/report")
                    # Send command
                    client.publish(
                        f"device/{self.serial}/request",
                        json.dumps(command)
                    )
                else:
                    response["status"] = "connection_failed"
                    response["error"] = f"MQTT connection failed with code {rc}"

            def on_message(client, userdata, msg):
                try:
                    data = json.loads(msg.payload)
                    response["status"] = "print_started"
                    response["data"] = data
                except:
                    pass

            client = mqtt.Client()
            client.username_pw_set("bblp", self.access_code)
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)

            client.on_connect = on_connect
            client.on_message = on_message

            client.connect(self.ip, 8883, 60)

            # Wait for response
            client.loop_start()
            time.sleep(5)
            client.loop_stop()
            client.disconnect()

            return response

        except Exception as e:
            raise PrinterError(f"MQTT command failed: {e}")

    def get_status(self) -> dict:
        """Get printer status."""
        if HAS_BAMBU_API:
            try:
                printer = bl.Printer(self.ip, self.access_code, self.serial)
                printer.connect()
                status = printer.get_state()
                printer.disconnect()
                return {"status": "ok", "state": status}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        else:
            return {"status": "unknown", "message": "bambulabs_api not installed"}


def slice_and_print(
    stl_path: str,
    printer_config: dict,
    profile_path: Optional[str] = None
) -> dict:
    """
    Complete workflow: slice STL and send to printer.

    Args:
        stl_path: Path to STL file
        printer_config: Dict with ip, access_code, serial
        profile_path: Optional slicing profile path

    Returns:
        Result dictionary
    """
    # Security: Validate STL path is within allowed directory
    try:
        validated_stl = validate_file_path(stl_path, MAPS_DIR)
    except PrinterError as e:
        return {"status": "security_error", "error": str(e)}

    # Security: Validate profile path if provided
    if profile_path:
        try:
            validate_file_path(profile_path, MAPS_DIR)
        except PrinterError as e:
            return {"status": "security_error", "error": str(e)}

    # Validate file exists and has correct extension
    if not validated_stl.exists():
        return {"status": "error", "error": "STL file not found"}
    if validated_stl.suffix.lower() != '.stl':
        return {"status": "error", "error": "File must be an STL file"}

    printer = BambuPrinter(
        ip=printer_config["ip"],
        access_code=printer_config["access_code"],
        serial=printer_config["serial"]
    )

    # Create temp directory for sliced file
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Slice STL to 3MF
        stl_name = validated_stl.stem
        gcode_path = os.path.join(tmp_dir, f"{stl_name}.gcode.3mf")

        try:
            printer.slice_stl(str(validated_stl), gcode_path, profile_path)
        except PrinterError as e:
            return {"status": "slice_failed", "error": str(e)}

        # Upload to printer
        try:
            remote_path = printer.upload_file(gcode_path)
        except PrinterError as e:
            return {"status": "upload_failed", "error": str(e)}

        # Start print
        try:
            result = printer.start_print(remote_path)
            result["remote_path"] = remote_path
            return result
        except PrinterError as e:
            return {"status": "print_failed", "error": str(e)}


# Default slicing profile for tactile maps
DEFAULT_TACTILE_PROFILE = {
    "layer_height": 0.2,
    "first_layer_height": 0.25,
    "infill_percentage": 15,
    "wall_loops": 3,
    "top_shell_layers": 4,
    "bottom_shell_layers": 3,
    "support_type": "none",
    "brim_type": "auto_brim",
    "print_sequence": "by_layer",
}
