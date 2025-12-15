# como_project4
## Instructions
1. Clone the repo, go to branch impact_extraction_multiprompt_clean
2. Install the environment using conda env create -f ifrc_llm_311.yml
3. Run pip install -e . to install src package
4. Run python -m spacy download en_core_web_sm to install spacy model
4. Set-up your paths by changing them in data.py

To reproduce the analysis, run the scripts in the following order:
1. preproces_reports.py
2. llm_extraction.py
3. postprocess_results.py

## Content
### src
Source code. Contains:
- accuracy.py : Accuracy calculation functions
- classOutput.py : Validation classes for LLM extraction
- client.py : OpenAI, Groq API and OpenStreetMap client set-up
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
- prompt_hazards.py : 
- prompt_impact.py : Prompt function to extract impacts
- sanity_checks.py : Postprocessing check of extracted impact
- text_processing_functions.py : text processing and pre-processing functions
- units.py : Definition of units per impact classes and categories
- utils.py : Usefull functions for navigation the data

### scripts
- preproces_reports.py : script to pre-process raw reports (formating, text selection)
- llm_extraction.py : script to extract data using LLMs
- postprocess_results.py : script to post-process extracted and labelled data (reclassification, standardization, geocoding)

