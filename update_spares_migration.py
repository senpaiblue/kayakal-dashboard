import os
import shutil
import pandas as pd
from pathlib import Path
import subprocess

def main():
    print("--- 1. Modifying Data/5S Model area.xlsx ---")
    xlsx_path = "Data/5S Model area.xlsx"
    if not os.path.exists(xlsx_path):
        print(f"Error: {xlsx_path} not found. Ensure you are running this in the project root directory.")
        return

    # Load sheet '5S Implementation - Nominat (2)' without header (header=None) to preserve all rows
    df_excel = pd.read_excel(xlsx_path, sheet_name="5S Implementation - Nominat (2)", header=None)
    
    # Check current values at index 50 and 54, column 7
    print(f"Current value at index 50, col 7: {df_excel.iloc[50, 7]}")
    print(f"Current value at index 54, col 7: {df_excel.iloc[54, 7]}")
    
    # Modify values to split the areas
    df_excel.iloc[50, 7] = "CRM-2 Maintanance Area Spares CAL & CGL"
    df_excel.iloc[54, 7] = "CRM-2 Maintanance Area Spares RCL"
    
    # Save back to Excel
    with pd.ExcelWriter(xlsx_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df_excel.to_excel(writer, sheet_name="5S Implementation - Nominat (2)", index=False, header=False)
    print("Excel updated successfully.")

    print("\n--- 2. Modifying Data/5S Model area.csv ---")
    csv_path = "Data/5S Model area.csv"
    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        print(f"Old CSV line 50: {lines[49].strip()}")
        print(f"Old CSV line 54: {lines[53].strip()}")
        
        lines[49] = lines[49].replace(
            "CRM-2 Maintanance Area Spares (CRM2 CAL & CGL)",
            "CRM-2 Maintanance Area Spares CAL & CGL"
        )
        lines[49] = lines[49].replace(
            "CRM-2 Maintanance Area Spares",
            "CRM-2 Maintanance Area Spares CAL & CGL"
        )
        lines[53] = lines[53].replace(
            "CRM-2 Maintanance Area Spares (CRM2 RCL)",
            "CRM-2 Maintanance Area Spares RCL"
        )
        lines[53] = lines[53].replace(
            "CRM-2 Maintanance Area Spares",
            "CRM-2 Maintanance Area Spares RCL"
        )
        
        with open(csv_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("CSV updated successfully.")
    else:
        print(f"Warning: {csv_path} not found.")

    print("\n--- 3. Handling Assets Folders on Disk ---")
    src_dir = Path("assets/5s/CRM-2/CRM-2 Maintanance Area Spares")
    dest_cal_cgl = Path("assets/5s/CRM-2/CRM-2 Maintanance Area Spares CAL & CGL")
    dest_rcl = Path("assets/5s/CRM-2/CRM-2 Maintanance Area Spares RCL")
    
    if src_dir.exists():
        print(f"Duplicating '{src_dir}' content to:")
        print(f"  - '{dest_cal_cgl}'")
        print(f"  - '{dest_rcl}'")
        
        # Copy to CAL & CGL
        if dest_cal_cgl.exists():
            shutil.rmtree(dest_cal_cgl)
        shutil.copytree(src_dir, dest_cal_cgl)
        
        # Copy to RCL
        if dest_rcl.exists():
            shutil.rmtree(dest_rcl)
        shutil.copytree(src_dir, dest_rcl)
        
        # Remove old directory
        shutil.rmtree(src_dir)
        print("Asset folder copy/move completed.")
    else:
        print(f"Warning: Source folder '{src_dir}' does not exist or has already been migrated.")

    print("\n--- 4. Running migrate_5s.py to regenerate DT.xlsx ---")
    if os.path.exists("migrate_5s.py"):
        try:
            subprocess.run(["python3", "migrate_5s.py"], check=True)
            print("Successfully regenerated DT.xlsx.")
        except subprocess.CalledProcessError as e:
            print(f"Error running migrate_5s.py: {e}")
    else:
        print("Warning: migrate_5s.py not found in the current directory.")

if __name__ == "__main__":
    main()
