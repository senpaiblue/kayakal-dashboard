import pandas as pd
import numpy as np
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
MONTHLY_CSV = DATA_DIR / "dwm_monthly.csv"
DAILY_CSV = DATA_DIR / "dwm_daily.csv"

def normalize_kpi_name(name):
    if not name:
        return ""
    import re
    return re.sub(r'[^a-z0-9]', '', str(name).lower())

def parse_dwm_excel(file_path):
    """
    Parses a DWM Excel file (.xlsm or .xlsx).
    Extracts monthly records from MASTER DATA and daily records from KPI sheets.
    """
    filename = os.path.basename(file_path)
    
    # Infer default department from filename
    dept_name = "Coke Ovens"
    if "CO3" in filename or "CO4" in filename:
        dept_name = "Coke Ovens"
    else:
        # e.g., "Blast Furnace DWM.xlsm" -> "Blast"
        dept_name = filename.split()[0]
        
    xl = pd.ExcelFile(file_path)
    sheet_names = xl.sheet_names
    
    # --- 0. Pre-scan KPI sheets for section/sub-section mapping ---
    kpi_sheets = [s for s in sheet_names if s not in ["MASTER DATA", "Update", "Attendance"]]
    kpi_meta_map = {}
    
    for sheet in kpi_sheets:
        try:
            df_sheet = xl.parse(sheet, header=None)
            kpi_name_sheet = None
            section_sheet = ""
            sub_section_sheet = ""
            
            # Scan top rows for metadata
            for r in range(min(15, len(df_sheet))):
                for c in [0, 1]:
                    if c >= len(df_sheet.columns):
                        continue
                    cell = df_sheet.iloc[r, c]
                    if pd.isna(cell):
                        continue
                    cell_str = str(cell).strip()
                    
                    if any(x in cell_str for x in ["Checking KPI", "Managing KPI", "Checking Point", "Managing Point", "KPI"]):
                        if len(df_sheet.columns) > 6 and pd.notna(df_sheet.iloc[r, 6]):
                            kpi_name_sheet = str(df_sheet.iloc[r, 6]).strip()
                            
                for c in range(len(df_sheet.columns)):
                    cell = df_sheet.iloc[r, c]
                    if pd.isna(cell):
                        continue
                    cell_str = str(cell).strip()
                    
                    if "Sub-Section:" in cell_str:
                        sub_section_sheet = cell_str.split("Sub-Section:", 1)[1].strip()
                    elif "Section:" in cell_str:
                        section_sheet = cell_str.split("Section:", 1)[1].strip()
            
            if not kpi_name_sheet:
                kpi_name_sheet = sheet
                
            norm_name = normalize_kpi_name(kpi_name_sheet)
            norm_sheet = normalize_kpi_name(sheet)
            kpi_meta_map[norm_name] = (section_sheet, sub_section_sheet)
            kpi_meta_map[norm_sheet] = (section_sheet, sub_section_sheet)
        except Exception as e:
            print(f"Error pre-scanning sheet {sheet} in {filename}: {e}")

    # --- 1. Parse MASTER DATA (Monthly) ---
    monthly_data = []
    if "MASTER DATA" in sheet_names:
        df_master = xl.parse("MASTER DATA")
        
        # Locate columns that are dates
        date_cols = []
        for col in df_master.columns:
            if isinstance(col, (datetime, pd.Timestamp)):
                date_cols.append(col)
            else:
                try:
                    dt = pd.to_datetime(col)
                    if not pd.isna(dt):
                        date_cols.append(col)
                except:
                    pass
                    
        current_kpi = None
        current_uom = None
        for idx, row in df_master.iterrows():
            kpi_val = row.iloc[1]
            uom_val = row.iloc[2]
            type_val = row.iloc[3] # Plan or Actual
            
            if pd.notna(kpi_val):
                current_kpi = str(kpi_val).strip()
                current_uom = str(uom_val).strip() if pd.notna(uom_val) else ""
                
            if pd.notna(type_val) and type_val in ["Plan", "Actual"] and current_kpi:
                norm_current_kpi = normalize_kpi_name(current_kpi)
                sect = ""
                sub_sect = ""
                if norm_current_kpi in kpi_meta_map:
                    sect, sub_sect = kpi_meta_map[norm_current_kpi]
                    
                for dt_col in date_cols:
                    val = row[dt_col]
                    if pd.notna(val):
                        if isinstance(dt_col, (datetime, pd.Timestamp)):
                            dt_str = dt_col.strftime("%Y-%m-%d")
                        else:
                            dt_str = pd.to_datetime(dt_col).strftime("%Y-%m-%d")
                            
                        try:
                            val_float = float(val)
                        except:
                            val_float = val
                            
                        monthly_data.append({
                            "source_file": filename,
                            "department": dept_name,
                            "section": sect,
                            "sub_section": sub_sect,
                            "kpi_name": current_kpi,
                            "uom": current_uom,
                            "type": type_val,
                            "date": dt_str,
                            "value": val_float
                        })
                        
    # --- 2. Parse KPI sheets (Daily) ---
    daily_data = []
    kpi_sheets = [s for s in sheet_names if s not in ["MASTER DATA", "Update", "Attendance"]]
    
    for sheet in kpi_sheets:
        try:
            df = xl.parse(sheet, header=None)
            
            kpi_name = None
            month_year_val = None
            freq = "Daily"
            dept = dept_name
            section = ""
            sub_section = ""
            
            # Scan top rows for metadata
            for r in range(min(15, len(df))):
                for c in [0, 1]:
                    if c >= len(df.columns):
                        continue
                    cell = df.iloc[r, c]
                    if pd.isna(cell):
                        continue
                    cell_str = str(cell).strip()
                    
                    if any(x in cell_str for x in ["Checking KPI", "Managing KPI", "Checking Point", "Managing Point", "KPI"]):
                        if len(df.columns) > 6 and pd.notna(df.iloc[r, 6]):
                            kpi_name = str(df.iloc[r, 6]).strip()
                    elif "Month / Year" in cell_str or "Month/Year" in cell_str:
                        if len(df.columns) > 6 and pd.notna(df.iloc[r, 6]):
                            month_year_val = df.iloc[r, 6]
                            
                for c in range(len(df.columns)):
                    cell = df.iloc[r, c]
                    if pd.isna(cell):
                        continue
                    cell_str = str(cell).strip()
                    
                    if "Department:" in cell_str:
                        dept = cell_str.split("Department:", 1)[1].strip()
                    elif "Sub-Section:" in cell_str:
                        sub_section = cell_str.split("Sub-Section:", 1)[1].strip()
                    elif "Section:" in cell_str:
                        section = cell_str.split("Section:", 1)[1].strip()
                    elif "Frequency" in cell_str:
                        if "-" in cell_str:
                            freq = cell_str.split("-", 1)[1].strip()
                        elif ":" in cell_str:
                            freq = cell_str.split(":", 1)[1].strip()
                            
            if not kpi_name:
                kpi_name = sheet
                
            # Parse month_year of the sheet
            target_year = None
            target_month = None
            if isinstance(month_year_val, (datetime, pd.Timestamp)):
                target_year = month_year_val.year
                target_month = month_year_val.month
                my_str = month_year_val.strftime("%Y-%m-%d")
            elif month_year_val:
                try:
                    dt = pd.to_datetime(month_year_val)
                    target_year = dt.year
                    target_month = dt.month
                    my_str = dt.strftime("%Y-%m-%d")
                except:
                    my_str = str(month_year_val)
            else:
                my_str = ""
                
            # Find daily table rows
            date_row_idx = None
            actual_row_idx = None
            plan_row_idx = None
            ucl_row_idx = None
            cl_row_idx = None
            lcl_row_idx = None
            
            for r in range(min(20, len(df))):
                row_val_0 = str(df.iloc[r, 1]).strip().lower() if pd.notna(df.iloc[r, 1]) else ""
                row_val_alt = str(df.iloc[r, 0]).strip().lower() if pd.notna(df.iloc[r, 0]) else ""
                
                label = row_val_0 if row_val_0 else row_val_alt
                
                if "date" == label:
                    date_row_idx = r
                elif "actual" == label:
                    actual_row_idx = r
                elif label in ["plan", "target"]:
                    plan_row_idx = r
                elif "ucl" == label:
                    ucl_row_idx = r
                elif "cl" == label:
                    cl_row_idx = r
                elif "lcl" == label:
                    lcl_row_idx = r
                    
            if date_row_idx is not None:
                date_row = df.iloc[date_row_idx]
                for c_idx in range(1, len(date_row)):
                    dt_val = date_row.iloc[c_idx]
                    if pd.isna(dt_val) or "date" in str(dt_val).lower() or str(dt_val).strip() == "":
                        continue
                        
                    # Parse date
                    dt_parsed = None
                    if isinstance(dt_val, (datetime, pd.Timestamp)):
                        dt_parsed = dt_val
                    else:
                        try:
                            dt_parsed = pd.to_datetime(dt_val)
                        except:
                            continue
                            
                    if dt_parsed is None or pd.isna(dt_parsed):
                        continue
                        
                    # Limit check for year/month
                    if target_year is not None and target_month is not None:
                        if dt_parsed.year != target_year or dt_parsed.month != target_month:
                            continue
                            
                    dt_str = dt_parsed.strftime("%Y-%m-%d")
                    
                    # Extract cell values
                    act_val = df.iloc[actual_row_idx, c_idx] if actual_row_idx is not None else np.nan
                    pl_val = df.iloc[plan_row_idx, c_idx] if plan_row_idx is not None else np.nan
                    ucl_val = df.iloc[ucl_row_idx, c_idx] if ucl_row_idx is not None else np.nan
                    cl_val = df.iloc[cl_row_idx, c_idx] if cl_row_idx is not None else np.nan
                    lcl_val = df.iloc[lcl_row_idx, c_idx] if lcl_row_idx is not None else np.nan
                    
                    def to_float(val):
                        if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nan":
                            return np.nan
                        try:
                            return float(val)
                        except:
                            return val
                            
                    if pd.notna(act_val) or pd.notna(pl_val):
                        daily_data.append({
                            "source_file": filename,
                            "department": dept,
                            "section": section,
                            "sub_section": sub_section,
                            "kpi_name": kpi_name,
                            "sheet_name": sheet,
                            "month_year": my_str,
                            "date": dt_str,
                            "actual": to_float(act_val),
                            "plan": to_float(pl_val),
                            "ucl": to_float(ucl_val),
                            "cl": to_float(cl_val),
                            "lcl": to_float(lcl_val)
                        })
        except Exception as e:
            print(f"Error parsing sheet {sheet} in {filename}: {e}")
            
    return pd.DataFrame(monthly_data), pd.DataFrame(daily_data)

def upsert_dwm_data(new_monthly_df, new_daily_df):
    """
    Upserts DWM data into the consolidated CSV files.
    Ensures newly uploaded data replaces matching keys (keeps last).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Monthly
    if not new_monthly_df.empty:
        if MONTHLY_CSV.exists():
            try:
                existing_monthly = pd.read_csv(MONTHLY_CSV)
                combined_monthly = pd.concat([existing_monthly, new_monthly_df], ignore_index=True)
            except Exception as e:
                print(f"Error reading existing monthly CSV: {e}. Starting fresh.")
                combined_monthly = new_monthly_df
        else:
            combined_monthly = new_monthly_df
            
        # Drop duplicates by matching keys, keeping the newly uploaded values (last)
        combined_monthly = combined_monthly.drop_duplicates(
            subset=["department", "kpi_name", "date", "type"], keep="last"
        )
        combined_monthly.to_csv(MONTHLY_CSV, index=False)
        
    # 2. Daily
    if not new_daily_df.empty:
        if DAILY_CSV.exists():
            try:
                existing_daily = pd.read_csv(DAILY_CSV)
                combined_daily = pd.concat([existing_daily, new_daily_df], ignore_index=True)
            except Exception as e:
                print(f"Error reading existing daily CSV: {e}. Starting fresh.")
                combined_daily = new_daily_df
        else:
            combined_daily = new_daily_df
            
        combined_daily = combined_daily.drop_duplicates(
            subset=["department", "kpi_name", "date"], keep="last"
        )
        combined_daily.to_csv(DAILY_CSV, index=False)

def convert_excel_to_csvs_bg(file_path, department):
    """
    Converts all sheets of the Excel file into individual CSV files
    saved under Data/dwm_uploaded_csvs/{dept_clean}/
    """
    import re
    try:
        dept_clean = re.sub(r'[^a-zA-Z0-9_]', '_', department.strip())
        xl = pd.ExcelFile(file_path)
        
        dept_csv_dir = DATA_DIR / "dwm_uploaded_csvs" / dept_clean
        dept_csv_dir.mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        for sheet_name in xl.sheet_names:
            try:
                df_sheet = xl.parse(sheet_name)
                sheet_clean = re.sub(r'[^a-zA-Z0-9_]', '_', sheet_name)
                csv_path = dept_csv_dir / f"{sheet_clean}.csv"
                df_sheet.to_csv(csv_path, index=False)
                saved_paths.append(str(csv_path))
            except Exception as e:
                print(f"Error converting sheet {sheet_name} to CSV in background: {e}")
        return saved_paths
    except Exception as e:
        print(f"Error in convert_excel_to_csvs_bg: {e}")
        return []

