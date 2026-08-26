import os
import re

files = [
    'Data/Dep_vs_Score_phase2.csv',
    'Data/Zone_vs_Score_phase2.csv'
]

replacements = [
    (re.compile(r'\bBar Mill II\b', re.IGNORECASE), 'BRM 2'),
    (re.compile(r'\bBar Rod Mill I\b', re.IGNORECASE), 'BRM 1'),
    (re.compile(r'\bCold Rolling Mill I\b', re.IGNORECASE), 'CRM 1'),
    (re.compile(r'\bCold Rolling Mill II\b', re.IGNORECASE), 'CRM 2'),
    (re.compile(r'\bHot Strip Mill I\b', re.IGNORECASE), 'HSM 1'),
    (re.compile(r'\bHot Strip Mill II\b', re.IGNORECASE), 'HSM 2'),
    # Use careful boundary for Wire Rod Mill I before II
    (re.compile(r'\bWire Rod Mill II\b', re.IGNORECASE), 'WRM 2'),
    (re.compile(r'\bWire Rod Mill I\b', re.IGNORECASE), 'WRM')
]

for file_path in files:
    try:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content
        for pattern, new_str in replacements:
            new_content = pattern.sub(new_str, new_content)
        
        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Reverted {file_path}")
        else:
            print(f"No changes needed for {file_path}")

    except Exception as e:
        print(f"Error on {file_path}: {e}")
