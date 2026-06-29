from playwright.sync_api import sync_playwright, Page, Error as PlaywrightError
from typing import List, Dict
from datetime import datetime, timedelta
from excel_reader import DayEntry
import time
import os
from rich.console import Console

console = Console()

class WebAutomator:
    def __init__(self, url: str, headless: bool = False, browser: str = "auto"):
        self.url = url
        self.headless = headless
        self.browser = browser.lower()

    def _launch_browser(self, p):
        browser_order = {
            "auto": ["chromium", "firefox", "webkit"],
            "chromium": ["chromium"],
            "firefox": ["firefox"],
            "webkit": ["webkit"],
        }

        order = browser_order.get(self.browser)
        if not order:
            raise ValueError(f"Unsupported browser '{self.browser}'. Use auto/chromium/firefox/webkit.")

        launch_errors = []
        for name in order:
            try:
                if name == "firefox":
                    # Fedora Wayland can segfault Firefox in Playwright; force XWayland when possible.
                    return p.firefox.launch(headless=self.headless, env={"MOZ_ENABLE_WAYLAND": "0"}), name
                if name == "chromium":
                    return p.chromium.launch(headless=self.headless), name
                return p.webkit.launch(headless=self.headless), name
            except PlaywrightError as e:
                launch_errors.append(f"{name}: {e}")

        error_message = "Failed to launch any browser.\n" + "\n\n".join(launch_errors)
        raise RuntimeError(error_message)

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
            browser, browser_name = self._launch_browser(p)
            console.print(f"[blue]Using browser: {browser_name}[/blue]")
            context = browser.new_context()
            page = context.new_page()
            
            console.print(f"[blue]Navigating to {self.url}...[/blue]")
            try:
                page.goto(self.url)
            except Exception as e:
                 console.print(f"[yellow]Could not navigate directly (maybe invalid URL?). Opening empty page.[/yellow]")

            # Auto-login Logic
            username = os.getenv("TIMESHEET_USER")
            password = os.getenv("TIMESHEET_PASSWORD")
            #console.print(f"[blue]{username} --- {password}[/blue]")

            if username and password:
                console.print("[blue]Credentials found (USER/PASSWORD). Attempting auto-login...[/blue]")
                try:
                    # Give page a moment to load inputs
                    page.wait_for_selector("input[type='password']", timeout=3000)
                    
                    if page.locator("input[type='password']").is_visible():
                        # Fill Username - Specific for the provided HTML
                        if page.locator("input[name='_username']").count() > 0:
                            page.fill("input[name='_username']", username)
                        else:
                            # Fallback
                            page.fill("input[type='text']", username)
                            
                        # Fill Password - Specific for the provided HTML
                        if page.locator("input[name='_password']").count() > 0:
                            page.fill("input[name='_password']", password)
                        else:
                            page.fill("input[type='password']", password)
                        
                        # Click Submit
                        if page.locator("button[name='_submit']").count() > 0:
                            page.click("button[name='_submit']")
                        else:
                            page.click("button[type='submit']")
                            
                        console.print("[blue]Credentials submitted.[/blue]")
                        
                        # Check for "Bad credentials" error
                        try:
                            if page.locator(".alert-error:has-text('Bad credentials')").is_visible(timeout=3000):
                                console.print("[red]Login failed: Bad credentials reported by website.[/red]")
                                console.print("[yellow]Please check your .env file or login manually.[/yellow]")
                        except:
                            pass
                            
                except Exception as e:
                    console.print(f"[dim]Auto-login issue: {e}[/dim]")

            console.print("[bold yellow]Waiting for login...[/bold yellow]")
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
                time.sleep(1)
            
            console.print("\n[green]Done processing weeks.[/green]")
            input("Press Enter to close browser...")
            browser.close()
