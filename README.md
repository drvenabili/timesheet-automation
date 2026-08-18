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
    Copy the example file and fill in your details:
    ```bash
    cp .env.example .env
    ```
    At minimum set your timesheet URL:
    ```
    TIMESHEET_URL=url-of-your-middleman's-timesheet
    ```
    You can also set `TIMESHEET_USER` / `TIMESHEET_PASSWORD` for auto-login, and
    `SHEET_SOURCE_PATH` to point at your source Excel file.

    Optionally, if your account has more than one timesheet box (project), you can
    pin which one to fill by its numeric project ID (the number in
    `projectTimeFormContainer<ID>`):
    ```
    TIMESHEET_PROJECT_ID=1308
    ```
    If unset, the **first** box on the page is used. Run `uv run main.py list-boxes`
    to discover the available IDs.

4.  **Place your Excel sheet**:
    Ensure your Excel timesheet is in the `sheet/` directory.

## Usage

Run the CLI tool using `uv run main.py`.

### List Available Sheets (Months)

Check which months are available in your Excel file:

```bash
uv run main.py list-sheets
```

### List Available Boxes (Projects)

If your account shows more than one timesheet box, discover their project IDs:

```bash
uv run main.py list-boxes
```

This opens the site, logs you in, and prints each box's project ID (marking the
first one as the default). Use an ID with `--project-id` on the `fill` command,
or set `TIMESHEET_PROJECT_ID` in your `.env`.

### Fill Timesheet

Automate the filling for a specific month. You will be prompted to log in manually in the browser window.

```bash
uv run main.py fill "January 2026"
```

To target a specific box (when more than one is present), pass its project ID:

```bash
uv run main.py fill "January 2026" --project-id 1308
```

If `--project-id` is omitted, the tool uses `TIMESHEET_PROJECT_ID` from `.env`, or
falls back to the first box on the page.

By default, the command now copies the source Excel file into `sheet/` (equivalent to `--excelpath`).
If you want to skip that copy step, use:

```bash
uv run main.py fill "January 2026" --no-excelpath
```

The script will:
1.  Read the data from the specified Excel sheet.
2.  Open a browser (auto-selects Chromium first, with fallback support).
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
