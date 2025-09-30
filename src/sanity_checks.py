#sanity checks for llm extraction
import pandas as pd
import numpy as np
from src.text_processing_functions import replace_commas_in_numbers, replace_count_suffixes, replace_numbers, format_number
#value in original text
def flag_value_in_text(row):
    """
    Adds a column to the dataframe, "value_in_text", which is
    True if the impactValue is found in the original text and
    False otherwise. If the impactValue is NaN, the value_in_text
    is also NaN.
    """

    if np.isnan(row["impactValue"]):
        return np.nan
    else:
        text = "".join(row["nathaz_text"])
        text = replace_commas_in_numbers(text)
        text = replace_count_suffixes(text)
        text = replace_numbers(text)
    return format_number(row["impactValue"]) not in text

def pop_cntry_check(x, country_pop):
    """
    Adds a column to the dataframe, "pop_cntry_check", which is
    True if the impactValue is less than the population of the country
    for the report year, and False otherwise. If the impactValue is NaN,
    the value_in_text is also NaN. If the report year is not in the
    population data, the value for 2023 is used.

    Parameters
    ----------
    extracted_data : pandas.DataFrame
        The dataframe containing the extracted data
    country_pop : pandas.DataFrame
        The dataframe containing the population for each country

    Returns
    -------
    pandas.DataFrame
        The dataframe with the added column
    """
    if not x["impactUnit"] == "people" or pd.isna(x[["impactValue", "impactValueMax", "impactValueMin"]]).values.all():
        return np.nan
    year = str(pd.to_datetime(x["reportDate"]).year)
    year_check = year if year in country_pop[country_pop["Country Code"] == x["country_iso3_kw"]].columns else None
    if not year_check:
        years_available = np.array([int(col) for col in country_pop[country_pop["Country Code"] == x["country_iso3_kw"]].columns if col.isnumeric()])
        year_check = str(int(years_available[np.argmin(np.abs(years_available - int(year)))]))
        print(f"Warning: year {year} not in population data for {x['country_iso3_kw']}"
              f"\n Defaulting to year {year_check}")
    if  x["country_iso3_kw"] not in country_pop["Country Code"].unique():
        print(f"Warning: country {x['country_iso3_kw']} not in population data")
        pop_year = np.nan
    else:
        pop_year = country_pop[country_pop["Country Code"] == x["country_iso3_kw"]][year_check].values[0]
    flag_pop = False
    for impval in x[["impactValue", "impactValueMax", "impactValueMin"]].values:
        if impval > pop_year:
            flag_pop = True
    return flag_pop

def flag_hazard(extracted_data, hazard_list):
    """
    Adds a column to the dataframe, "haz_check", which is True if any
    of the hazards in the report are not in the original hazard_list, and False
    otherwise.

    Parameters
    ----------
    extracted_data : pandas.DataFrame
        The dataframe containing the extracted data
    hazard_list : list
        The list of hazards to check against

    Returns
    -------
    pandas.DataFrame
        The dataframe with the added column
    """
    def check_haz(x):
        return any(haz not in hazard_list for haz in x["hazards"])
    extracted_data["unknown_haz"] = np.nan
    extracted_data["unknown_haz"] = extracted_data.apply(check_haz, axis=1)
    return extracted_data
