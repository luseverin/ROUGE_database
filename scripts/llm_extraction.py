import datetime as dt
from operator import mul
from src.data import *
from src.LLM_functions import *
from src.labelling_helpers import take_latest_report, take_longest_report
from src.logger_setup import set_logger

## Open and read the JSON file
# file_path = DATA_IN_JSONS / "preproc_text_sel_gaps_df_with_clean_text_all_v190526.csv"
file_path = DATA_IN_JSONS /"preproc_text_sel_gaps_df_with_clean_text_all_combined_v300626_v060726.csv"
ifrc_reports_df = pd.read_csv(file_path)

# filter reports by report type and date
ifrc_reports_df_filtered = take_latest_report(ifrc_reports_df)

# filter year 
ymin = 2016
ymax = 2025
ifrc_reports_df_filtered["reportYear"] = pd.to_datetime(ifrc_reports_df_filtered["reportDate"], errors="coerce", infer_datetime_format=True).dt.year
ifrc_reports_df_filtered = ifrc_reports_df_filtered.loc[(ifrc_reports_df_filtered["reportYear"]>=ymin) & (ifrc_reports_df_filtered["reportYear"]<=ymax)]

# eventually load labelled reports
# labelled_reports = pd.read_csv(DATA_LABELLED / "labelled_reports_all_v26062026.csv")
labelled_reports = pd.read_csv(DATA_LABELLED / "combined_labelled_reports.csv")
keys = labelled_reports[["appealCode", "reportDate"]].drop_duplicates()
labelled_reports_raw = ifrc_reports_df.merge(
    keys, on=["appealCode", "reportDate"], how="inner"
)

# eventually select by appeal code
# appeals_test = [
#     "MDRKZ010",
#     "MDREC019",
#     "MDRPK018",
#     "MDRPG008",
#     "MDRYE011",
#     "MDRIQ014",
#     "MDRKE058",
#     "MDRNG041",
#     "MDRUG050",
#     "MDRDZ011",
#     "MDRPK026",
#     "MDRCM039",
#     "MDRBJ019",
#     "MDRSD034",
#     "MDRRW022",
#     "MDRMZ024",
#     "MDRCM036",
#     "MDRDZ008",
#     "MDRPH036",
#     "MDRJO003",
#     "MDR55001",
#     "MDRHU005",
#     "MDRLB013",
#     "MDRID013",
#     "MDRVU012",
# ]  # ["MDRYE011","MDRZM022", "MDRSD034", "MDRUG050", "MDRRW022"]
# # test_reports = labelled_reports_raw[
# #    labelled_reports_raw.appealCode.isin(appeals_test)
# # ]
# test_reports = labelled_reports_raw[labelled_reports_raw.appealCode.isin(appeals_test)]

# select reports to process
lreport = 0
rreport = len(ifrc_reports_df_filtered)
reports_in = ifrc_reports_df_filtered.iloc[
   lreport : rreport + 1
]  # labelled_reports_raw#ifrc_reports_df_filtered.iloc[:nreports] #test_reports
# reports_in = test_reports
nreports = len(reports_in)

## Parameters
chunk_size = 1000  # chunk size of input. None to disable
max_rounds = None  # max number of continuations for impact extraction. None to disable
multi_dates = False  # whether to allow multiple date pairs per impact or not (only for qualitative impacts)
sim_name = f"{lreport}-{rreport}_llm_response_preproc_text_sel_gaps_combined_v300626_v060726_{ymin}-{ymax}"#f"test_labelled_reports_1quali_chunksize{chunk_size}_{max_rounds}it"
res_savename = f"{sim_name}_{MODEL_NAME.replace('/', '_')}_v{dt.date.today().strftime('%d%m%y')}"  # model to be changed in src.client

# choose hazard and impact cats
hazcat = list(hazard_main_types_emdat_desc.keys())
impmaintype = IMPACT_TYPES
impsubtype_dict = IMPACT_DESCRIPTIONS
impsubtype = IMPACT_SUBTYPES
# Validation
dedup_impacts = "quali"  # whether to deduplicate impacts or not. If "quali", only deduplicate qualitative impacts, if "all", deduplicate all impacts, if None, do not deduplicate
dedup_fields = [
    "impactSubtype"
]  # fields to use for deduplication. Only used if dedup_impacts is not None.
validate_impSubtypes = True  # whether to validate impact subtypes or not. If True, only keep impacts with valid subtypes according to impsubtype_dict
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
    response, response_df = get_event_impacts(
        reports_in,
        impact_types_dict=impsubtype_dict,
        hazards_list=hazcat,
        validate_impSubtypes=validate_impSubtypes,
        validate_hazards=validate_hazards,
        chunk_size=chunk_size,
        max_rounds=max_rounds,
        res_savename=res_savename,
        dedup_impacts=dedup_impacts,
        dedup_fields=dedup_fields,
        multi_dates=multi_dates,
        **groq_kwargs,
    )
    LOGGER.info(
        "Extraction completed successfully. File saved as %s in %s",
        res_savename,
        DATA_OUT_LLMS,
    )
except Exception as e:
    LOGGER.exception(f"Error while processing {res_savename}: {e}")
