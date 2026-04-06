import datetime as dt
from src.data import *
from src.LLM_functions import *
from src.labelling_helpers import take_longest_report
from src.logger_setup import set_logger

## Open and read the JSON file
file_path = (
    DATA_IN_JSONS
    / "preproc_text_sel_gaps_all_ifrc_reports_info_unnested_with_text_v181125_v050326.csv"
    # preproc_text_sel_nogaps_all_ifrc_reports_info_unnested_with_text_v181125_v050326
)  # "preproc_filtered_report_types_nat_hazards_bugfix_v250925.csv"
ifrc_reports_df = pd.read_csv(file_path)

# filter reports by report type and date
ifrc_reports_df_filtered = take_longest_report(ifrc_reports_df)

# eventually load labelled reports
labelled_reports = pd.read_csv(
    DATA_LABELLED / "labelled_reports_impacts_gaps_v270326.csv"
)
keys = labelled_reports[["appealCode", "reportDate"]].drop_duplicates()
labelled_reports_raw = ifrc_reports_df.merge(
    keys, on=["appealCode", "reportDate"], how="inner"
)

# eventually select by appeal code
appeals_test = [
    "MDRYE011",
    "MDRZM022",
    "MDRSD034",
    "MDRUG050",
    "MDRRW022",
]  # ["MDRYE011","MDRZM022", "MDRSD034", "MDRUG050", "MDRRW022"]
test_reports = labelled_reports_raw[
    labelled_reports_raw.appealCode.isin(appeals_test)
]  # ifrc_reports_df_filtered[ifrc_reports_df_filtered.appealCode.isin(appeals_test)]

# select reports to process
nreports = 350
reports_in = test_reports  # labelled_reports_raw#ifrc_reports_df_filtered.iloc[:nreports] #test_reports
# labelled_reports_raw#ifrc_reports_df_filtered.iloc[:nreports] #test_reports
nreports = len(reports_in)

## Parameters
chunk_size = 1000  # chunk size of input. None to disable
max_rounds = 10  # max number of continuations
sim_name = f"test_reports_gaps_chunksize{chunk_size}"  # all_appeals_unique_1-222"#name of simulation "labelled_reports"
res_savename = f"{sim_name}_{MODEL_NAME.replace('/', '_')}_v{dt.date.today().strftime('%d%m%y')}"  # model to be changed in src.client

# choose hazard and impact cats
hazcat = list(hazard_main_types_emdat_desc.keys())
impmaintype = IMPACT_TYPES
impsubtype_dict = IMPACT_DESCRIPTIONS
impsubtype = IMPACT_SUBTYPES
# Validation
validate_impSubtypes = False
validate_hazards = True  # deactivate hazards validation as cause issues

# api parameters
groq_kwargs = {
    "temperature": 0.0,
    "top_p": 0.01,
    "seed": 42,
    # "response_format":{
    #    "type": "json_schema",
    #    "json_schema": {
    #        "name" : "impact_extraction",
    #        "schema": json_scheme
    #    }
    # },
}

## Extraction
logger_name = "impact_extraction"
log_file = DATA_LOGS / f"LOGS_{logger_name}_{res_savename}.txt"
LOGGER = set_logger(log_file, logger_name=logger_name)
LOGGER.info(f"Processing {res_savename} from {file_path}...")
try:
    response, response_df = get_event_impacts_multiprompt(
        reports_in,
        impact_types_dict=impsubtype_dict,
        hazards_list=hazcat,
        validate_impSubtypes=validate_impSubtypes,
        validate_hazards=validate_hazards,
        chunk_size=chunk_size,
        max_rounds=max_rounds,
        res_savename=res_savename,
        **groq_kwargs,
    )
    LOGGER.info("Extraction completed successfully.")
except Exception as e:
    LOGGER.exception(f"Error while processing {res_savename}: {e}")
