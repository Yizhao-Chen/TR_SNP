import pandas as pd
import re
import os

# Read the existing species mapper code
existing_codes = {}
with open('species_mapper.py', 'r', encoding='utf-8') as f:
    for line in f:
        if "'" in line and ':' in line and '#' in line:
            match = re.search(r"'([^']+)':\s*'([^']+)'", line)
            if match:
                code = match.group(1)
                name = match.group(2)
                existing_codes[code] = name

print(f"Found {len(existing_codes)} existing species codes in species_mapper.py")

# Read the global metadata
df = pd.read_csv('metadata/global_detailed_metadata.csv')
species_data = df[['tree_species_code', 'species_name']].dropna().drop_duplicates()

print(f"Found {len(species_data)} unique species code entries in the metadata")

# Process each entry
new_codes = {}
for _, row in species_data.iterrows():
    code = row['tree_species_code']
    full_name = row['species_name']
    
    # Skip if code is already in our existing map
    if code in existing_codes:
        continue
    
    # Extract the first two words as the species name
    if isinstance(full_name, str) and len(full_name.strip()) > 0:
        # Clean up the species name
        words = re.sub(r'[^\w\s\.\-]', '', full_name).split()
        if len(words) >= 2:
            species_name = ' '.join(words[:2])
            new_codes[code] = species_name

print(f"Found {len(new_codes)} new species codes to add")

# Output the code to be added to species_mapper.py
print("\n# New species codes to add to SPECIES_CODE_MAP:")
for code, name in sorted(new_codes.items()):
    print(f"    '{code}': '{name}',")

# Save the results to a file for reference
with open('new_species_codes.txt', 'w', encoding='utf-8') as f:
    f.write("# New species codes to add to SPECIES_CODE_MAP:\n")
    for code, name in sorted(new_codes.items()):
        f.write(f"    '{code}': '{name}',\n")

print("\nNew species codes saved to new_species_codes.txt") 