import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class DayEntry:
    date: datetime
    status: Optional[str]  # 'w', 'v', 'h', or None/NaN
    reason: Optional[str]

class ExcelReader:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.xl = pd.ExcelFile(file_path)

    def get_sheet_names(self) -> List[str]:
        return self.xl.sheet_names

    def read_month(self, sheet_name: str) -> List[DayEntry]:
        if sheet_name not in self.xl.sheet_names:
            raise ValueError(f"Sheet '{sheet_name}' not found.")

        # Read the sheet, assuming header is at row 12 (0-indexed)
        # We'll read without header first to be safe, then slice
        df = pd.read_excel(self.file_path, sheet_name=sheet_name, header=None)
        
        entries = []
        
        # Iterate over rows. We expect dates in column 1.
        # We start looking from row 13 onwards.
        # Column mapping based on inspection of "January 2026":
        # Col 2: Date
        # Col 3: Status (Normal days)
        # Col 6: Reason (Tasks/Requests)
        
        for index, row in df.iterrows():
            # Skip rows before data starts. We look for a datetime object in col 2
            try:
                date_val = row[2]
            except KeyError:
                continue

            if isinstance(date_val, datetime):
                status = row[3]
                reason = row[6]
                
                # Clean up status
                if pd.isna(status):
                    status = None
                else:
                    status = str(status).strip()
                    
                # Clean up reason
                if pd.isna(reason):
                    reason = None
                else:
                    reason = str(reason).strip()
                
                entry = DayEntry(
                    date=date_val,
                    status=status,
                    reason=reason
                )
                entries.append(entry)
                
        return entries
