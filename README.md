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
    - Download the latest WinDivert package from the [official website](https://reqrypt.org/windivert.html).
    - Extract the archive.
    - Copy the `WinDivert64.dll` and `WinDivert64.sys` files to a location in your system's PATH, or into the `nts` directory of this project.

5.  **Verify Administrator Privileges:**
    You can check if your shell has administrator privileges by running:
    ```powershell
    net session
    ```
    If it returns an error, you are not running as an administrator.

## Usage

### Dry Run (No Administrator Privileges Required)
To test the application's logging and stats features without performing any network operations, use the `--dry-run` flag.
```bash
python -m nts.main --dry-run
```

### Standard Operation (Administrator Privileges Required)
```bash
python -m nts.main --help
```
