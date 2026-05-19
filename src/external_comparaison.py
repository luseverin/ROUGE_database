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
                       "Injured People" : {"ifrc_monty" : "injured", "ifrc_go" : "num_injured", "emdat" : "No. Injured"},
                       "Displaced People" : {"ifrc_monty" : "displaced_total", "ifrc_go" : "num_displaced", "emdat" : None},
                       "Human Deaths" : {"ifrc_monty" : "death", "ifrc_go" : "num_dead", "emdat" : "Total Deaths"},
                       "Missing People" : {"ifrc_monty" : "missing", "ifrc_go" : "num_missing", "emdat" : None},
                       "Homeless People" : {"ifrc_monty" : None, "ifrc_go" : None, "emdat" : "No. Homeless"}
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
        df["impactValue"].replace("", pd.NA)
        .combine_first(df["impactValueMin"].replace("", pd.NA))
        .combine_first(df["impactValueMax"].replace("", pd.NA))
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

def group_quanti_country_level(df: pd.DataFrame, ADM_min=0) -> pd.DataFrame:
    """
    Groups quantitative impacts at the country level.

    Rules:
    - If rows exist with locationLowestAdminNum == 0:
        * Sum impactValue_final
        * Concatenate unique values of location, locationOsm, locationGaul
        * Union geometries
        * Keep other columns constant (take first non-null)
    - Other wise :
        * Take the highest reported value
        * Add other impacts if the the intersection of the polygons is null
    """
    df_output = []

    for appeal in df["appealCode"].unique():
        df_loop = df[df["appealCode"] == appeal]

        for impactType in df_loop["impactSubtype"].unique():
            df_impact_loop = df_loop[df_loop["impactSubtype"] == impactType]

            # Take the row with the maximum impactValue_final regardless of admin level
            if df_impact_loop.empty:
                continue

            max_idx = df_impact_loop["impactValue_final"].idxmax()
            df_admin = df_impact_loop.loc[[max_idx]]

            row = {}
            row["impactValue_final"] = df_admin["impactValue_final"].iloc[0]

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
    df_output = df_impact.copy()
    df_output['startYear'] = df_output.apply(consolidate_startYear, axis=1)
    df_output = add_location_admin_num(df_output)
    df_output = consolidate_impact_value(df_output)
    df_output = group_quanti_country_level(df_output, ADM_min=0)
    return df_output

## IFRC_GO

def clean_impact_values(row):
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

def open_clean_ifrc_go(appeal_filter=["DREF", "Emergency Appeal", "International Appeal"]) :
    df_ifrc_go = pd.read_csv(DATA_EXTERNAL_SOURCE / 'ifrc_go_all.csv')

    #Retrieve impact value
    df_ifrc_go = df_ifrc_go.apply(clean_impact_values, axis=1)

    # #Remove extra row
    # raw_cols = [
    # prefix + mapping["ifrc_go"]
    # for prefix in ifrc_go_impact_source.values()
    # for mapping in mapping_impact_type.values()]
    # df_ifrc_go = df_ifrc_go.drop(columns=[c for c in raw_cols if c in df_ifrc_go.columns])

    #Rename columns
    df_ifrc_go = df_ifrc_go.rename({"appeals_code" : "appealCode"}, axis=1)
    df_ifrc_go["id"] = df_ifrc_go["id"].astype("Int64")

    #Select only DREF reports
    df_ifrc_go = df_ifrc_go.loc[df_ifrc_go["appeals_atype_display"].isin(appeal_filter)]

    #Select only natural disaster events
    df_ifrc_go = df_ifrc_go.loc[df_ifrc_go["dtype_name"].isin(hazard_ifrc_go)]

    return df_ifrc_go

def clean_structure_ifrc_go(df, impactSubtypes=mapping_impact_type.keys()) :
    """
    Transform IFRC GO data into long-format with one row per impact type.
    
    Parameters:
    -----------
    df : pd.DataFrame
        The IFRC GO dataframe with impact columns
    impactSubtypes : list
        List of impact subtypes to extract (e.g., ['Affected People', 'Displaced People', ...])
    
    Returns:
    --------
    pd.DataFrame
        Long-format dataframe with one row per impact per appeal,
        with all columns prefixed by IFRCGO_
    """
    
    # Columns to keep from the original dataframe
    keep_cols = [
        "appealCode", "appeals_atype_display", "appeals_end_date",
        "appeals_start_date", "countries_iso3", "dtype_name", "glide", "updated_at"
    ]
    
    # Filter to only columns that exist in the dataframe
    available_cols = [c for c in keep_cols if c in df.columns]
    
    # Collect rows for each impact subtype
    rows = []
    
    for impactSubtype in impactSubtypes:
        # Get the column name for this impact subtype from the mapping
        # col = mapping_impact_type.get(impactSubtype, {}).get('ifrc_go')
        col = impactSubtype
        
        # Skip if no mapping or column doesn't exist
        if col is None or col not in df.columns:
            # print("Skipping impact subtype '{}' because column '{}' is not available.".format(impactSubtype, col))
            continue
        
        # Create subset with only non-null impact values
        df_subset = df[available_cols + [col]].copy()
        df_subset = df_subset.dropna(subset=[col])
        
        # Add impactSubtype and rename impact value column
        df_subset["IFRCGO_impactSubtype"] = impactSubtype
        df_subset["IFRCGO_impactValue"] = df_subset[col]
        
        # Keep only the columns we want
        df_subset = df_subset[available_cols + ["IFRCGO_impactSubtype", "IFRCGO_impactValue"]]
        
        rows.append(df_subset)
    
    # Concatenate all rows
    if rows:
        result = pd.concat(rows, ignore_index=True)
    else:
        result = pd.DataFrame()
    
    # Add IFRCGO_ prefix to all columns except impactSubtype
    rename_dict = {col: f"IFRCGO_{col}" for col in available_cols}
    result = result.rename(columns=rename_dict)
    
    return result

## IFRC_MONTY

def open_clean_ifrc_monty(df_ifrc_go) :
    # df_ifrc_monty = pd.read_csv(DATA_EXTERNAL_SOURCE / 'ifrc_monty_all.csv')
    df_ifrc_monty = pd.read_csv(DATA_EXTERNAL_SOURCE / 'ifrc_monty_all_20260417.csv')

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

def open_emdat(file_name='public_emdat_custom_request_2025-08-19.xlsx', 
               columns_interest = ["DisNo.", "Classification Key", "Disaster Type", "Disaster Subtype", "ISO", "Country", "Location", "Start Date", "End Date", 
                                   "Total Deaths", "No. Injured", "No. Homeless", "Total Affected", "Entry Date"]) :
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

    #Select only columns of interest
    df_em_dat = df_em_dat[columns_interest ]
    rename_dict = {col: f"EMDAT_{col}" for col in df_em_dat.columns}
    df_em_dat = df_em_dat.rename(columns=rename_dict)

    return df_em_dat

def clean_structure_emdat(df, impactSubtypes=None):
    """
    Transform EMDAT wide-format data into long-format with one row per impact type.

    Output columns include:
    - all non-impact EMDAT columns (kept as-is)
    - EMDAT_ImpactSubtype
    - EMDAT_impactValue
    """
    if impactSubtypes is None:
        impactSubtypes = list(mapping_impact_type.keys())

    # Build mapping: impact subtype -> EMDAT impact column (prefixed)
    emdat_col_by_subtype = {}
    for subtype in impactSubtypes:
        emdat_raw_col = mapping_impact_type.get(subtype, {}).get("emdat")
        if emdat_raw_col is None:
            continue
        emdat_col = f"EMDAT_{emdat_raw_col}"
        if emdat_col in df.columns:
            emdat_col_by_subtype[subtype] = emdat_col

    # Keep all non-impact columns (hazard/event metadata)
    emdat_impact_cols = list(emdat_col_by_subtype.values())
    keep_cols = [c for c in df.columns if c not in emdat_impact_cols]

    rows = []
    for subtype, impact_col in emdat_col_by_subtype.items():
        subset = df[keep_cols + [impact_col]].copy()
        subset = subset.dropna(subset=[impact_col])

        subset["EMDAT_impactSubtype"] = subtype
        subset["EMDAT_impactValue"] = subset[impact_col]

        subset = subset[keep_cols + ["EMDAT_impactSubtype", "EMDAT_impactValue"]]
        rows.append(subset)

    if rows:
        return pd.concat(rows, ignore_index=True)

    return pd.DataFrame(columns=keep_cols + ["EMDAT_impactSubtype", "EMDAT_impactValue"])

def choose_unique_disno(df_llm_em_dat, column_minimize):
    # Count number of impacts per DisNo
    if df_llm_em_dat["EMDAT_DisNo."].nunique() == 1:
        return df_llm_em_dat["EMDAT_DisNo."].iloc[0]

    # print(top_disnos)
    # # Tie case: pick closest EntryDate to reportDate
    # tied = group[group["DisNo."].isin(top_disnos)].copy()
    # tied["date_diff"] = (tied["EntryDate"] - tied["reportDate"]).abs()
    # return tied.loc[tied["date_diff"].idxmin(), "DisNo."]
    # print(group)

    # Filter over impact with a Glide number
    df_llm_em_dat_glide = df_llm_em_dat.copy()
    # df_llm_em_dat_glide = df_llm_em_dat_glide.dropna(subset=["External IDs"])

    # if df_llm_em_dat_glide.empty:
    #     df_llm_em_dat_filtered = df_llm_em_dat.copy()
    # else :
    #     df_llm_em_dat_filtered = df_llm_em_dat_glide
    df_llm_em_dat_filtered = df_llm_em_dat_glide

    # Select the DisNo. with the most numerous number of associated impact
    counts = df_llm_em_dat_filtered["EMDAT_DisNo."].value_counts()  # assuming you have an "impact_id" col
    max_count = counts.max()
    top_disnos = counts[counts == max_count].index

    # # Minimize distance in declaration date
    # df_llm_em_dat_filtered["date_diff"] = (df_llm_em_dat_filtered['Entry Date'] - df_llm_em_dat_filtered["reportDate"]).abs()
    # min_diff = df_llm_em_dat_filtered[df_llm_em_dat_filtered["EMDAT_DisNo."].isin(top_disnos)].groupby("EMDAT_DisNo.")["date_diff"].min()
    # chosen_disno = min_diff.idxmin()

    #Minimize the distance between start dates
    min_diff = df_llm_em_dat_filtered[df_llm_em_dat_filtered["EMDAT_DisNo."].isin(top_disnos)].groupby("EMDAT_DisNo.", group_keys=False)[column_minimize].min()
    chosen_disno = min_diff.idxmin()
    return chosen_disno

def matching_emdat(df_llm, df_em_dat, date_diff_th, column_minimize, country_field='country_iso3', match_on_subtype=True):
    """
    df1 : DataFrame with the llm output
    df2 : DataFrame with the emdat data
    """
    df1 = cp.deepcopy(df_llm)
    df1_no_split = cp.deepcopy(df_llm)
    # df1["_row_id"] = np.arange(len(df1))
    df2 = cp.deepcopy(df_em_dat)

    # Map the hazard to emdat type
    reverse_hazard_mapping_emdat = reverse_mapping(hazard_mapping_emdat)
    df1["hazards_reclass"] = df1["hazards"].apply(lambda x: reclassify_hazard_emdat(x, reverse_hazard_mapping_emdat)) ## ADD the reverse_haazrd_mapping

    # Explode countries
    df1 = df1.explode(country_field).reset_index(drop=True)

    # # Rename and add columns
    # df2 = df2.rename({'ISO' : 'iso_emdat'}, axis=1)

    ## First occurence year
    # df_llm_em_dat = df2.merge(df1, left_on='Start Year', right_on = 'startYear', how='inner')
    df_llm_em_dat = df2.merge(
        df1,
        left_on="EMDAT_ISO",
        right_on=country_field,
        how="inner"
    )

    # df_llm_em_dat = (
    #     df2.merge(df1, how="cross")  # every combination
    #     .query("abs(`Start Year` - startYear) <= 1")
    # )

    ## Keep only rows where Disaster Type is inside hazards list
    df_llm_em_dat = df_llm_em_dat[
        df_llm_em_dat.apply(lambda row: row["EMDAT_Disaster Type"] in row["hazards_reclass"], axis=1)
    ].reset_index(drop=True)

    # ## Macth with countries
    # df_llm_em_dat = df_llm_em_dat[
    #     df_llm_em_dat.apply(lambda row: row["country_emdat"] in row[country_field], axis=1)
    # ].reset_index(drop=True)

    # Create date columns
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
    # date_diff_th = datetime.timedelta(days=6*30) ## Verify how to define the timedelta
    df_llm_em_dat["date_diff_start"] = (df_llm_em_dat['EMDAT_Start Date'] - df_llm_em_dat["startDate"]).abs()
    df_llm_em_dat["date_diff_end"] = (df_llm_em_dat['EMDAT_End Date'] - df_llm_em_dat["endDate"]).abs()
    df_llm_em_dat = df_llm_em_dat.loc[df_llm_em_dat["date_diff_start"]<date_diff_th]
    df_llm_em_dat = df_llm_em_dat.loc[df_llm_em_dat["date_diff_end"]<date_diff_th]

    df_llm_em_dat["date_diff_mean"] = (df_llm_em_dat["date_diff_start"] + df_llm_em_dat["date_diff_end"])/2
    # Match with GLIDE and closest date
    df_llm_em_dat["EMDAT_DisNo."] = df_llm_em_dat["EMDAT_DisNo."].astype(str)

    # Build one chosen EMDAT event per appealCode
    appeal_to_disno = (
        df_llm_em_dat.groupby(["appealCode"], group_keys=False)
        .apply(lambda x: choose_unique_disno(x, column_minimize))
        .reset_index()
        .rename(columns={0: "chosen_DisNo"})
    )

    # Keep all rows from df1_no_split, then attach chosen DisNo
    df1_no_split = df1_no_split.merge(appeal_to_disno, on=["appealCode"], how="left")

    # Then attach EMDAT hazard rows by DisNo and matching impact subtype when available
    subtype_col = None
    if "EMDAT_ImpactSubtype" in df2.columns:
        subtype_col = "EMDAT_ImpactSubtype"
    elif "EMDAT_impactSubtype" in df2.columns:
        subtype_col = "EMDAT_impactSubtype"

    if match_on_subtype and subtype_col is not None and "impactSubtype" in df1_no_split.columns:
        df_matched = df1_no_split.merge(
            df2,
            left_on=["chosen_DisNo", "impactSubtype"],
            right_on=["EMDAT_DisNo.", subtype_col],
            how="left",
        )
    else:
        df_matched = df1_no_split.merge(
            df2,
            left_on="chosen_DisNo",
            right_on="EMDAT_DisNo.",
            how="left",
        )

    return df_matched, df_llm_em_dat

def match_impact_values(df_llm_all_geo_linked, impactType):
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

    # df_merge_uniquely_linked = df_merge.loc[df_merge["appealCode"].isin(appeal_uniquely_linked)]
    return df_merge

############ ANALYSIS FUNCTIONS

def count_impacts_by_subtype(
    df_rouge,
    linked_sources,
    impact_subtypes,
    appeal_col="appealCode",
    rouge_subtype_col="impactSubtype",
    rouge_value_col="impactValue_final",
):
    """
    Count unique appealCode with available impact value per impact subtype for:
    - ROUGE original dataframe
    - any number of linked external dataframes (e.g. IFRCGO, EMDAT)

    Returns counts and percentages.
    """
    summary_rows = []

    count_dict = {"ROUGE": []}
    perc_dict = {"ROUGE": []}
    for source_name in linked_sources.keys():
        count_dict[source_name] = []
        perc_dict[source_name] = []

    # Denominators for percentages (unique appealCode per dataset)
    rouge_den = max(df_rouge[appeal_col].nunique(), 1)
    source_den = {
        source_name: max(cfg["df"][appeal_col].nunique(), 1)
        for source_name, cfg in linked_sources.items()
    }

    for subtype in impact_subtypes:
        row = {"impactSubtype": subtype}

        # ROUGE count + %
        rouge_mask = (
            (df_rouge[rouge_subtype_col] == subtype)
            & (df_rouge[rouge_value_col].notna())
        )
        n_rouge = df_rouge.loc[rouge_mask, appeal_col].nunique()
        p_rouge = 100.0 * n_rouge / rouge_den

        row["ROUGE_count"] = n_rouge
        row["ROUGE_perc"] = p_rouge
        count_dict["ROUGE"].append(n_rouge)
        perc_dict["ROUGE"].append(p_rouge)

        # Linked sources count + %
        for source_name, cfg in linked_sources.items():
            df_src = cfg["df"]
            value_col = cfg["value_col"]
            source_subtype_col = cfg.get("source_subtype_col")

            mask = df_src[appeal_col].notna()

            # Keep the original ROUGE subtype lane when available in linked df
            if rouge_subtype_col in df_src.columns:
                mask &= df_src[rouge_subtype_col] == subtype

            # Also enforce source subtype match when the source-specific subtype column exists
            if source_subtype_col and source_subtype_col in df_src.columns:
                mask &= df_src[source_subtype_col] == subtype

            if value_col in df_src.columns:
                mask &= df_src[value_col].notna()
            else:
                mask &= False

            n_source = df_src.loc[mask, appeal_col].nunique()
            p_source = 100.0 * n_source / source_den[source_name]

            row[f"{source_name}_count"] = n_source
            row[f"{source_name}_perc"] = p_source
            count_dict[source_name].append(n_source)
            perc_dict[source_name].append(p_source)

        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    return summary_df, count_dict, perc_dict


