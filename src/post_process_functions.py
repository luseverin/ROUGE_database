import pycountry
import pandas as pd
import json
from collections import Counter
import numpy as np
import re
import copy as cp
import ast


def country_name_to_iso3(name):
    try:
        country = pycountry.countries.lookup(name)
        return country.alpha_3
    except LookupError:
        return None
def separate_locs(locations):
    """Separate locations separated by a comma"""
    if pd.isnull(locations):
        return None
    else:
        return locations.split(",")

def remove_startspace(loc_list):
    """Remove space at start of string"""
    if loc_list is None:
        return None
    else:
        return [loc.strip() for loc in loc_list]

def format_output(df, num_cols, list_cols=None):
    """
    Format output of the final report

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to be formatted
    num_cols : list
        List of columns to be converted to float

    Returns
    -------
    pd.DataFrame
        Formatted DataFrame
    """
    def listify_strings(x):
        if isinstance(x, str):
            try :
                x = json.loads(x.replace("'", '"'))
            except :
                x = [x]
            return x
        elif isinstance(x, list):
            return x
        elif pd.isna(x) or x is None:
            return []
        else:
            return x
    df = df.replace(["null", "None", None], np.nan)
    df[num_cols] = df[num_cols].astype(float)
    if list_cols is None:
        return df
    df[list_cols] = df[list_cols].map(lambda x: listify_strings(x))
    return df

def explode_lists(df):
    """
    Explodes columns containing lists in a DataFrame, creating separate rows for each element in the lists.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns that may contain lists.

    Returns
    -------
    pd.DataFrame
        A DataFrame where each list element in the specified columns is expanded into its own row.
    """
    # Identify columns with lists
    list_columns = [col for col in df.columns if df[col].apply(lambda x: isinstance(x, list)).any()]

    # Replace `None` or `NaN` with empty lists for exploding
    for col in list_columns:
        df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])

    # Create the repeated index based on the maximum lengths of lists in the list columns
    repeat_counts = df[list_columns].applymap(len).max(axis=1)
    df = df.loc[df.index.repeat(repeat_counts)].reset_index(drop=True)

    # Explode each list column
    for col in list_columns:
        df[col] = df[col].explode(ignore_index=True)

    return df

def convert_labelled_chat_format(df_labelled) :
    """
    Convert a labelled report DataFrame with the regions and cities as list into a DataFrame a row for each region and each city.
    """
    df_labelled_chat = pd.DataFrame(columns=df_labelled.columns)
    for index, row in df_labelled.iterrows():
        #If no regions and cities
        if isinstance(row.region, float) and isinstance(row.city, float) :
            df_labelled_chat = pd.concat([df_labelled_chat, row.to_frame().T], ignore_index=True)

        else :
            #Add region
            if isinstance(row.region, str)  :
                regions = ast.literal_eval(row.region)
            elif isinstance(row.region, list) :
                regions = row.region
            else :
                regions = None

            if not regions is None:
                for region in regions :
                    row_append = row.copy()
                    row_append['region'] = region
                    row_append['city'] = None

                    #Find the corresponding locationAnnotation
                    # print(row)
                    # print(row.locationAnnotation)
                    locationsAnnotations = ast.literal_eval(row.locationAnnotation)
                    for locationAnnot in locationsAnnotations :
                        if re.search(region, locationAnnot, re.IGNORECASE) :
                            row_append['locationAnnotation'] = locationAnnot
                            df_labelled_chat = pd.concat([df_labelled_chat, row_append.to_frame().T], ignore_index=True)

            #Add location
            if isinstance(row.city, str) :
                cities = ast.literal_eval(row.city)
            elif isinstance(row.city, list) :
                cities = row.city
            else :
                cities = None

            if not cities is None :
                for city in cities :
                    row_append = row.copy()
                    row_append['region'] = None
                    row_append['city'] = city

                    #Find the corresponding locationAnnotation
                    locationsAnnotations = ast.literal_eval(row.locationAnnotation)
                    for locationAnnot in locationsAnnotations :
                        if re.search(city, locationAnnot, re.IGNORECASE) :
                            row_append['locationAnnotation'] = locationAnnot
                            df_labelled_chat = pd.concat([df_labelled_chat, row_append.to_frame().T], ignore_index=True)
    return df_labelled_chat

def clean_chat_format(df_labelled) :
    """
    Convert a labelled report DataFrame with the regions and cities as list into a DataFrame a row for each region and each city.
    """
    df_labelled_chat = pd.DataFrame(columns=df_labelled.columns)
    for index, row in df_labelled.iterrows():
        #Loop over the hazardSubtype
        hazardsubtypes = ast.literal_eval(row.hazardSubtypes)
        if not hazardsubtypes :
            hazardsubtypes = [None]
        for subtype in hazardsubtypes :
            #If no regions and cities
            if isinstance(row.region, float) and isinstance(row.city, float) :
                df_labelled_chat = pd.concat([df_labelled_chat, row.to_frame().T], ignore_index=True)

            else :
                regions = row.region
                if not regions is None :
                    for region in regions :
                        row_append = row.copy()
                        row_append['region'] = region
                        row_append['city'] = None
                        row_append['hazardSubtypes'] = subtype
                        df_labelled_chat = pd.concat([df_labelled_chat, row_append.to_frame().T], ignore_index=True)

                #Add location
                cities = row.city
                if not cities is None :
                    for city in cities :
                        row_append = row.copy()
                        row_append['region'] = None
                        row_append['city'] = city
                        row_append['hazardSubtypes'] = subtype
                        df_labelled_chat = pd.concat([df_labelled_chat, row_append.to_frame().T], ignore_index=True)
    return df_labelled_chat

## DEPRECATED
## Convert json to dataframe
#def clean_output_df(results_json, out_cols=['Hazard','Country','Location','Start_Date','End_Date']):
#    df_all_list = []
#    for report_id, report in results_json.items():
#        results = report['results']
#        results_process = cp.deepcopy(results)
#        results_process = re.sub('[\{\}]', '', results_process)
#        results_process= results_process.split("\n")
#        results_process = results_process[1: -1]
#        columns=['Hazard','Country','Location','Start_Date','End_Date']
#        #df_results = pd.DataFrame(columns=columns)
#        df_list = []
#        haz_list = []
#        dict_results = dict()
#        for i, pair in enumerate(results_process[:]):
#            #print(str(i)+": "+pair)
#            if len(pair.split(":")) == 2:
#                key, value = pair.split(":")
#            else:
#                pass
#            key = re.sub("[\", ]","",key)
#
#            if key == 'Hazard':
#                haz_list.append(re.sub("[\", ]","",key))
#                dict_haz = cp.copy(results_process[i:i+5])
#                dict_res={}
#                for j in np.arange(i,i+5):
#                    pairj = results_process[j]
#                    keyj, valuej = pairj.split(":")
#                    keyj = re.sub("[\", ,,]","",keyj)
#                    valuej = re.sub("[\",\[,\]]","",valuej)
#                    dict_res[keyj] = valuej[1:]#valuej
#                df_list.append(pd.DataFrame(dict_res,index=[0]))
#
#            df_all = pd.concat(df_list)
#            df_all['appealCode'] = report_id
#
#            #Separate if several countries are found
#            expanded_df = pd.DataFrame(columns=df_all.columns)
#            for id_row, row in df_all.iterrows() :
#                matched_countries = re.findall(pattern, row['Country'])
#                # If more than one country found
#                #if len(matched_countries) > 1 :
#                for country in matched_countries:
#                    new_row = row.copy()
#                    new_row['Country'] = country
#                    expanded_df = pd.concat([expanded_df, pd.DataFrame([new_row])], ignore_index=True)
#
#        df_all_list.append(expanded_df)#.append(df_all)
#    return pd.concat(df_all_list)