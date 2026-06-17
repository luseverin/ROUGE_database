# sanity checks for llm extraction
import pandas as pd
import numpy as np
import logging
import regex as re
from src.text_processing_functions import (
    replace_commas_in_numbers,
    replace_count_suffixes,
    replace_numbers,
    format_number,
)
from src.units import RESPONSE_UNITS, STANDARD_UNITS

# set up logger
LOGGER = logging.getLogger("postprocessing")


# value in original text
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


def flag_value_no_unit(x):
    """
    Adds a column to the dataframe, "value_no_unit", which is
    True if the impactValue is not NaN and the impactUnit is NaN,
    and False otherwise. This flag is used to mark values that
    do not have a unit associated with them.

    Parameters
    ----------
    x : pandas.DataFrame
        The dataframe containing the extracted data

    Returns
    -------
    pandas.Series
        A series containing the flag value for each row of the dataframe
    """
    return not np.isnan(x["impactValue"]) and pd.isna(x["impactUnit"])


def pop_cntry_check(x, country_pop, country_col="country_iso3"):
    """
    Checks if the impact value (and/or the impactValueMax and impactValueMin)
    is larger than the population of the country in the given year.

    Parameters
    ----------
    x : pandas.Series
        The dataframe containing the extracted data
    country_pop : pandas.DataFrame
        The dataframe containing the population data
    country_col : str, default "country_iso3"
        The column name in x containing the country iso3 code

    Returns
    -------
    bool
        Whether the impact value (and/or the impactValueMax and impactValueMin)
        is larger than the population of the country in the given year
    """
    flag_pop = False
    if (
        not x["impactUnit"] == "people"
        or pd.isna(x[["impactValue", "impactValueMax", "impactValueMin"]]).values.all()
    ):
        return flag_pop
    year = str(pd.to_datetime(x["reportDate"]).year)
    population = 0
    countries = np.unique(x[country_col])
    for country in countries:
        year_check = (
            year
            if year in country_pop[country_pop["Country Code"] == country].columns
            else None
        )
        if not year_check:
            years_available = np.array(
                [
                    int(col)
                    for col in country_pop[
                        country_pop["Country Code"] == country
                    ].columns
                    if col.isnumeric()
                ]
            )
            year_check = str(
                int(years_available[np.argmin(np.abs(years_available - int(year)))])
            )
            LOGGER.warning(
                "Year %s not in population data for %s" "\n Defaulting to year %s",
                year,
                country,
                year_check,
            )
        if country not in country_pop["Country Code"].unique():
            LOGGER.warning("Country %s not in population data", country)
            pop_year = np.nan
        else:
            pop_year = country_pop[country_pop["Country Code"] == country][
                year_check
            ].values[0]
        population += pop_year
    for impval in x[["impactValue", "impactValueMax", "impactValueMin"]].values:
        if impval > population:
            flag_pop = True
    return flag_pop


def flag_partial_unit(x):
    """
    Adds a column to the dataframe, "flag_partial_unit", which is True if the impactUnit is equal to the unit_type, and False otherwise.

    Parameters
    ----------
    x : pandas.Series
        The dataframe containing the extracted data

    Returns
    -------
    pandas.Series
        The series with the added column
    """
    return x["impactUnit"] == x["unit_type"]


def flag_response_unit(x, response_units=RESPONSE_UNITS):
    """
    Adds a column to the dataframe, "flag_response_unit", which is True if the impactUnit is equal to "responses", and False otherwise.

    Parameters
    ----------
    x : pandas.Series
        The dataframe containing the extracted data
    response_units : str, default RESPONSE_UNITS
        A regex pattern containing the response units to check for

    Returns
    -------
    pandas.Series
        The series with the added column
    """
    return re.search(response_units, x["impactUnit"]) is not None


def flag_unit_nonstd(x, standard_units=STANDARD_UNITS):
    """
    Adds a column to the dataframe, "flag_unit_nonstd", which is True if the impactUnit is not in the list of standard units, and False otherwise.

    Parameters
    ----------
    x : pandas.Series
        The dataframe containing the extracted data

    Returns
    -------
    pandas.Series
        The series with the added column
    """
    std_units_pattern = "|".join([re.escape(unit) for unit in standard_units])
    return re.search(std_units_pattern, x["impactUnit"]) is None


def flag_percent(x):
    """
    Adds a column to the dataframe, "flag_percent", which is True if the impactValue is a percent and the impactSubtype is not "Other Economic Activity & Livelihood Production", and False otherwise.

    Parameters
    ----------
    x : pandas.Series
        The dataframe containing the extracted data

    Returns
    -------
    pandas.Series
        The series with the added column
    """
    return (
        "%" in x["impactUnit"]
    )  # (x["flag_partial_unit"] and x["unit_type"] == "percent" and x["impactSubtype"] != "Other Economic Activity & Livelihood Production")


def flag_missing_date_field(x, date_fields):
    """
    For each date field, check if it's missing (NaN or empty string) and create a flag for it.
    """
    for field in date_fields:
        if pd.isnull(x[field]) or x[field] == "":
            x[field] = np.nan
            x[f"flag_missing_{field}"] = True
        else:
            x[f"flag_missing_{field}"] = False
    return x


def flag_startYear_after_endYear(x):
    """
    Check if startYear is after endYear and create a flag for it.
    """
    x["flag_startYear_after_endYear"] = False
    if not pd.isnull(x["startYear"]) and not pd.isnull(x["endYear"]):
        if x["startYear"] > x["endYear"]:
            x["flag_startYear_after_endYear"] = True
    else:
        x["flag_startYear_after_endYear"] = np.nan
    return x


def flag_inconsistent_year(x, min_year, max_year):
    """
    Check for inconsistencies in year fields and create flags for them. For instance,
    if the year is before min_year or after max_year, or if startYear is after endYear.
    """
    x["flag_inconsistent_year"] = False
    if not pd.isnull(x["startYear"]):
        if min_year is not None and x["startYear"] < min_year:
            x["flag_inconsistent_year"] = True
        if max_year is not None and x["startYear"] > max_year:
            x["flag_inconsistent_year"] = True
    elif not pd.isnull(x["endYear"]):
        if min_year is not None and x["endYear"] < min_year:
            x["flag_inconsistent_year"] = True
        if max_year is not None and x["endYear"] > max_year:
            x["flag_inconsistent_year"] = True
    else:
        x["flag_inconsistent_year"] = np.nan
    return x


def is_month(value):
    """
    Check if a value is a valid month (1-12).
    """
    if pd.isnull(value):
        return np.nan
    try:
        month = int(value)
        return 1 <= month <= 12
    except ValueError:
        return False


def is_day(value):
    """
    Check if a value is a valid day (1-31).
    """
    if pd.isnull(value):
        return np.nan
    try:
        day = int(value)
        return 1 <= day <= 31
    except ValueError:
        return False


def flag_inconsistent_month(x):
    """
    Check if month fields are valid and create flags for them.
    """
    x["flag_inconsistent_month"] = False
    for field in ["startMonth", "endMonth"]:
        if field in x:
            if not pd.isnull(x[field]):
                if not is_month(x[field]):
                    x["flag_inconsistent_month"] = True
            else:
                x["flag_inconsistent_month"] = np.nan
    return x


def flag_inconsistent_day(x):
    """
    Check if day fields are valid and create flags for them.
    """
    x["flag_inconsistent_day"] = False
    for field in ["startDay", "endDay"]:
        if field in x:
            if not pd.isnull(x[field]):
                if not is_day(x[field]):
                    x["flag_inconsistent_day"] = True
            else:
                x["flag_inconsistent_day"] = np.nan
    return x


def flag_hazard_all_unknown(x):
    """
    Adds a column to the dataframe, "flag_hazard_all_unknown", which is True if all
    of the hazards in the report are "Unknown", and False otherwise.

    Parameters
    ----------
    x : pandas.Series
        The series containing the extracted data

    Returns
    -------
    pandas.Series
        The series with the added column
    """

    return all(haz == "Unknown" for haz in x["hazards"])


def flag_remove_cat(x, remove_cats):
    """
    Adds a column to the dataframe, "flag_remove_cat", which is True if the impactSubtype is in the list of categories to remove, and False otherwise.

    Parameters
    ----------
    x : pandas.Series
        The dataframe containing the extracted data
    remove_cats : list
        The list of categories to remove

    Returns
    -------
    pandas.Series
        The series with the added column
    """
    return x["impactSubtype"] in remove_cats


def flag_remove_hazard(x, remove_hazards, strict=False):
    """
    Adds a column to the dataframe, "flag_remove_hazard", which is True if the hazard is in the list of hazards to remove, and False otherwise.

    Parameters
    ----------
    x : pandas.Series
        The dataframe containing the extracted data
    remove_hazards : list
        The list of hazards to remove
    strict : bool, default False
        Whether to use strict matching (any hazard in the list) or not (all hazards in the list)

    Returns
    -------
    pandas.Series
        The series with the added column
    """
    if strict:
        return any(haz in remove_hazards for haz in x["hazards"])
    else:
        return all(haz in remove_hazards for haz in x["hazards"])


def flag_remove_unit(x, remove_units=["children", "women", "male", "female"]):
    """
    Adds a column to the dataframe, "flag_remove_unit", which is True if the impact
    unit contains any of the units in the list of units to remove, and False otherwise.
    Additionally, if the impactSubtype contains "Education" and the impactUnit contains "children", the flag is also set to True.

    Parameters
    ----------
    x : pandas.Series
        The dataframe containing the extracted data
    remove_units : list (optional)
        The list of units to remove (default is ["children", "women", "male", "female"])

    Returns
    -------
    pandas.Series
        The series with the added column
    """
    if re.search(r"Education", x["impactSubtype"]) and "children" in x["impactUnit"]:
        return False
    remove_units_pattern = "|".join([re.escape(unit) for unit in remove_units])
    return re.search(remove_units_pattern, x["impactUnit"]) is not None


def gather_flags(extracted_data, flag_columns, flag_name="any_flag"):
    """
    Gathers all flag columns into a single column "any_flag", which is True if any of the flag columns are True, and False otherwise.

    Parameters
    ----------
    extracted_data : pandas.DataFrame
        The dataframe containing the extracted data
    flag_columns : list
        The list of flag columns to gather
    flag_name : str, default "any_flag"
        The name of the column to store the gathered flags

    Returns
    -------
    pandas.DataFrame
        The dataframe with the added column
    """

    def check_any_flag(x):
        return any(x[flag] for flag in flag_columns if flag in x.index)

    extracted_data[flag_name] = np.nan
    extracted_data[flag_name] = extracted_data.apply(check_any_flag, axis=1)
    # drop individual flag columns
    flags_drop = [flag for flag in flag_columns if flag != flag_name]
    extracted_data = extracted_data.drop(columns=flags_drop)
    return extracted_data
