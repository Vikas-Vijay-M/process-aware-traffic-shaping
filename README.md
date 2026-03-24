# NTS Project

This project is a network utility.

## Installation (Windows 11 x64)

1.  **Run PowerShell as Administrator:**
    Open the Start Menu, search for "PowerShell", right-click it, and select "Run as administrator".

2.  **Create a Virtual Environment:**
    Navigate to the project directory and create a virtual environment.
    ```powershell
    cd path\\to\\your\\project
    python -m venv .venv
    ```

3.  **Activate the Virtual Environment and Install Requirements:**
    ```powershell
    .venv\\Scripts\\Activate.ps1
    pip install -r requirements.txt
    ```

4.  **Install WinDivert:**
    This application requires WinDivert for network packet interception. The binaries are **not** included in this repository.
    - Download the latest `WinDivert-2.2.2-A-x64.zip` (or newer) from the [official website](https://reqrypt.org/windivert.html).
    - Create a directory named `windivert` in the root of this project.
    - Extract the contents of the zip file and place `WinDivert.dll` and `WinDivert64.sys` into the `./windivert/` directory. The application will load them from this local path first.
    
    Your project structure should look like this:
    ```
    /
    |-- nts/
    |-- windivert/
    |   |-- WinDivert.dll
    |   `-- WinDivert64.sys
    |-- README.md
    ...
    ```

5.  **Verify Administrator Privileges:**
    You can check if your shell has administrator privileges by running:
    ```powershell
    net session
    ```
    If it returns an error, you are not running as an administrator.

## Usage

### Ctypes Passthrough Mode (Recommended)
This mode uses `ctypes` for high-performance packet capture and reinjection. It is the recommended mode for most use cases.
```bash
# Must be run as Administrator
python -m nts.main --mode ctypes-passthrough --filter "outbound and tcp.DstPort == 443"
```

### Legacy Pydivert Passthrough Mode
This mode uses the `pydivert` library. It is simpler but may have lower performance.
```bash
# Must be run as Administrator
python -m nts.main --mode passthrough --filter "outbound and tcp.DstPort == 443"
```

### Smoke Tests
To verify that the WinDivert driver is installed and accessible.
```bash
# Must be run as Administrator
python -m nts.main --mode windivert-smoke
python -m nts.main --mode ctypes-smoke
```

### Dry Run (No Administrator Privileges Required)
To test the application's logging and stats features without performing any network operations.
```bash
python -m nts.main --mode dry-run
```

### Help
```bash
python -m nts.main --help
```
