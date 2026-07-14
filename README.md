# ROUGE
**A database of disaster impacts in the Global South using Red Cross reports and Large Language Models**

Laura Hasbini<sup>1,2\*</sup>, Luca G. Severino<sup>3,4\*</sup>, Mariana Madruga de Brito<sup>5</sup>, Gabriela Gesualdo<sup>6</sup>, Ana Maria Rotaru<sup>7</sup>, David N. Bresch<sup>3,4</sup>,Evelyn Mühlhofer<sup>4</sup>, Jingxian Wang<sup>8,9</sup>  and Taís Maria Nunes Carvalho<sup>5,10</sup>

<sup>1</sup> Laboratoire des Sciences du Climat et de l’Environnement, UMR 8212CEA-CNRS-UVSQ,
Université Paris-Saclay, Gif-sur-Yvette, France.
<sup>2</sup> Generali France SAS, 93210, Saint Denis, France.
<sup>3</sup> Institute for Environmental Decisions, ETH Zurich, Universitätstr. 22, 8092 Zurich, Switzerland.
<sup>4</sup> Federal Office of Meteorology and Climatology MeteoSwiss, Operation Center 1, P.O. Box 257, 8058 Zurich-Airport, Switzerland.
<sup>5</sup>  Helmholtz-Centre for Environmental Research, Department of Urban and Environmental Sociology, Leipzig, Germany.
<sup>6</sup> Department of Geosciences, The Pennsylvania State University, University Park, PA, USA.
<sup>7</sup> Department of Civil and Environmental Engineering, Politecnico di Milano, Milan, Italy.
<sup>8</sup> University School for Advanced Studies IUSS Pavia, Pavia, Italy.
<sup>9</sup> Department of Electronics, Information and Bioengineering, Politecnico di Milano, Milan, Italy.
<sup>10</sup>  Center for Scalable Data Analytics and Artificial Intelligence (ScaDS.AI), Universität Leipzig, Leipzig, Germany.

\* corresponding authors: laura.hasbini@lsce.ipsl.fr, luca.severino@usys.ethz.ch

## Abstract
High quality data on natural hazard damages are crucial for effective disaster risk management. Yet, existing impact datasets remain limited and often biased toward Northern countries and monetary losses. To help address these gaps, we present ROUGE (Redcross Operations Unified Global Emergency database); a new socio-economic impact database obtained using textual operational reports from the International Federation of Red Cross and Red Crescent Societies (IFRC). These reports are systematically collected and provide broad coverage of regions that are commonly underrepresented in existing impact datasets. Using large language models (LLM), we extract qualitative and quantitative information on a wide range of non-monetary impacts at national and sub-national scales. The resulting dataset documents socio-economic impacts of natural hazards on the population, infrastructure and economy with a spatial detail reaching the subregional level. This resource is designed to support research and applications that require geographically explicit information on socio-economic impacts of disasters, enabling more precise and inclusive analyses of socio-economic consequences of natural hazards worldwide.

---
## Data references
### Input data
|       Dataset       |               Description                    |               Reference/DOI          |
|:-------------------:|:--------------------------------------------:|:--------------------------------:|
|TBD|TBD|[![DOI]()]()|

## Output data
|       Dataset       |              Description                    |           Repository Link        |                   DOI                   |
|:-------------------:|:-------------------------------------------:|:--------------------------------:|:---------------------------------------:|
|TBD|TBD|[Link]()|[![DOI]()]()|

## Reproduce our experiment

### Requirements

| Requirement | Notes |
|------------|-------|
| Python | Version 3.11 |
| Conda | Used for environment management |
| LLM API access | As defined in `client.py` |
| Internet connection | Required for models and external data |

---
### 1. Clone the repository
    
    git clone https://github.com/luseverin/ROUGE_database
    cd ROUGE_database
    git checkout impact_extraction_multiprompt_clean

### 2. Create the conda environment
   
    conda env create -f ifrc_llm_311.yml
    conda activate ifrc_llm_311
  
### 3. Install the source package
  
    pip install -e .
   
### 4. Install required language models
   
    python -m spacy download en_core_web_sm

### 5. Configure local paths
  Set up all local paths by editing `data.py.`


### Core pipeline execution
The core pipeline consists of five main steps.

|   Script Name | Description |
|--------:|:--------|
|   1_preproces_reports.py | Pre process raw IFRC reports, formatting and text selection|
|   2_llm_extraction.py | Extract hazards and impacts using LLMs |
|   3_postprocess_results.py | Reclassify, standardize, and geocode extracted impacts|
|   4_subtypes_merger.py | Merge impactSubtypes and drop duplicates |
|   5_final_data_filter.py | Rename, reclassify and add final columns for final database|

## Repository content

### Analysis

Jupyter notebooks used for data inspection, validation, and analysis.

| Notebook | Purpose |
|--------:|:--------|
| `download_external_sources.ipynb` | Download IFRC Monty and IFRCGo data via APIs |
| `gather_label_reports_v2.ipynb` | Gather manually lablled reports into a single file |
| `gather_raw_reports.ipynb` | Gather raw IFRC reports into a single file |
| `inspect_preprocessed_data.ipynb` | Inspect the number of files dropped at each steps of the pre-processing |
| `labelled_extracted_row_matching.ipynb` | Match manually labelled data with LLM extracted results |
| `open_data.ipynb` | User guidelines to open the database from different formats |
| `result_data_overview.ipynb` | Overview plots and summary statistics of extracted impacts |
| `validation_accuracy.ipynb` | Accuracy evaluation of extracted impacts |
| `validation_coverage.ipynb` | Coverage assessment across regions and hazards |
| `validation_external_sources.ipynb` | Comparison with external impact databases |
| `validation_flags.ipynb` | Analysis of the flag and error propagation |
| `validation_sensitivity_analysis.ipynb` | Sensitivity analysis across different LLM models |

---

### src

Source code implementing the ROUGE extraction and post processing pipeline.

| Module | Description |
|------:|:------------|
| `accuracy.py` | Functions to compute accuracy and validation metrics |
| `classOutput.py` | Classes defining standardized LLM extraction outputs |
| `client.py` | API client setup for OpenAI, Groq, and OpenStreetMap |
| `data.py` | Centralized path and directory definitions |
| `external_comparaison.py` | Aggregation and comparison with external datasets |
| `geocoding.py` | End to end geocoding pipeline |
| `geocoding_utils.py` | Utility functions supporting geocoding operations |
| `hazard_def.py` | Definitions of hazard classes and categories |
| `impact_def.py` | Definitions of impact classes and categories |
| `ImpactRegistry.py` | Registry and mapping of impact types |
| `labelling_helpers.py` | Helper functions for manual labelling workflows |
| `LLM_functions/` | Prompt templates and LLM query functions |
| `logger_setup.py` | Logging configuration and utilities |
| `post_processing_functions.py` | Impact post processing and harmonization functions |
| `prompt_examples.py` | Example prompts used for LLM extraction |
| `prompt_hazards.py` | Prompt functions for hazard extraction |
| `prompt_impact.py` | Prompt functions for impact extraction |
| `sanity_checks.py` | Consistency and sanity checks on extracted data |
| `text_processing_functions.py` | Text cleaning and pre processing utilities |
| `units.py` | Unit definitions per impact class and category |
| `utils.py` | General utility and helper functions |
| `visualisation.py` | Colormaps |
