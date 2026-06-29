import shutil

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from excel_reader import ExcelReader
from web_automator import WebAutomator
import sys
import os
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer()
console = Console()

def get_excel_file() -> Path:
    sheet_dir = Path("sheet")
    files = list(sheet_dir.glob("*.xlsx"))
    if not files:
        console.print("[red]No Excel file found in 'sheet/' directory.[/red]")
        sys.exit(1)
    return files[0]

@app.command()
def list_sheets():
    """List all available sheets (months) in the Excel file."""
    file_path = get_excel_file()
    reader = ExcelReader(file_path)
    sheets = reader.get_sheet_names()
    
    table = Table("Sheet Name")
    for sheet in sheets:
        table.add_row(sheet)
    console.print(table)

@app.command()
def fill(
    month: str = typer.Argument(..., help="The name of the sheet to process (e.g. 'June 2021')"),
    url: str = typer.Option(
        os.getenv("TIMESHEET_URL"), 
        help="The URL of the timesheet website. Defaults to TIMESHEET_URL env var."
    ),
    headless: bool = typer.Option(False, help="Run browser in headless mode"),
    browser: str = typer.Option("auto", help="Browser engine: auto, chromium, firefox, or webkit"),
    excelpath: bool = typer.Option(True, help="Copy the source file into the 'sheet' directory (disable with --no-excelpath)")
):
    """Read a specific month sheet and automate the web filling process."""
    if excelpath:
        source_path = os.getenv("SHEET_SOURCE_PATH")
        if not source_path:
            console.print("[red]SHEET_SOURCE_PATH environment variable not set.[/red]")
        else:
            os.makedirs("sheet", exist_ok=True)
            for file in os.listdir("sheet"):
                file_path = os.path.join("sheet", file)
                os.remove(file_path)
    
            try:
                shutil.copy(source_path, "sheet/")
                console.print(f"[green]File copied to 'sheet/' directory successfully.[/green]")
            except Exception as e:
                console.print(f"[red]Failed to copy file: {e}[/red]")               
                sys.exit(1)

    file_path = get_excel_file()
    reader = ExcelReader(file_path)
    
    try:
        entries = reader.read_month(month)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
        
    if not entries:
        console.print(f"[yellow]No entries found for {month}. Check the sheet format.[/yellow]")
        return

    console.print(f"Found [bold]{len(entries)}[/bold] days in sheet '{month}'")
    
    # Preview data
    table = Table("Date", "Status", "Reason")
    for entry in entries:
        if entry.status: # Only show days with status
            table.add_row(
                str(entry.date.date()), 
                entry.status, 
                entry.reason or ""
            )
    console.print(table)
    
    if typer.confirm("Do you want to proceed with web automation?"):
        automator = WebAutomator(url, headless=headless, browser=browser)
        automator.fill_timesheet(entries)

if __name__ == "__main__":
    app()
