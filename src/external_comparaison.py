import pandas as pd
import json
import geopandas as gpd
from collections import Counter
import numpy as np
import ast
from shapely.ops import unary_union
import pandas as pd
from src.LLM_functions import *
from src.plot_functions import *
from src.data import *
from src.hazard_def import *
from src.impact_def import *

mapping_impact_type = {"Affected People" : {"monty_ifrc" : "affected_total", "go_ifrc" : "num_affected"}, 
                       "Injured People" : {"monty_ifrc" : "injured", "go_ifrc" : "num_injured"}, 
                       "Displaced People" : {"monty_ifrc" : "displaced_total", "go_ifrc" : "num_displaced" }, 
                       "Human Deaths" : {"monty_ifrc" : "death", "go_ifrc" : "num_dead" }, 
                       "Missing People" : {"monty_ifrc" : "missing", "go_ifrc" : "num_missing"}, 
                       "Infected and Ill People" : {"monty_ifrc" : None, "go_ifrc" : "epi_cases"}
                       }

go_ifrc_impact_source = {"report" : "field_reports_", 
                         "gov" : "field_reports_gov_", 
                         "other" : "field_reports_other_"
                         }

### LABELLED AND LLM DATAFRAMES 
def consolidate_impact_value(df: pd.DataFrame) -> pd.DataFrame:
    """
    Consolidates impact values into a single column 'impactValue_final' with priority:
    1. impactValue
    2. impactValueMin
    3. impactValueMax
    Drops rows where all three are missing.
    """
    df = df.copy()

    # Create consolidated column
    df["impactValue_final"] = (
        df["impactValue"]
        .combine_first(df["impactValueMin"])
        .combine_first(df["impactValueMax"])
    )

    # Drop rows where final value is missing
    df = df.dropna(subset=["impactValue_final"])

    return df

def consolidate_startYear(row):
    """
    If no startYear has been detected, take the year of the report 
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
    Converts the 'locationLowestAdmin' column (format 'ADM_0') 
    into a numeric column 'locationLowestAdminNum'.
    """
    df = df.copy()
    df["locationLowestAdminNum"] = (
        df["locationLowestAdmin"]
        .astype(str)                 # ensure it's string
        .str.extract(r"(\d+)")       # extract digits
        .astype(float)               # convert to number
    )
    return df

def group_quanti_country_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups quantitative impacts at the country level.
    
    Rules:
    - If rows exist with locationLowestAdminNum == 0:
        * Sum impactValue_final
        * Concatenate unique values of location, locationOsm, locationGaul
        * Union geometries
        * Keep other columns constant (take first non-null)
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
                
            elif not df_admin_1.empty : 
                row["impactValue_final"] = df_admin_1["impactValue_final"].sum()
                df_admin = df_admin_1

            elif not df_admin_2.empty : 
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

def clean_group(df_impact) : 
    df_output = df_impact.copy()
    df_output['startYear'] = df_output.apply(consolidate_startYear, axis=1)
    df_output = add_location_admin_num(df_output)
    df_output = consolidate_impact_value(df_output)
    df_output = group_quanti_country_level(df_output)
    return df_output    

## IFRC_GO 

def clean_impact_values(row):
    for impact_type, mapping in mapping_impact_type.items():
        for impact_source, prefix in go_ifrc_impact_source.items():
            col = prefix + mapping["go_ifrc"]
            # check if column exists and has a non-null value
            if col in row and pd.notna(row[col]):
                row[impact_type] = row[col]
                row[f"{impact_type} Source"] = impact_source
                break  # stop once one source is found
    return row

def open_clean_ifrc_go() : 
    df_ifrc_go = pd.read_csv(DATA_EXTERNAL_SOURCE + 'ifrc_go_all.csv')

    #Retrieve impact value 
    df_ifrc_go = df_ifrc_go.apply(clean_impact_values, axis=1)

    # #Remove extra row 
    # raw_cols = [
    # prefix + mapping["go_ifrc"]
    # for prefix in go_ifrc_impact_source.values()
    # for mapping in mapping_impact_type.values()]
    # df_ifrc_go = df_ifrc_go.drop(columns=[c for c in raw_cols if c in df_ifrc_go.columns])

    #Rename columns 
    df_ifrc_go = df_ifrc_go.rename({"appeals_code" : "appealCode"}, axis=1)
    df_ifrc_go["id"] = df_ifrc_go["id"].astype(int)
    return df_ifrc_go


## IFRC_MONTY

def open_clean_ifrc_monty(df_ifrc_go) : 
    df_ifrc_monty = pd.read_csv(DATA_EXTERNAL_SOURCE + 'ifrc_monty_all.csv')

    #Use id and df_ifrc_go to fing appealCode 
    df_ifrc_monty["id_clean"] = df_ifrc_monty["id"].str.extract(r"ifrcevent-impact--(\d+)-")
    df_ifrc_monty["id_clean"] = df_ifrc_monty["id_clean"].astype(int)
    df_ifrc_monty = df_ifrc_monty.merge(
        df_ifrc_go[["id", "appealCode"]].rename(columns={"id": "id_clean"}),
        on="id_clean",
        how="left")
    
    df_ifrc_monty = df_ifrc_monty.drop(columns=["id_clean"])

    #Rename impact type 
    monty_map = {
        mapping["monty_ifrc"]: impact_type
        for impact_type, mapping in mapping_impact_type.items()
        if mapping["monty_ifrc"] is not None
        }

    # Replace values in the column
    df_ifrc_monty["impact_type"] = df_ifrc_monty["impact_type"].replace(monty_map)

    return df_ifrc_monty
