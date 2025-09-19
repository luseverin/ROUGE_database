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
- data.py : path definitions
- client.py : OpenAI and Groq API client set-up
- text_processing_functions.py : text processing and pre-processing functions
- LLM_functions.py : functions related to LLM extraction
- prompts_impacts.py : prompt definition to extract impacts
- impact_def.py : definition of impact classes and categories
- hazard_def.py : definition of hazard classes and categories
- units.py : impact units definition
- classOutput.py : validation classes for LLM extraction
- post_processing_functions.py : post-processing functions
- geocoding.py : geocoding functions
- accuracy.py : accuracy calculation functions
### scripts
- preproces_reports.py : script to pre-process raw reports (formating, text selection)
- llm_extraction.py : script to extract data using LLMs
- postprocess_results.py : script to post-process extracted and labelled data (reclassification, standardization, geocoding)

