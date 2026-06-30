## Steps
# 1. Load reports text from JSON (check it is the correct version, eventually redo scraping ourself)
# 2. Filter out unnessecary reports
# 3. Clean text
# 4. Separate sentences and tokenize
# 5. Add hazard category for each report (use Laura's reclassifying)
# 6. Add division according to header

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
filter_types = [
    "Emergency Appeal",
    "Emergency Appeal Revision",
    "Operations Update",
    "Final Report",
    "DREF Operation",
    "DREF Operation Final Report",
    "DREF Operation Update",
]
filter_names = None  # ["MDR", "DREF"]
filter_types = [ft.lower() for ft in filter_types] if filter_types is not None else None

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
    "summary",
    "the disaster",
    "situation overview",
    "needs (gaps) identified",
]
headers_drop = [
    "coordination and partnerships",
    "operational strategy",
    "red cross red crescent action",
    # "needs (gaps) identified",
    "operational developments",
    "summary of response",
    "summary of the response",
    "the response so far",
    "previous operations",
    "current national society actions",
    "national society actions",
    "summary of measures taken by the national society",
    "detailed operation plan",
    "summary of the current response",
    "summary of current response",
    "Overview of the host National Society and ongoing response",
    "Overview of Operating National Society Response Action",
    "financial status",
    "appeal history",
    "targeting",
    "planned operations",
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
    # "Community Engagement And Accountability",
    # "Any identified gaps/limitations in the assessment"
]
id_language = True  # identify language and get rid of reports not in english
format_numbers = False
std_units = False
match_above = False  # whether to select natural hazard impact text from keywords at the top or from the start of the text
format_report_date = True  # incompatible with json
informat = "csv"  # csv json
outformat = "csv"  # csv json

## Select data
fname_in = "df_with_clean_text_all"  # "all_ifrc_reports_info_unnested_with_text_v181125"  #'filtered_report_types_nat_hazards_bugfix'
fname_metadata_in = "filtered_reports_all_30062026"
fname_out = f'preproc_text_sel_gaps_{fname_in}_v{dt.date.today().strftime("%d%m%y")}'

if format_numbers:
    fname_out = fname_out + "_format_nb"
if std_units:
    fname_out = fname_out + "_std_units"

# set up logger
logger_name = "preprocessing"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{fname_out}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)

## Preprocessing
start_time = time.time()
LOGGER.info("Preprocessing %s...", fname_out)
if filter_types is not None:
    LOGGER.info(
        "Filtering types %s",
        ", ".join(filter_types) if len(filter_types) > 1 else filter_types,
    )
if filter_names is not None:
    LOGGER.info(
        "Filtering names %s",
        ", ".join(filter_names) if len(filter_names) > 1 else filter_names,
    )

LOGGER.info(
    "Filtering headers to keep: %s",
    ", ".join(headers_keep) if len(headers_keep) > 1 else headers_keep,
)
LOGGER.info(
    "Filtering headers to drop: %s",
    ", ".join(headers_drop) if len(headers_drop) > 1 else headers_drop,
)

# Open and read the input file
fname_in_path = Path(fname_in)
if informat in {".csv", ".json"}:
    input_path = DATA_IN_JSONS / fname_in_path
else:
    input_path = DATA_IN_JSONS / f"{fname_in}.{informat}"

if input_path.suffix == ".json":
    with open(input_path, "r") as json_file:
        reports_in = json.load(json_file)
elif input_path.suffix == ".csv":
    text_in = pd.read_csv(input_path, index_col=0)
    text_in = text_in.rename(columns={"clean_text": "text"})
    if fname_metadata_in is not None:
        metadata_in = pd.read_csv(DATA_IN_JSONS / (fname_metadata_in + ".csv"))
        reports_in = pd.merge(text_in, metadata_in, on="uid", how="left").to_dict(
            orient="records"
        )
    else:
        reports_in = text_in.to_dict(orient="records")
else:
    raise ValueError("informat must be 'csv' or 'json'")

not_eng = []
missing_origType = []
removed_reportName = []
removed_appealType = []
removed_no_nathaz = []
removed_no_text = []
filtered_reports = []
filtered_reports_hazonly = []
for report in reports_in:
    # Remove reports with no origType
    if pd.isna(report["origType"]):
        LOGGER.info(
            "Report %s %s has no origType, skipping.",
            report["appealCode"],
            report["date"],
        )
        missing_origType.append(report)
        continue

    # Filter unwanted report
    if filter_names is not None:
        allowed_name = re.search(
            "|".join(filter_names), report["reportName"], re.IGNORECASE
        )  # avoid undesired reports to be processed
    else:
        allowed_name = True
    # filter out unwanted disaster types
    report = reclass_disaster_type(report)

    if not allowed_name:
        removed_reportName.append(report)
        LOGGER.info(
            "Report %s %s has invalid reportName %s, skipping.",
            report["appealCode"],
            report["date"],
            report["reportName"],
        )
        continue
    if filter_types is not None and not report["appealType"].lower() in filter_types:
        removed_appealType.append(report)
        LOGGER.info(
            "Report %s %s has appealType %s, skipping.",
            report["appealCode"],
            report["date"],
            report["appealType"],
        )
        continue
    if not report["naturalHazard"] == 1:
        removed_no_nathaz.append(report)
        LOGGER.info(
            "Report %s %s has no natural hazard, skipping.",
            report["appealCode"],
            report["date"],
        )
        continue
    if id_language and "language" not in report.keys():
        report["language"] = detect_language(report["text"])
    else:
        report["language"] = "unknown"

    if id_language and not report["language"] == "en":
        not_eng.append(report)
        LOGGER.info(
            "Report %s %s is not in English (%s), skipping.",
            report["appealCode"],
            report["date"],
            report["language"],
        )
        continue
    else:
        report["iso_code"] = country_name_to_iso3(report.get("location"))
        # reformat time
        if format_report_date:
            report["reportDate"] = pd.to_datetime(
                report["date"], dayfirst=True
            )  # .strftime("%Y-%m-%d")
        else:
            report["reportDate"] = report["date"]
        del report["date"]
        report["text_processed"] = clean_text(
            report["text"],
            remove_newlines=False,
            remove_numbers=False,
            remove_stopwords=False,
        )
        if format_numbers:
            report["text_processed"] = replace_commas_in_numbers(
                report["text_processed"]
            )
            report["text_processed"] = replace_count_suffixes(report["text_processed"])
            report["text_processed"] = replace_numbers(report["text_processed"])
        # if std_units:
        #    report['text_processed'] = text_standardize_metric_units(report['text_processed'])
        report = select_impact_description(report, headers_keep, headers_drop)
        if not len(report["nathaz_text"]) > 0:
            LOGGER.info(
                "Report %s %s has no natural hazard impact text, skipping.",
                report["appealCode"],
                report["reportDate"],
            )
            removed_no_text.append(report)
            continue
        report["nathaz_text"] = sent_tokenize(report["nathaz_text"])
        report["nathaz_text"] = remove_newlines(report["nathaz_text"])
        report["hazards_found_kw"] = check_hazard_type_keyword(
            report["text_processed"], hazard_kw_reclass
        )
        filtered_reports.append(report)
        if (
            len(report["hazards_found_kw"]) > 0
        ):  # and (report['disasterTypeReclassified'] not in disasterType_nathaz)):
            filtered_reports_hazonly.append(report)

end_time = time.time()
dropped_reports = (
    missing_origType
    + removed_reportName
    + removed_appealType
    + removed_no_nathaz
    + not_eng
    + removed_no_text
)
LOGGER.info("Total preprocessing time %.2f seconds", end_time - start_time)
LOGGER.info("Number of reports: %i", len(filtered_reports))
LOGGER.info("Number of reports dropped: %i", len(dropped_reports))
LOGGER.info(
    "Number of reports with hazards id with kw search: %i",
    len(filtered_reports_hazonly),
)
LOGGER.info(
    "%i reports with missing origType: %s",
    len(missing_origType),
    [report["appealCode"] for report in missing_origType],
)
LOGGER.info(
    "%i reports with removed reportName: %s",
    len(removed_reportName),
    [report["appealCode"] for report in removed_reportName],
)
LOGGER.info(
    "%i reports with removed appealType: %s",
    len(removed_appealType),
    [report["appealCode"] for report in removed_appealType],
)
LOGGER.info(
    "%i reports with no natural hazard identified: %s",
    len(removed_no_nathaz),
    [report["appealCode"] for report in removed_no_nathaz],
)
LOGGER.info(
    "%i reports not in English: %s",
    len(not_eng),
    [report["appealCode"] for report in not_eng],
)
LOGGER.info(
    "%i reports with no natural hazard impact text: %s",
    len(removed_no_text),
    [report["appealCode"] for report in removed_no_text],
)

## Save data
if outformat == "csv":
    filtered_reports = pd.DataFrame(filtered_reports)
    filtered_reports_hazonly = pd.DataFrame(filtered_reports_hazonly)
    dropped_reports = pd.DataFrame(dropped_reports)

    filtered_reports.to_csv(DATA_IN_JSONS / (fname_out + ".csv"), index=False)
    filtered_reports_hazonly.to_csv(
        DATA_IN_JSONS / ("hazonly_" + fname_out + ".csv"), index=False
    )
    dropped_reports.to_csv(
        DATA_IN_JSONS / ("dropped_" + fname_out + ".csv"), index=False
    )

elif outformat == "json":
    with open(DATA_IN_JSONS / (fname_out + ".json"), "w") as f:
        json.dump(filtered_reports, f, indent=4)

    with open(DATA_IN_JSONS / ("hazonly_" + fname_out + ".json"), "w") as f:
        json.dump(filtered_reports_hazonly, f, indent=4)

    with open(DATA_IN_JSONS / ("dropped_" + fname_out + ".json"), "w") as f:
        json.dump(dropped_reports, f, indent=4)

else:
    LOGGER.error("outformat must be 'csv' or 'json'")
