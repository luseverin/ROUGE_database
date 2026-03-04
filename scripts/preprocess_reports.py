## Steps
#1. Load reports text from JSON (check it is the correct version, eventually redo scraping ourself)
#2. Filter out unnessecary reports
#3. Clean text
#4. Separate sentences and tokenize
#5. Add hazard category for each report (use Laura's reclassifying)
#6. Add division according to header

from venv import logger
import pandas as pd
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import copy as cp
import regex as re
import time
import datetime as dt
from pathlib import Path
from collections import Counter
from src.data import *
from src.hazard_def import hazard_kw_reclass
from src.text_processing_functions import *
from src.post_process_functions import country_name_to_iso3
from src.logger_setup import set_logger

## Parameters
filter_types = ['Emergency Appeal','Emergency Appeal Revision', 'Operations Update', 'Final Report','DREF Operation', 'DREF Operation Final Report', 'DREF Operation Update']
headers_keep = [
        "operation summary",
        "scope and scale",
        "A. situation analysis",
        "description of the crisis",
        "what happened, where and when",
        "what happened, where and when?",
        "description of the emergency",
        "description of the disaster",
        "description of disaster",
        "description of the event",
        "the situation",
        "summary", "the disaster", "situation overview",
        #"needs (gaps) identified",
    ]
headers_drop = [
    "coordination and partnerships", "operational strategy", "red cross red crescent action",
    "needs (gaps) identified",
    "operational developments", "summary of response", "summary of the response","the response so far",
    "previous operations", "current national society actions",
    "national society actions", "summary of measures taken by the national society",
    "detailed operation plan", "summary of the current response", "summary of current response",
    "Overview of the host National Society and ongoing response",
    "Overview of Operating National Society Response Action",
    "financial status", "appeal history", "targeting", "planned operations",
    "IFRC Network Actions Related To The Current Event",
    "ICRC Actions Related To The Current Event",
    "Other Actors Actions Related To The Current Event",
    "Overall objective of the operation",
    "Operation strategy rationale",
    "Targeting Strategy",
    "Who was targeted by this operation?",
    "Explain the selection criteria for the targeted population",
    "Total Targeted Population",
    "Risk and Security Considerations",
    "Please indicate about potential operation risk for this operations and mitigation actions",
    "Please indicate any security and safety concerns for this operation",
    "Implementation",
    "Narrative description of achievements",
    "Lessons Learnt",
    "National Society Strengthening",
    "Financial Report",
    "About Support Services",
    "How many staff and volunteers will be involved in this operation. Briefly describe their role.",
    "If there is procurement, will it be done by National Society or IFRC?",
    "How will this operation be monitored?",
    "Please briefly explain the National Societies communication strategy for this operation",
    #"Community Engagement And Accountability",
    #"Any identified gaps/limitations in the assessment"
]
id_language = False #identify language and get rid of reports not in english
format_numbers = False
std_units = False
match_above = False #whether to select natural hazard impact text from keywords at the top or from the start of the text
format_report_date = True #incompatible with json
outformat = 'csv' #csv json

## Select data
fname_in = "all_ifrc_reports_info_unnested_with_text_v181125"#'filtered_report_types_nat_hazards_bugfix'

fname_out = f'preproc_text_sel_nogaps_{fname_in}_v{dt.date.today().strftime("%d%m%y")}'

if format_numbers:
    fname_out = fname_out + '_format_nb'
if std_units:
    fname_out = fname_out + '_std_units'

#set up logger
logger_name = "preprocessing"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{fname_out}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)

## Preprocessing
start_time = time.time()
LOGGER.info("Preprocessing %s...", fname_out)
LOGGER.info("Filtering types %s", ", ".join(filter_types) if len(filter_types) > 1 else filter_types)
LOGGER.info("Filtering headers to keep: %s", ", ".join(headers_keep) if len(headers_keep) > 1 else headers_keep)
LOGGER.info("Filtering headers to drop: %s", ", ".join(headers_drop) if len(headers_drop) > 1 else headers_drop)

# Open and read the JSON file
with open(DATA_IN_JSONS / (fname_in + '.json'), 'r') as json_file:
    reports_in_json = json.load(json_file)

not_eng = []
filtered_reports = []
filtered_reports_hazonly = []
for report in reports_in_json:
    #Filter unwanted report
    filter_kw =r"|".join(["MDR", "DREF"]+filter_types)
    allowed_orig_type = re.search(filter_kw, report["origType"], re.IGNORECASE)#avoid undesired reports to be processed
    #filter out unwanted disaster types
    report = reclass_disaster_type(report)

    if allowed_orig_type and report['appealType'] in filter_types and report['naturalHazard'] == 1:
        if id_language and "language" not in report.keys():
            report['language'] = detect_language(report['text'])
        else:
            report['language'] = "unknown"
        if report["language"] == 'en' or not id_language:
            report["iso_code"] = country_name_to_iso3(report.get("location"))
            #reformat time
            if format_report_date:
                report["reportDate"] = pd.to_datetime(report["date"], dayfirst=True)#.strftime("%Y-%m-%d")
            else:
                report["reportDate"] = report["date"]
            del report["date"]
            report['text_processed'] = clean_text(report['text'], remove_newlines=False, remove_numbers=False, remove_stopwords=False)
            if format_numbers:
                report['text_processed'] = replace_commas_in_numbers(report['text_processed'])
                report['text_processed'] = replace_count_suffixes(report['text_processed'])
                report['text_processed'] = replace_numbers(report['text_processed'])
            #if std_units:
            #    report['text_processed'] = text_standardize_metric_units(report['text_processed'])
            report = select_impact_description(report, headers_keep, headers_drop)
            report['nathaz_text'] = sent_tokenize(report['nathaz_text'])
            report['nathaz_text'] = remove_newlines(report['nathaz_text'])
            report['hazards_found_kw'] = check_hazard_type_keyword(report['text_processed'], hazard_kw_reclass)
            filtered_reports.append(report)
            if (len(report['hazards_found_kw']) > 0):# and (report['disasterTypeReclassified'] not in disasterType_nathaz)):
                filtered_reports_hazonly.append(report)
        else:
            not_eng.append(report)

end_time = time.time()
LOGGER.info("Total preprocessing time %.2f seconds", end_time - start_time)
LOGGER.info("Reports not in English: %s", [report['appealCode'] for report in not_eng])
LOGGER.info("Number of reports: %i", len(filtered_reports))
LOGGER.info("Number of reports with hazards id with kw search: %i", len(filtered_reports_hazonly))

## Save data
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
    LOGGER.error("outformat must be 'csv' or 'json'")