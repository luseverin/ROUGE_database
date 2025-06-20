#sanity checks for llm extraction
import pandas as pd
import numpy as np

#value in original text
def format_number(num):
    """
    Formats a number into a string, removing unnecessary trailing zeros
    and the decimal point if it's not needed.
    """
    if isinstance(num, float) and num.is_integer():
        # If the number is a float but represents an integer
        return str(int(num))
    return str(num).rstrip('0').rstrip('.') if '.' in str(num) else str(num)
def flag_value_in_text(extract_df):
    """
    Adds a column to the dataframe, "value_in_text", which is
    True if the impactValue is found in the original text and
    False otherwise. If the impactValue is NaN, the value_in_text
    is also NaN.
    """
    def value_in_text(row):
        if np.isnan(row["impactValue"]):
            return np.nan
        else:
            return format_number(row["impactValue"]) in "".join(row["nathaz_text"])
    extract_df["value_in_text"] = extract_df.apply(lambda x: value_in_text(x), axis=1)
    return extract_df

def pop_cntry_check(extracted_data, country_pop):
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
    def check_pop(x):
        year = str(pd.to_datetime(x["reportDate"]).year)
        year_check = year if year in country_pop[country_pop["Country Code"] == x["country_iso3_kw"]].columns else "2023"
        if year != year_check:
            print(f"Warning: year {year} not in population data for {x['country_iso3_kw']}")
        if  x["country_iso3_kw"] not in country_pop["Country Code"].unique():
            print(f"Warning: country {x['country_iso3_kw']} not in population data")
            pop_year = np.nan
        else:
            pop_year = country_pop[country_pop["Country Code"] == x["country_iso3_kw"]][year_check].values[0]
        return x["impactValue"] < pop_year if (x["impactUnit"] == "people" and not np.isnan(x["impactValue"]))  else np.nan
    extracted_data["pop_cntry_check"] = np.nan
    extracted_data["pop_cntry_check"] = extracted_data.apply(check_pop, axis=1)
    return extracted_data

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
