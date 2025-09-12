## Steps
#1. Load reports text from JSON (check it is the correct version, eventually redo scraping ourself)
#2. Filter out unnessecary reports
#3. Clean text
#4. Separate sentences and tokenize
#5. Add hazard category for each report (use Laura's reclassifying)
#6. Add division according to header

import pandas as pd
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import copy as cp
import regex as re
import datetime as dt
from pathlib import Path
from collections import Counter
from src.text_processing_functions import *
from src.data import *
from src.hazard_def import hazard_subtype_kw_searc
from src.text_processing_functions import *
from src.post_process_functions import country_name_to_iso3

## Parameters
id_language = True #identify language and get rid of reports not in english
format_numbers = False
std_units = False
match_above = False #whether to select natural hazard impact text from keywords at the top or from the start of the text
format_report_date = True #incompatible with json
outformat = 'csv' #csv json

## Select data
fname_in = 'filtered_report_types_nat_hazards_bugfix'

fname_out = f'preproc_{fname_in}_v{dt.date.today().strftime("%d%m%y")}'

if format_numbers:
    fname_out = fname_out + '_format_nb'
if std_units:
    fname_out = fname_out + '_std_units'

# Open and read the JSON file
with open(DATA_IN_JSONS / (fname_in + '.json'), 'r') as json_file:
    all_ifrc_reports_info_unnested = json.load(json_file)

not_eng = []
id_lang = 0
filtered_reports = []
filtered_reports_hazonly = []
for report in all_ifrc_reports_info_unnested:
    #Filter unwanted report types
    if report['appealType'] in ['Operations Update', 'DREF Operation', 'DREF Operation Final Report', 'DREF Operation Update']:
        if id_language and "language" not in report.keys():
            report['language'] = detect_language(report['text'])
            id_lang=1
        if report["language"] == 'en':
            report["iso_code"] = country_name_to_iso3(report.get("location"))
            #reformat time
            if format_report_date:
                report["reportDate"] = pd.to_datetime(report["date"], dayfirst=True)#.strftime("%Y-%m-%d")
            else:
                report["reportDate"] = report["date"]
            del report["date"]
            if format_numbers:
                report['text_processed'] = replace_commas_in_numbers(report['text_processed'])
                report['text_processed'] = replace_count_suffixes(report['text_processed'])
                report['text_processed'] = replace_numbers(report['text_processed'])
            if std_units:
                report['text_processed'] = standardize_units(report['text_processed'])
            report['sentences'] = sent_tokenize(report['text_processed'])
            report['nathaz_text'] = select_hazard_description(report['sentences'], match_above=match_above)
            report['hazards_found_kw'] = check_hazard_type_keyword(report['text_processed'], hazard_subtype_kw_searc)
            filtered_reports.append(report)
            if (len(report['hazards_found_kw']) > 0):# and (report['disasterTypeReclassified'] not in disasterType_nathaz)):
                filtered_reports_hazonly.append(report)
        else:
            not_eng.append(report)

print(f"Reports not in English: {[report['appealCode'] for report in not_eng]}")
print(f"Number of reports: {len(filtered_reports)}")
print(f"Number of reports with hazards id with kw search: {len(filtered_reports_hazonly)}")

## Save data
if id_lang:#save file with language info as takes time to process
    with open(DATA_IN_JSONS / (fname_in + '.json'), 'w') as f:
        json.dump(filtered_reports, f, indent=4)
if outformat == 'csv':
    filtered_reports = pd.DataFrame(filtered_reports)
    filtered_reports_hazonly = pd.DataFrame(filtered_reports_hazonly)

    filtered_reports.to_csv(DATA_IN_JSONS / (fname_out + '.csv'), index=False)
    filtered_reports_hazonly.to_csv(DATA_IN_JSONS / ("hazonly_" + fname_out + '.csv'), index=False)

elif outformat == 'json':
    with open(DATA_IN_JSONS / (fname_out + '.json'), 'w') as f:
        json.dump(filtered_reports, f, indent=4)

    with open(DATA_IN_JSONS / ("hazonly_" + fname_out + '.json'), 'w') as f:
        json.dump(filtered_reports_hazonly, f, indent=4)

else:
    raise ValueError("outformat must be 'csv' or 'json'")