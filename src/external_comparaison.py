import pandas as pd
import json
import geopandas as gpd
from collections import Counter
import numpy as np
import ast
from shapely.ops import unary_union
import pandas as pd
import copy as cp
import datetime
from src.LLM_functions import *
from src.data import *
from src.hazard_def import *
from src.impact_def import *
from src.post_process_functions import *

ifrc_go_impact_source = {"report" : "field_reports_",
                         "gov" : "field_reports_gov_",
                         "other" : "field_reports_other_"
                         }

mapping_impact_type = {"Affected People" : {"ifrc_monty" : "affected_total", "ifrc_go" : "num_affected", "emdat" : "Total Affected"},
                       "Injured People" : {"ifrc_monty" : "injured", "ifrc_go" : "num_injured", "emdat" : None},
                       "Displaced People" : {"ifrc_monty" : "displaced_total", "ifrc_go" : "num_displaced", "emdat" : None},
                       "Human Deaths" : {"ifrc_monty" : "death", "ifrc_go" : "num_dead", "emdat" : "Total Deaths"},
                       "Missing People" : {"ifrc_monty" : "missing", "ifrc_go" : "num_missing", "emdat" : None},
                       "Homeless People" : {"ifrc_monty" : None, "ifrc_go" : None, "emdat" : "No. Homeless"}
                       }

### LABELLED AND LLM DATAFRAMES
def consolidate_impact_value(df: pd.DataFrame) -> pd.DataFrame:
    """
    Consolidate quantitative impact values into a single column.

    Combines the columns `impactValue`, `impactValueMin`, and `impactValueMax`
    into a single column `impactValue_final`, using a priority order.
    Rows without any available impact value are removed.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing impact value columns.

    Returns
    -------
    pd.DataFrame
        DataFrame with a consolidated `impactValue_final` column and
        rows with missing values removed.
    """
    df = df.copy()

    # Create consolidated column
    df["impactValue_final"] = (
        df["impactValue"].replace("", pd.NA)
        .combine_first(df["impactValueMin"].replace("", pd.NA))
        .combine_first(df["impactValueMax"].replace("", pd.NA))
    )

    # Drop rows where final value is missing
    df = df.dropna(subset=["impactValue_final"])
    return df

def consolidate_startYear(row):
    """
    Ensure a valid start year for an impact record.

    If `startYear` is missing, the year is inferred from the report date.

    Parameters
    ----------
    row : pd.Series
        Row of a DataFrame containing date information.

    Returns
    -------
    int
        Start year of the impact event.
    """
    # Check if 'startYear' exists in row
    if 'startYear' in row and pd.isna(row['startYear']):
        return pd.to_datetime(row['reportDate']).year
    elif 'startYear' in row:
        return row['startYear']
    else:
        # If column doesn't exist, just return None (or could return reportDate year instead)
        return pd.to_datetime(row['reportDate']).year

def add_location_admin_num(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert administrative level identifiers to numeric values.

    Extracts the numeric administrative level from the
    `locationLowestAdmin` column (e.g. 'ADM_0') and stores it as a float.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing a `locationLowestAdmin` column.

    Returns
    -------
    pd.DataFrame
        DataFrame with an additional `locationLowestAdminNum` column.
    """
    df = df.copy()
    df["locationLowestAdminNum"] = (
        df["locationLowestAdmin"]
        .astype(str)                 # ensure it's string
        .str.extract(r"(\d+)")       # extract digits
        .astype(float)               # convert to number
    )
    return df

def group_quanti_country_level(df: pd.DataFrame, ADM_min=0) -> pd.DataFrame:
    """
    Aggregate quantitative impacts at the country or coarser admin level.

    Groups impact records by appeal and subtype, prioritizing country-level
    reports (ADM 0). If unavailable, subnational data are aggregated based
    on the specified coarser administrative level.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing quantitative impact records.
    ADM_min : int, default=0
        Coarser administrative level allowed for aggregation.

    Returns
    -------
    pd.DataFrame
        Aggregated DataFrame with merged impact values, locations,
        and geometries.
    """
    df_output = []

    for appeal in df["appealCode"].unique():
        df_loop = df[df["appealCode"] == appeal]

        for impactType in df_loop["impactSubtype"].unique():
            df_impact_loop = df_loop[df_loop["impactSubtype"] == impactType]

            # Check for rows at country level
            df_admin_0 = df_impact_loop[df_impact_loop["locationLowestAdminNum"] == 0]
            df_admin_1 = df_impact_loop[df_impact_loop["locationLowestAdminNum"] == 1]
            df_admin_2 = df_impact_loop[df_impact_loop["locationLowestAdminNum"] == 2]
            # df_admin_1_2 = df_impact_loop[df_impact_loop["locationLowestAdminNum"] > 0]

            row = {}
            if not df_admin_0.empty:
                row = {}
                # Sum of impactValue_final
                # row["impactValue_final"] = df_admin_0["impactValue_final"].sum()
                row["impactValue_final"] = df_admin_0["impactValue_final"].max()
                df_admin = df_admin_0

            elif (not df_admin_1.empty) and (ADM_min>=1):
                row["impactValue_final"] = df_admin_1["impactValue_final"].sum()
                df_admin = df_admin_1

            elif (not df_admin_2.empty) and (ADM_min>=2) :
                row["impactValue_final"] = df_admin_2["impactValue_final"].sum()
                df_admin = df_admin_2

            else :
                continue

            # Helper to flatten list-like entries
            def flatten_unique(series):
                values = []
                for v in series.dropna():
                    if isinstance(v, list):
                        values.extend(v)
                    else:
                        values.append(v)
                return "; ".join(pd.Series(values).astype(str).unique())

            # Concatenate / flatten columns
            if "country" in df_admin.columns:
                row["country"] = flatten_unique(df_admin["country"])
            if "location" in df_admin.columns:
                row["location"] = flatten_unique(df_admin["location"])
            if "locationOsm" in df_admin.columns:
                row["locationOsm"] = flatten_unique(df_admin["locationOsm"])
            if "locationGaul" in df_admin.columns:
                row["locationGaul"] = flatten_unique(df_admin["locationGaul"])

            # Union geometries (if geometry column exists)
            if "geometry" in df_admin.columns:
                row["geometry"] = unary_union(df_admin["geometry"].dropna().tolist())

            # Keep other columns same → take first non-null
            for col in df_admin.columns:
                if col not in [
                    "impactValue_final",
                    "country",
                    "location",
                    "locationOsm",
                    "locationGaul",
                    "geometry",
                ]:
                    non_nulls = df_admin[col].dropna()
                    if not non_nulls.empty:
                        row[col] = non_nulls.iloc[0]
            df_output.append(row)

    return pd.DataFrame(df_output)

def clean_group(df_impact, ADM_min=0) :
    """
    Clean and aggregate impact data into a standardized format.

    Applies date normalization, administrative level parsing, value
    consolidation, and spatial aggregation to produce a clean,
    country-level quantitative impact dataset.

    Parameters
    ----------
    df_impact : pd.DataFrame
        Raw impact DataFrame from labelled or LLM-generated outputs.
    ADM_min : int, default=0
        Minimum administrative level allowed for aggregation.

    Returns
    -------
    pd.DataFrame
        Cleaned and aggregated impact DataFrame.
    """
    df_output = df_impact.copy()
    df_output['startYear'] = df_output.apply(consolidate_startYear, axis=1)
    df_output = add_location_admin_num(df_output)
    df_output = consolidate_impact_value(df_output)
    df_output = group_quanti_country_level(df_output, ADM_min=ADM_min)
    return df_output

## IFRC_GO

def clean_impact_values(row):
    """
    Extract and harmonize impact values from IFRC GO source columns.

    Iterates over predefined impact types and data sources to identify
    the first available IFRC GO impact value in a row. The extracted
    value is assigned to the standardized impact type column, and the
    corresponding source is recorded.

    Parameters
    ----------
    row : pd.Series
        Row of the IFRC GO DataFrame containing raw impact value columns.

    Returns
    -------
    pd.Series
        Row with standardized impact values and source annotations.
    """
    for impact_type, mapping in mapping_impact_type.items():
        for impact_source, prefix in ifrc_go_impact_source.items():
            if mapping["ifrc_go"] : 
                col = prefix + mapping["ifrc_go"]
                # check if column exists and has a non-null value
                if col in row and pd.notna(row[col]):
                    row[impact_type] = row[col]
                    row[f"{impact_type} Source"] = impact_source
                    break  # stop once one source is found
    return row

def open_clean_ifrc_go() :
    """
    Load and clean IFRC GO impact data.

    Reads the IFRC GO dataset, harmonizes impact values, standardizes
    column names and types, and filters the data to include only DREF
    reports related to natural disasters.

    Parameters
    ----------
    None

    Returns
    -------
    pd.DataFrame
        Cleaned IFRC GO DataFrame with standardized impact information.
    """
    df_ifrc_go = pd.read_csv(DATA_EXTERNAL_SOURCE / 'ifrc_go_all.csv')

    #Retrieve impact value
    df_ifrc_go = df_ifrc_go.apply(clean_impact_values, axis=1)

    #Rename columns
    df_ifrc_go = df_ifrc_go.rename({"appeals_code" : "appealCode"}, axis=1)
    df_ifrc_go["id"] = df_ifrc_go["id"].astype("Int64")

    #Select only DREF reports 
    df_ifrc_go = df_ifrc_go.loc[df_ifrc_go["appeals_atype_display"]=="DREF"]

    #Select only natural disaster events 
    df_ifrc_go = df_ifrc_go.loc[df_ifrc_go["dtype_name"].isin(hazard_ifrc_go)]

    return df_ifrc_go

## IFRC_MONTY

def open_clean_ifrc_monty(df_ifrc_go) :
    """
    Load and clean IFRC Monty impact data and link it to IFRC GO appeals.

    Reads the IFRC Monty dataset, extracts and matches event identifiers
    to IFRC GO records to recover appeal codes, and harmonizes impact
    type labels using a predefined mapping.

    Parameters
    ----------
    df_ifrc_go : pd.DataFrame
        Cleaned IFRC GO DataFrame containing appeal identifiers.

    Returns
    -------
    pd.DataFrame
        Cleaned IFRC Monty DataFrame with standardized impact types and
        associated appeal codes.
    """
    df_ifrc_monty = pd.read_csv(DATA_EXTERNAL_SOURCE / 'ifrc_monty_all.csv')

    #Use id and df_ifrc_go to fing appealCode
    df_ifrc_monty["id_clean"] = df_ifrc_monty["id"].str.extract(r"ifrcevent-impact--(\d+)-")
    df_ifrc_monty["id_clean"] = df_ifrc_monty["id_clean"].astype("Int64")
    df_ifrc_monty = df_ifrc_monty.merge(
        df_ifrc_go[["id", "appealCode"]].rename(columns={"id": "id_clean"}),
        on="id_clean",
        how="left")

    df_ifrc_monty = df_ifrc_monty.drop(columns=["id_clean"])

    #Rename impact type
    monty_map = {
        mapping["ifrc_monty"]: impact_type
        for impact_type, mapping in mapping_impact_type.items()
        if mapping["ifrc_monty"] is not None
        }

    # Replace values in the column
    df_ifrc_monty["impact_type"] = df_ifrc_monty["impact_type"].replace(monty_map)

    return df_ifrc_monty

## EMDAT 

def open_emdat(file_name='public_emdat_custom_request_2025-08-19.xlsx'):
    """
    Load and preprocess EM-DAT disaster records.

    Reads an EM-DAT Excel extract, filters disasters to the hazards of
    interest, and constructs start and end dates from year, month, and
    day components, filling missing months and days with January 1st.

    Parameters
    ----------
    file_name : str, optional
        Name of the EM-DAT Excel file to load, by default
        'public_emdat_custom_request_2025-08-19.xlsx'.

    Returns
    -------
    pd.DataFrame
        Preprocessed EM-DAT DataFrame with parsed start and end dates.
    """
    #Open EM-DAT
    df_em_dat = pd.read_excel(DATA_EXTERNAL_SOURCE / file_name)
    df_em_dat = df_em_dat.loc[df_em_dat["Disaster Type"].isin(hazard_mapping_emdat.keys())]

    df_em_dat["Start Month"] = df_em_dat["Start Month"].fillna(1).astype("Int64")
    df_em_dat["Start Day"] = df_em_dat["Start Day"].fillna(1).astype("Int64")
    df_em_dat["Start Date"] = pd.to_datetime(
        df_em_dat[["Start Year", "Start Month", "Start Day"]].rename(
            columns={"Start Year": "year", "Start Month": "month", "Start Day": "day"}
        ),
        errors="coerce"
    )

    df_em_dat["End Month"] = df_em_dat["End Month"].fillna(1).astype("Int64")
    df_em_dat["End Day"] = df_em_dat["End Day"].fillna(1).astype("Int64")
    df_em_dat["End Date"] = pd.to_datetime(
        df_em_dat[["End Year", "End Month", "End Day"]].rename(
            columns={"End Year": "year", "End Month": "month", "End Day": "day"}
        ),
        errors="coerce"
    )
    return df_em_dat

def choose_unique_disno(df_llm_em_dat, column_minimize):
    """
    Select a unique EM-DAT disaster number (DisNo.) for a given appeal.

    When multiple EM-DAT events are associated with the same appeal,
    the function selects the DisNo. with the largest number of linked
    impacts. In case of ties, it minimizes the specified distance
    metric (e.g., temporal distance).

    Parameters
    ----------
    df_llm_em_dat : pd.DataFrame
        DataFrame containing candidate EM-DAT matches for a single appeal.
    column_minimize : str
        Column used to minimize the selection criterion (e.g., date
        difference).

    Returns
    -------
    str
        Selected EM-DAT disaster number.
    """
    # Count number of impacts per DisNo
    if df_llm_em_dat["DisNo."].nunique() == 1:
        return df_llm_em_dat["DisNo."].iloc[0]

    # Filter over impact with a Glide number 
    df_llm_em_dat_glide = df_llm_em_dat.copy()

    df_llm_em_dat_filtered = df_llm_em_dat_glide

    # Select the DisNo. with the most numerous number of associated impact 
    counts = df_llm_em_dat_filtered["DisNo."].value_counts()
    max_count = counts.max()
    top_disnos = counts[counts == max_count].index

    #Minimize the distance between start dates
    min_diff = df_llm_em_dat_filtered[df_llm_em_dat_filtered["DisNo."].isin(top_disnos)].groupby("DisNo.", group_keys=False)[column_minimize].min()
    chosen_disno = min_diff.idxmin()
    return chosen_disno

def matching_emdat(df_llm, df_em_dat, date_diff_th, column_minimize) : 
    """
    Match LLM-extracted disaster impacts to EM-DAT events.

    Links LLM-derived disaster reports to EM-DAT records using country
    codes, hazard type harmonization, and temporal proximity. Matching
    is constrained by a maximum allowable date difference threshold and
    resolved to a single EM-DAT disaster number per appeal.

    Parameters
    ----------
    df_llm : pd.DataFrame
        DataFrame containing LLM-extracted disaster and impact information.
    df_em_dat : pd.DataFrame
        Preprocessed EM-DAT disaster DataFrame.
    date_diff_th : datetime.timedelta
        Maximum allowed difference between LLM and EM-DAT start/end dates.
    column_minimize : str
        Column used to select the closest EM-DAT event when multiple
        candidates exist.

    Returns
    -------
    tuple of pd.DataFrame
        - df_matched : LLM DataFrame enriched with matched EM-DAT records.
        - df_llm_em_dat : Intermediate DataFrame containing all candidate
          LLM–EM-DAT matches and distance metrics.
    """
    df1 = cp.deepcopy(df_llm)
    df1_no_split = cp.deepcopy(df_llm)
    df2 = cp.deepcopy(df_em_dat)

    # Map the hazard to emdat type 
    reverse_hazard_mapping_emdat = reverse_mapping(hazard_mapping_emdat) 
    df1["hazards_reclass"] = df1["hazards"].apply(lambda x: reclassify_hazard_emdat(x, reverse_hazard_mapping_emdat)) ## ADD the reverse_haazrd_mapping

    # Explode countries 
    df1 = df1.explode("iso3_code").reset_index(drop=True)

    # Rename and add columns 
    df2 = df2.rename({'ISO' : 'iso_emdat'}, axis=1)

    ## First occurence year
    df_llm_em_dat = df2.merge(
        df1,
        left_on="iso_emdat",
        right_on="iso3_code",
        how="inner"
    )

    ## Keep only rows where Disaster Type is inside hazards list
    df_llm_em_dat = df_llm_em_dat[
        df_llm_em_dat.apply(lambda row: row["Disaster Type"] in row["hazards_reclass"], axis=1)
    ].reset_index(drop=True)

    # Create date columns 
    df_llm_em_dat["Start Month"] = df_llm_em_dat["Start Month"].fillna(1).astype("Int64")
    df_llm_em_dat["Start Day"] = df_llm_em_dat["Start Day"].fillna(1).astype("Int64")
    df_llm_em_dat["Start Date"] = pd.to_datetime(
        df_llm_em_dat[["Start Year", "Start Month", "Start Day"]].rename(
            columns={"Start Year": "year", "Start Month": "month", "Start Day": "day"}
        ),
        errors="coerce"
    )

    df_llm_em_dat["End Month"] = df_llm_em_dat["End Month"].fillna(1).astype("Int64")
    df_llm_em_dat["End Day"] = df_llm_em_dat["End Day"].fillna(1).astype("Int64")
    df_llm_em_dat["End Date"] = pd.to_datetime(
        df_llm_em_dat[["End Year", "End Month", "End Day"]].rename(
            columns={"End Year": "year", "End Month": "month", "End Day": "day"}
        ),
        errors="coerce"
    )

    df_llm_em_dat["startMonth"] = df_llm_em_dat["startMonth"].fillna(1).astype("Int64")
    df_llm_em_dat["startDay"] = df_llm_em_dat["startDay"].fillna(1).astype("Int64")
    df_llm_em_dat["startDate"] = pd.to_datetime(
        df_llm_em_dat[["startYear", "startMonth", "startDay"]].rename(
            columns={"startYear": "year", "startMonth": "month", "startDay": "day"}
        ),
        errors="coerce"
    )

    df_llm_em_dat["endMonth"] = df_llm_em_dat["endMonth"].fillna(1).astype("Int64")
    df_llm_em_dat["endDay"] = df_llm_em_dat["endDay"].fillna(1).astype("Int64")
    df_llm_em_dat["endDate"] = pd.to_datetime(
        df_llm_em_dat[["endYear", "endMonth", "endDay"]].rename(
            columns={"endYear": "year", "endMonth": "month", "endDay": "day"}
        ),
        errors="coerce"
    )

    # # Keep only the ones with a difference of starting date smaller than a threshold 
    df_llm_em_dat["date_diff_start"] = (df_llm_em_dat['Start Date'] - df_llm_em_dat["startDate"]).abs()
    df_llm_em_dat["date_diff_end"] = (df_llm_em_dat['End Date'] - df_llm_em_dat["endDate"]).abs()
    df_llm_em_dat = df_llm_em_dat.loc[df_llm_em_dat["date_diff_start"]<date_diff_th]
    df_llm_em_dat = df_llm_em_dat.loc[df_llm_em_dat["date_diff_end"]<date_diff_th]

    df_llm_em_dat["date_diff_mean"] = (df_llm_em_dat["date_diff_start"] + df_llm_em_dat["date_diff_end"])/2

    # Match with GLIDE and closest date 
    df_llm_em_dat["DisNo."] = df_llm_em_dat["DisNo."].astype(str)

    appeal_to_disno = (
        df_llm_em_dat.groupby("appealCode", group_keys=False)
        .apply(lambda x: choose_unique_disno(x, column_minimize))
        .reset_index()
        .rename(columns={0: "chosen_DisNo"})
    )

    df1_no_split = df1_no_split.merge(appeal_to_disno, on="appealCode", how="left")

    df_matched = df1_no_split.merge(
        df2,
        left_on="chosen_DisNo",
        right_on="DisNo.",
        how="left"
    )
    return df_matched, df_llm_em_dat

def match_impact_values(df_llm_all_geo_linked, impactType): 
    """
    Compare LLM-extracted impact values with EM-DAT reported impacts.

    Aggregates LLM-extracted impact values at the appeal level and
    compares them with the corresponding EM-DAT impact values for a
    given impact type.

    Parameters
    ----------
    df_llm_all_geo_linked : pd.DataFrame
        LLM DataFrame already linked to EM-DAT events and geographic data.
    impactType : str
        Standardized impact type to be compared (e.g., fatalities,
        affected).

    Returns
    -------
    pd.DataFrame
        DataFrame containing LLM and EM-DAT impact values per appeal and
        a boolean indicator of exact matches.
    """
    appealCodelist = df_llm_all_geo_linked["appealCode"].unique()
    df_emdat_linked = df_llm_all_geo_linked.copy()
    emdat_col = mapping_impact_type[impactType]["emdat"]

    #Select impact values from the LLM
    df1 = (
            df_llm_all_geo_linked[(df_llm_all_geo_linked["impactSubtype"] == impactType) &
                        (df_llm_all_geo_linked["appealCode"].isin(appealCodelist))]
            [["appealCode", "impactValue_final"]]
            .groupby("appealCode", as_index=False)
            .sum()
            .rename(columns={"impactValue_final": "LLM_extracted"})
        )
    df1 = df1.dropna(subset=["LLM_extracted"])

    #Impact values from EMDAT
    df3 = (
            df_emdat_linked.loc[df_emdat_linked["appealCode"].isin(appealCodelist), ["appealCode", emdat_col]]
            .rename(columns={emdat_col: "EM-DAT"})
            .drop_duplicates()
            )
    df3 = df3.dropna(subset=["EM-DAT"])

    df_merge = pd.merge(df1, df3, on="appealCode", how='inner')
    df_merge["match"] = df_merge["LLM_extracted"] == df_merge["EM-DAT"]

    return df_merge