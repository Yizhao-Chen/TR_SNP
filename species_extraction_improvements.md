# Improved Species Name Extraction for ITRDB Metadata

## Issue Summary

When fetching metadata for ITRDB sites (specifically the "in003" site), the code was incorrectly extracting species information from the abstract section of the "-noaa.rwl" file instead of the dedicated species field in the "-rwl-noaa.txt" file.

For example, for site "in003":
- The "-noaa.rwl" file had the text `# Species: in Dendroclimatic Reconstructions: A Case Study Using Juglans nigra in South-Central Indiana, USA.` which was being incorrectly identified as the species name
- The "-rwl-noaa.txt" file correctly had the species name `# Species_Name: Juglans nigra` in a dedicated section

## Changes Made

1. Modified the `process_file` method in `itrdb_global_detailed_metadata.py` to prioritize extracting species information from "-rwl-noaa.txt" files when available
2. Enhanced the validation process to reject species names that:
   - Are too long (over 100 characters)
   - Contain terms likely to indicate they're from an abstract (e.g., "case study", "reconstruction")
3. Added dedicated pattern matching for the standardized Species section format: `#------- # Species # Species_Name: [species]`
4. Implemented a line-by-line fallback method for more precise extraction in complex cases

## Test Results

A test was created to verify the improved extraction logic specifically for the "in003" site:

```
=== Testing in003 species name extraction with local files ===

--- Testing -rwl-noaa.txt file ---
Reading file: test_data\in003-rwl-noaa.txt
Found species name from dedicated Species section: Juglans nigra

--- Testing -noaa.rwl file ---
Reading file: test_data\in003-noaa.rwl
Found potentially invalid species name using pattern 'SPECIES[\s:]+([^\n]+)': in Dendroclimatic Reconstructions: A Case Study Using Juglans nigra in South-Central Indiana, USA.
No valid species name found

=== Results ===
Species from -rwl-noaa.txt: Juglans nigra
Species from -noaa.rwl: None
✅ PASS: Correctly extracted 'Juglans nigra' from -rwl-noaa.txt file
✅ PASS: Correctly rejected invalid species name from -noaa.rwl file
```

## Implementation Details

The improved extraction logic:
1. First checks if a "-rwl-noaa.txt" file is available for a site
2. Attempts to extract the species name from this file first
3. Validates the extracted name to ensure it's legitimate (not abstract text)
4. Falls back to the "-noaa.rwl" file with strict validation if needed
5. Uses a more precise line-by-line approach for complex file formats

This enhancement ensures more accurate species information in the metadata, which is important for scientific analysis and proper species classification in tree-ring research. 