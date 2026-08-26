import os
import re

files = [
    'Data/Dep_vs_Score_phase2.csv',
    'Data/schedule.csv',
    'Data/projects_data.csv',
    'Data/KZ_REPORT.csv',
    'Data/opl_pokayoke.csv',
    'Data/j1_data.csv',
    'Data/pending_approvals.csv',
    'Data/area_master.csv',
    'Data/execution_team.csv'
]

replacements = [
    (re.compile(r'\bhsm i\b', re.IGNORECASE), 'Hot Strip Mill I'),
    (re.compile(r'\bhsm 1\b', re.IGNORECASE), 'Hot Strip Mill I'),
    (re.compile(r'\bhsm1\b', re.IGNORECASE), 'Hot Strip Mill I')
]

for file_path in files:
    try:
        if not os.path.exists(file_path):
            continue
            
        encodings_to_try = ['utf-8', 'latin1']
        content = None
        used_encoding = None
        
        for enc in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                used_encoding = enc
                break
            except UnicodeDecodeError:
                pass
                
        if content is None:
            print(f"Could not read {file_path} with any encoding")
            continue

        new_content = content
        for pattern, new_str in replacements:
            new_content = pattern.sub(new_str, new_content)
        
        if content != new_content:
            with open(file_path, 'w', encoding=used_encoding) as f:
                f.write(new_content)
            print(f"Updated {file_path} (encoding: {used_encoding})")
        else:
            print(f"No changes needed for {file_path}")

    except Exception as e:
        print(f"Error on {file_path}: {e}")
