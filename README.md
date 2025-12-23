# ROUGE :  A database of disaster impacts in the Global South using Red Cross reports and Large Language Models 
## Instructions
1. Clone the repo, go to branch main
2. Install the environment using conda env create -f ifrc_llm_311.yml
3. Run pip install -e . to install src package
4. Run python -m spacy download en_core_web_sm to install spacy model
4. Set-up your paths by changing them in data.py
5. Set-up your API keys by changing them in client.py

To reproduce the analysis, run the scripts according to their numerical order. 

## Content

### Analysis 
List of the following notebooks, for data validation, pre-processing, post-processing, results analysis : 
- download_external_sources.ipynb : Download IFRC Monty and IFRCGo data from API
- labelled_extracted_row_matching.ipynb : Matching of labelled and extracted impact data
- open_data : User guidelines to open the database from different formats
- result_data_overview.ipynb : Plots and overview of extracted impact
- validation_accuracy.ipynb : Accuracy scores for validation
- validation_coverage.ipynb : Coverage scores for validation
- validation_external_sources.ipynb : Comparaison with external sources
- validation_sensitivity_analysis.ipynb : Sensitivity analysis with other LLM models 

### src
Source code. Contains:
- accuracy.py : Accuracy calculation functions
- classOutput.py : Validation classes for LLM extraction
- client.py : OpenAI, Groq API and OpenStreetMap client set-up
- data_format.py : User functions to open the database 
- data.py : Path definitions
- external_comparaison.py : Text processing and aggregation functions (for comparaison with EMDAT, IFRCGo and IFRCMonty external data)
- geocoding.py : Pipeline of geocoding functions
- geocoding_utils.py : Geocoding utils functions 
- hazard_def.py : Definition of hazard classes and categories
- impact_def.py : Definition of impact classes and categories
- ImpactRegistry.py : Class for impact types
- labelling_helpers.py : Helpers functions for manual labelling
- LLM_functions : Prompt and LLM query functions 
- logger_setup.py : Logger setup to track potential errors 
- post_processing_functions.py : Impact post-processing functions
- prompt_examples.py : Examples of prompts for the LLM
- prompt_impact.py : Prompt function to extract impacts
- sanity_checks.py : Postprocessing check of extracted impact
- text_processing_functions.py : text processing and pre-processing functions
- units.py : Definition of units per impact classes and categories
- utils.py : Usefull functions for navigation the data

### scripts
- 1_preproces_reports.py : script to pre-process raw reports (formating, text selection)
- 2_llm_extraction.py : script to extract data using LLMs
- 3_postprocess_results.py : script to post-process extracted and labelled data (reclassification, standardization, geocoding)
- 4_subtypes_merger.py : script to merge the impactSubtypes
- 5_final_data_filter.py : script to clean the database for final usage (Remove unwanted columns, remove duplicates...)

