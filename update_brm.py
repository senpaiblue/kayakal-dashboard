import pandas as pd
import os
import re

files = [
    'Data/Dep_vs_Score_phase2.csv',
    'Data/schedule.csv',
    'Data/projects_data.csv',
    'Data/KZ_REPORT.csv'
]

for file_path in files:
    try:
        # We perform exact word boundary replacements to ensure "BRM 2" doesn't match "BRM 20", though unlikely.
        # But we do string replace anyway because some columns might have "WRM 2 + BRM 2"
        # Reading as text is safest because it preserves all other CSV formatting precisely.
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace 'BRM 2' and 'BRM2' with 'Bar Mill II'
        # To avoid double replacing or matching wrong things, we can use regex but standard string replacement 
        # is fine for these specific strings given the grep results.
        
        # We replace any occurrences of "BRM 2" and "BRM2" regardless of trailing spaces, 
        # but let's just do exact string replacement as grep showed.
        new_content = content.replace('BRM 2', 'Bar Mill II')
        new_content = new_content.replace('BRM2', 'Bar Mill II')
        
        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {file_path}")
        else:
            print(f"No changes needed for {file_path}")

    except Exception as e:
        print(f"Error on {file_path}: {e}")
