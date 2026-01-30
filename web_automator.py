from playwright.sync_api import sync_playwright, Page
from typing import List, Dict
from datetime import datetime, timedelta
from excel_reader import DayEntry
from time import sleep
from rich.console import Console

console = Console()

class WebAutomator:
    def __init__(self, url: str, headless: bool = False):
        self.url = url
        self.headless = headless

    def _get_start_of_week_timestamp(self, date_obj: datetime) -> int:
        """Get the unix timestamp for the Monday of the week for a given date."""
        # Adjust so Monday=0, Sunday=6
        start_of_week = date_obj - timedelta(days=date_obj.weekday())
        return int(start_of_week.timestamp())

    def _group_by_week(self, entries: List[DayEntry]) -> Dict[str, List[DayEntry]]:
        """Group entries by their week (Monday string representation)."""
        weeks = {}
        for entry in entries:
            # ISO calendar week: (year, week_num, weekday)
            year, week, _ = entry.date.isocalendar()
            week_key = f"{year}-W{week}"
            if week_key not in weeks:
                weeks[week_key] = []
            weeks[week_key].append(entry)
        return weeks

    def fill_timesheet(self, entries: List[DayEntry]):
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            
            console.print(f"[blue]Navigating to {self.url}...[/blue]")
            try:
                page.goto(self.url)
            except Exception as e:
                 console.print(f"[yellow]Could not navigate directly (maybe invalid URL?). Opening empty page.[/yellow]")

            console.print("[bold yellow]PLEASE LOGIN MANUALLY.[/bold yellow]")
            console.print("I will wait until I see the 'My Sheet' or the Project container.")
            
            # Wait for the project container from the source code provided
            # id="projectTimeFormContainer1308" - the ID might change, so we look for prefix
            try:
                page.wait_for_selector("div[id^='projectTimeFormContainer']", timeout=300000) # 5 mins to login
            except:
                console.print("[red]Timeout waiting for login. Exiting.[/red]")
                return

            console.print("[green]Login detected![/green]")

            # Extract Project ID
            # We look for an ID like projectTimeFormContainerXXXX
            container = page.locator("div[id^='projectTimeFormContainer']").first
            container_id_str = container.get_attribute("id") 
            project_id = container_id_str.replace("projectTimeFormContainer", "")
            console.print(f"Detected Project ID: [bold]{project_id}[/bold]")

            weeks = self._group_by_week(entries)
            
            for week_key, week_entries in weeks.items():
                first_entry = week_entries[0]
                monday_ts = self._get_start_of_week_timestamp(first_entry.date)
                
                console.print(f"\nProcessing Week: [bold]{week_key}[/bold] (TS: {monday_ts})")
                
                # Navigate to the correct week
                page.evaluate(f"""
                    document.getElementById('project_nav_time_{project_id}').value = '{monday_ts}';
                    fetchProjectTimeForm({project_id});
                """)
                
                # Wait for the table to reload with the correct dates
                # We use the date of the first entry in our list for this week to verify loading
                # (Note: Entry might not be Monday, but it should be in the table)
                
                days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

                # Helper to format date as it appears on the website: "Mon 26/01/2026"
                def format_date_web(d: datetime) -> str:
                    day_name = days[d.weekday()]
                    return f"{day_name} {d.strftime('%d/%m/%Y')}"

                check_date_str = format_date_web(first_entry.date)
                
                try:
                    # Wait for the row with this date to appear
                    page.wait_for_selector(f"tr:has-text('{check_date_str}')", timeout=10000)
                except Exception:
                    console.print(f"[red]Timeout waiting for data for {check_date_str}. Skipping week.[/red]")
                    continue
                
                console.print("[dim]Form loaded. Filling days...[/dim]")
                
                for entry in week_entries:
                    if not entry.status:
                        continue
                        
                    formatted_date = format_date_web(entry.date)
                    row = page.locator(f"tr:has-text('{formatted_date}')")
                    
                    if row.count() == 0:
                        console.print(f"[yellow]  Row not found for {formatted_date}[/yellow]")
                        continue
                        
                    hours = "0"
                    if entry.status.lower() == 'w':
                        hours = "8"
                    elif entry.status.lower() == 'v':
                        hours = "4"
                    # 'h' remains "0"
                    
                    reason = entry.reason or ""

                    console.print(f"  Filling {formatted_date}: {hours}h - {reason}")

                    # Fill Hours: select class="hour-input"
                    select_input = row.locator("select.hour-input")
                    if select_input.count() > 0 and select_input.is_visible():
                        if not select_input.is_disabled() and not select_input.get_attribute("readonly"):
                             select_input.select_option(value=hours)
                        else:
                             console.print(f"    [dim]Skipping hours (readonly/disabled)[/dim]")

                    # Fill Comment: input name contains 'comment'
                    comment_input = row.locator("input[name*='comment']")
                    if comment_input.count() > 0 and comment_input.is_visible():
                         if not comment_input.is_disabled() and not comment_input.get_attribute("readonly"):
                            comment_input.fill(reason)
                         else:
                            console.print(f"    [dim]Skipping comment (readonly/disabled)[/dim]")
                
                # Save the week
                console.print(f"[blue]Saving week {week_key}...[/blue]")
                page.evaluate(f"saveProjectTime({project_id})")
                
                # Wait for "Time saved" flash message or just a simple timeout to ensure operation completes
                # The JS function reloads the form (fetchProjectTimeForm) on success.
                # We can wait for the network to be idle or just wait a couple of seconds.
                try:
                    page.wait_for_selector("text=Time saved", timeout=5000)
                    console.print("[green]Success: Time saved.[/green]")
                except:
                    console.print("[yellow]Warning: specific 'Time saved' message not detected, but save command sent.[/yellow]")
                
                # Small buffer before next week
                sleep(1)
            
            console.print("\n[green]Done processing weeks.[/green]")
            input("Press Enter to close browser...")
            browser.close()
