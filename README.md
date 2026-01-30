# Timesheet Automation

Automate the process of filling your monthly timesheets from an Excel file to the online Timeflow portal.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) (Fast Python package installer and resolver)

## Setup

1.  **Install dependencies**:
    ```bash
    uv sync
    ```
    *(Note: `uv run` will automatically install dependencies if they are missing)*

2.  **Install Playwright browsers**:
    ```bash
    uv run playwright install
    ```

3.  **Configure Environment**:
    Create a `.env` file in the root directory and add your timesheet URL:
    ```
    TIMESHEET_URL=url-of-your-middleman's-timesheet
    ```

4.  **Place your Excel sheet**:
    Ensure your Excel timesheet is in the `sheet/` directory.

## Usage

Run the CLI tool using `uv run main.py`.

### List Available Sheets (Months)

Check which months are available in your Excel file:

```bash
uv run main.py list-sheets
```

### Fill Timesheet

Automate the filling for a specific month. You will be prompted to log in manually in the browser window.

```bash
uv run main.py fill "January 2026"
```

The script will:
1.  Read the data from the specified Excel sheet.
2.  Open **Firefox**.
3.  Wait for you to log in manually.
4.  Navigate through the weeks corresponding to the dates.
5.  Fill in hours (Full day = 8h, Half day = 4h) and comments.
6.  **Save each week automatically** and verify success.

## Tech Stack

-   **Python 3.12+**
-   **[uv](https://docs.astral.sh/uv/)**: Dependency management.
-   **[Typer](https://typer.tiangolo.com/)**: CLI app builder.
-   **[Playwright](https://playwright.dev/python/)**: Browser automation.
-   **[Pandas](https://pandas.pydata.org/)**: Excel data processing.
-   **[Rich](https://rich.readthedocs.io/)**: Beautiful terminal output.

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE).

**This means:**
- ✅ Personal use is allowed
- ✅ Non-commercial use is allowed  
- ✅ Use by educational and non-profit organizations is allowed
- ❌ Commercial use (including by companies for their employees) is NOT allowed

For commercial licensing options, please contact the project maintainer.
