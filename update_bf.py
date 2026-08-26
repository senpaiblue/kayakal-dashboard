import os

files = [
    'Data/Dep_vs_Score_phase2.csv',
    'Data/schedule.csv',
    'Data/projects_data.csv',
    'Data/KZ_REPORT.csv',
    'Data/opl_pokayoke.csv',
    'Data/j1_data.csv'
]

replacements = [
    # Quoted versions first
    ('"Blast Furnace I & II"', '"Blast Furnace I ,Blast Furnace II"'),
    ('"Blast Furnace-1,2"', '"Blast Furnace I ,Blast Furnace II"'),
    ('"Blast Furnace 1 & 2"', '"Blast Furnace I ,Blast Furnace II"'),
    # Unquoted versions
    (',Blast Furnace I & II,', ',"Blast Furnace I ,Blast Furnace II",'),
    (',Blast Furnace-1,2,', ',"Blast Furnace I ,Blast Furnace II",'),
    (',Blast Furnace 1 & 2,', ',"Blast Furnace I ,Blast Furnace II",'),
    # Unquoted version at end of line (just in case)
    (',Blast Furnace I & II\n', ',"Blast Furnace I ,Blast Furnace II"\n'),
    (',Blast Furnace-1,2\n', ',"Blast Furnace I ,Blast Furnace II"\n'),
    (',Blast Furnace 1 & 2\n', ',"Blast Furnace I ,Blast Furnace II"\n')
]

for file_path in files:
    try:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = content
        for old_str, new_str in replacements:
            new_content = new_content.replace(old_str, new_str)
        
        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {file_path}")
        else:
            print(f"No changes needed for {file_path}")

    except Exception as e:
        print(f"Error on {file_path}: {e}")
