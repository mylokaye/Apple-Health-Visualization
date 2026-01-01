#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Apple Health XML to CSV
==============================
:File: convert.py
:Description: Convert Apple Health "export.xml" file into a csv
:Version: 0.0.2
:Created: 2019-10-04
:Updated: 2023-10-29
:Authors: Jason Meno (jam)
:Dependencies: An export.xml file from Apple Health
:License: BSD-2-Clause
"""

# %% Imports
import os
import pandas as pd
import xml.etree.ElementTree as ET
import datetime as dt
import sys


# %% Function Definitions

def preprocess_to_temp_file(file_path):
    """
    The export.xml file is where all your data is, but Apple Health Export has
    two main problems that make it difficult to parse: 
        1. The DTD markup syntax is exported incorrectly by Apple Health for some data types.
        2. The invisible character \x0b (sometimes rendered as U+000b) likes to destroy trees. Think of the trees!

    Knowing this, we can save the trees and pre-processes the XML data to avoid destruction and ParseErrors.
    """

    print("Pre-processing and writing to temporary file...", end="")
    sys.stdout.flush()

    temp_file_path = "temp_preprocessed_export.xml"
    with open(file_path, 'r', encoding='UTF-8') as infile, open(temp_file_path, 'w', encoding='UTF-8') as outfile:
        skip_dtd = False
        for line in infile:
            if '<!DOCTYPE' in line:
                skip_dtd = True
            if not skip_dtd:
                line = strip_invisible_character(line)
                outfile.write(line)
            if ']>' in line:
                skip_dtd = False

    print("done!")
    return temp_file_path

def strip_invisible_character(line):
    return line.replace("\x0b", "")


def xml_to_csv(file_path):
    """Loops through the element tree, retrieving all objects, and then
    combining them together into a dataframe
    """

    print("Converting XML File to CSV...")
    sys.stdout.flush()

    attribute_list = []
    count = 0
    filtered_count = 0

    # Columns to keep - using a set for faster lookup
    columns_to_keep = {'type', 'unit', 'creationDate', 'startDate', 'endDate', 'value'}

    for event, elem in ET.iterparse(file_path, events=('end',)):
        if event == 'end' and elem.tag == 'Record':
            child_attrib = elem.attrib
            count += 1

            # Filter by year 2025 during parsing - faster string check instead of pandas
            start_date = child_attrib.get('startDate', '')
            if not start_date or not start_date.startswith('2025'):
                elem.clear()
                continue

            # Only keep the columns we need - direct dict comprehension
            filtered_attrib = {k: child_attrib[k] for k in columns_to_keep if k in child_attrib}

            attribute_list.append(filtered_attrib)
            filtered_count += 1

            # Show progress every 10000 records processed
            if count % 10000 == 0:
                print(f"\rProcessed {count:,} records, kept {filtered_count:,} from 2025...", end='', flush=True)

            # Clear the element from memory to avoid excessive memory consumption
            elem.clear()

    print(f"\rProcessed {count:,} records total, kept {filtered_count:,} from 2025.")
    health_df = pd.DataFrame(attribute_list)

    # Every health data type has a long identifer - remove for readability
    if 'type' in health_df.columns and len(health_df) > 0:
        health_df['type'] = health_df['type'].str.replace('HKQuantityTypeIdentifier', "")
        health_df['type'] = health_df['type'].str.replace('HKCategoryTypeIdentifier', "")

    # Sort by newest data first
    if 'startDate' in health_df.columns and len(health_df) > 0:
        health_df.sort_values(by='startDate', ascending=False, inplace=True)

    print("done!")

    return health_df


def save_to_csv(health_df):
    print("Saving CSV file...", end="")
    sys.stdout.flush()

    today = dt.datetime.now().strftime('%Y-%m-%d')
    filename = "apple_health_export_" + today + ".csv"
    health_df.to_csv(filename, index=False)
    print("done!")

    return filename

def remove_temp_file(temp_file_path):
    print("Removing temporary file...", end="")
    os.remove(temp_file_path)
    print("done!")
    
    return

def main():
    file_path = "export.xml"
    temp_file_path = preprocess_to_temp_file(file_path)
    health_df = xml_to_csv(temp_file_path)
    output_file = save_to_csv(health_df)
    remove_temp_file(temp_file_path)

    print("\n" + "="*50)
    print("SUCCESS! Export completed successfully.")
    print(f"Output file: {output_file}")
    print(f"Total records exported: {len(health_df):,}")
    print("="*50)

    return


# %%
if __name__ == '__main__':
    main()
