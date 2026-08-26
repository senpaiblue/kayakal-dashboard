import os

files = [
    'Data/opl_pokayoke.csv'
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
        for old_str, new_str in replacements:
            new_content = new_content.replace(old_str, new_str)
        
        if content != new_content:
            with open(file_path, 'w', encoding=used_encoding) as f:
                f.write(new_content)
            print(f"Updated {file_path} (encoding: {used_encoding})")
        else:
            print(f"No changes needed for {file_path}")

    except Exception as e:
        print(f"Error on {file_path}: {e}")
