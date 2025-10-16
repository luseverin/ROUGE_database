
import datetime as dt

from attr import validate
from src.data import *
from src.LLM_functions import *
from src.labelling_helpers import filter_reports

## Open and read the JSON file
file_path = DATA_IN_JSONS / "preproc_filtered_report_types_nat_hazards_bugfix_v240925.csv"#'all_ifrc_reports_info_processed_extended_format_nb_std_units.json' "nathaz_ifrc_reports_info_processed.json"
ifrc_reports_df = pd.read_csv(file_path)

# filter reports by report type and date
ifrc_reports_df_filtered = filter_reports(ifrc_reports_df, take_latest=True)

# eventually load labelled reports
labelled_reports = pd.read_csv(DATA_LABELLED / "labelled_reports_impacts_all_v111025.csv")
keys = labelled_reports[['appealCode', 'reportDate']].drop_duplicates()
labelled_reports_raw = ifrc_reports_df.merge(keys, on=['appealCode', 'reportDate'], how='inner')

#eventually select by appeal code
appeals_test = ["MDRYE011"]
test_reports = labelled_reports_raw[labelled_reports_raw.appealCode.isin(appeals_test)]

# select reports to process
nreports = 1
reports_in = labelled_reports_raw#labelled_reports_raw#ifrc_reports_df_filtered.iloc[:nreports] #test_reports
nreports = len(reports_in)


## Parameters
sim_name = "labelled_reports_turnoff_subtype_val"#name of simulation "labelled_reports"
res_savename = f"{sim_name}_{MODEL_NAME.replace('/', '_')}_v{dt.date.today().strftime('%d%m%y')}.csv" #model to be changed in src.client
chunk_size = None #chunk size of input. None to disable
max_rounds = 10 #max number of continuations

#chose hazard and impact cats
hazcat = list(hazard_main_types_emdat_desc.keys())
impmaintype = IMPACT_TYPES
impsubtype_dict = IMPACT_DESCRIPTIONS
impsubtype = IMPACT_SUBTYPES
#Validation
validate_impSubtypes = False
validate_hazards = True #deactivate hazards validation as cause issues

#impunit = impactUnit_list_prompting
#impunittype = impactUnitType_list
#descriptions_impact = format_desc(impact_subtypes_desc_dict)
#descriptions_hazard = format_desc(hazard_main_types_emdat_desc)
#validate_hazards = True #deactivate hazards validation as cause issues
#constr_unit = False #constrain unit or not
#examples = examples_range
#json_scheme = impact_scehem_json_schema(impsubtype, hazcat)

#chose prompt function
#base_prompt = quantify_impacts_all_system_prompt(impsubtype, hazcat)#groq_system_prompt(impsubtype, hazcat)
#text_pos = "above"
#add_examples = True
#add_descriptions = True
#
#if add_descriptions:
#    base_prompt = add_subtype_descriptions_prompt(base_prompt, "impactSubtype", descriptions_impact)
#    base_prompt = add_subtype_descriptions_prompt(base_prompt, "hazards", descriptions_hazard)
#
#if add_examples:
#    base_prompt = add_examples_prompt(base_prompt, examples)

#api parameters
groq_kwargs = {"temperature": 0,
               "seed": 42,
               #"response_format":{
               #    "type": "json_schema",
               #    "json_schema": {
               #        "name" : "impact_extraction",
               #        "schema": json_scheme
               #    }
               #},
               }

## Extraction
#print(add_text_prompt(base_prompt, """\nTEST\nTEXT\n""", text_pos=text_pos))
print(f"Processing {res_savename}")
response, response_df = get_event_impacts_multiprompt(reports_in,
                                                      impact_types_dict=impsubtype_dict,
                                                      hazards_list=hazcat,
                                                      validate_impSubtypes=validate_impSubtypes,
                                                      validate_hazards=validate_hazards,
                                                      chunk_size=chunk_size,
                                                      max_rounds=max_rounds,
                                                      res_savename=res_savename,
                                                      **groq_kwargs)