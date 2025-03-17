import pandas as pd
import json
from collections import Counter
import numpy as np
import re
import pycountry
from sklearn.metrics.pairwise import cosine_similarity
import copy as cp
from constants import *
import ast


unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
unique_country_names = [country.name for country in pycountry.countries]
pattern = '|'.join(map(re.escape, unique_country_names))
unique_dict = {
    'hazardType' : maintype_to_subytpe_emdat.keys(),
    'hazardSubtypes' : ast.literal_eval(hazard_all_subtype_emdat),
    'country' : unique_country_names
}

# Functions for accuracy computation
def calculate_precision_v2(df_chat, df_labelled, precision_columns_list, unique_dict=unique_dict):
    '''
    df1 : Test DataFrame
    df2 : Labbeled DataFrame

    Look for unique type
    '''
    # Replace "nan" with empty string in df2 for specified columns
    for column in precision_columns_list:
        df2[column] = ["" if str(value) == "nan" else value for value in df2[column]]

    # Initialize results dictionary
    results = {col: {"psum": 0, "count": 0} for col in precision_columns_list}

    # Group by 'doi' and calculate precision for each column
    for id, df in df1.groupby("appealCode"):
        tmp = df2[df2["appealCode"] == id].reset_index(drop=True)
        tmp2 = df.reset_index(drop=True)

        for precision_column in precision_columns_list:
            #For Hazard and Country, accuracy is computed by checking is the found attributes are matching
            if precision_column in ['Hazard', 'Hazard_subtype', 'Country'] :
                unique_list = unique_dict[precision_column]

                #Select the unique set
                tmp_unique  = tmp[precision_column].unique()

                if precision_column == 'Hazard_subtype' :
                    tmp2_unique = set(
                    elem
                    for row in tmp2[precision_column].dropna()
                    if isinstance(row, list)
                    for elem in row)
                else :
                    tmp2_unique = tmp2[precision_column].unique()

                # Create binary vectors for the two lists
                vector1 = [1 if hazard in sorted(tmp_unique) else 0 for hazard in unique_list]
                vector2 = [1 if hazard in sorted(tmp2_unique) else 0 for hazard in unique_list]

                # Convert the vectors to numpy arrays and reshape them
                vector1 = np.array(vector1).reshape(1, -1)
                vector2 = np.array(vector2).reshape(1, -1)

                # Compute the cosine similarity
                cos_sim = cosine_similarity(vector1, vector2)[0][0]
                results[precision_column]["psum"] += cos_sim
                results[precision_column]["count"] += 1

            #For Location and Date, the accuracy look is a value is found when one should be found
            #Do not look at the exact value
            elif precision_column in ['Location', 'Start_Date', 'End_Date'] :
                # Create binary vectors for the two lists
                n_tmp = sum(1 for value in tmp[precision_column] if (value != 'NULL') and (value != np.NaN))
                n_tmp2 = sum(1 for value in tmp2[precision_column] if (value != 'NULL') and (value != np.NaN))

                #cos_sim = cosine_similarity(vector1, vector2)[0][0]
                if n_tmp != 0 :
                    results[precision_column]["psum"] += n_tmp2/n_tmp
                    results[precision_column]["count"] += 1
    # Calculate precision and create a DataFrame
    precision_values = []
    for precision_column in precision_columns_list:
        if results[precision_column]["count"] > 0:
            precision = results[precision_column]["psum"] / results[precision_column]["count"]
        else:
            precision = float('nan')  # Handle case where there is no data to calculate precision
        precision_values.append(precision)

    precision_df = pd.DataFrame([precision_values], columns=precision_columns_list)
    return precision_df


# Functions for accuracy computation
def calculate_precision_per_report(df_chat, df_labelled, precision_columns_list, unique_dict=unique_dict):
    '''
    df_chat : Test DataFrame
    df_labelled : Labbeled DataFrame

    unique_dist : Dictionnary listing all the possible values. Used of the hazardType, hazardSubtypes and country
    '''
    # Replace "nan" with empty string in df2 for specified columns
    for column in precision_columns_list:
        df_labelled[column] = ["" if str(value) == "nan" else value for value in df_labelled[column]]

    # Initialize results dictionary
    results = {col: {"psum": 0, "count": 0} for col in precision_columns_list}

    # Group by 'doi' and calculate precision for each column
    for id, df_chat_rep in df_chat.groupby("appealCode"):
        tmp_labelled = df_labelled[df_labelled["appealCode"] == id].reset_index(drop=True)
        tmp_chat = df_chat_rep.reset_index(drop=True)

        #Group by event 
        grouping_columns = ["hazardType", "hazardSubtypes", "country", "startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay"] 
        tmp_labelled[grouping_columns] = tmp_labelled[grouping_columns].fillna('missing')
        tmp_labelled_event = tmp_labelled.groupby(grouping_columns)
        
        tmp_chat[grouping_columns] = tmp_chat[grouping_columns].fillna('missing')
        tmp_chat_event = tmp_chat.groupby(grouping_columns)

        for precision_column in precision_columns_list:
            if precision_column in grouping_columns : 
                index = grouping_columns.index(precision_column)
    
                #Select the unique set
                tmp_labelled_event_unique = [haz[index] for haz in tmp_labelled_event.groups.keys()]
                tmp_chat_event_unique = [haz[index] for haz in tmp_chat_event.groups.keys()]
                
                #For Hazard and Country, accuracy is computed by checking is the found attributes are matching
                if precision_column in ["hazardType", "hazardSubtypes", "country"] :
                    unique_list = unique_dict[precision_column]
                    
                    # Create binary vectors for the two lists
                    vector1 = [1 if hazard in sorted(tmp_labelled_event_unique) else 0 for hazard in unique_list]
                    vector2 = [1 if hazard in sorted(tmp_chat_event_unique) else 0 for hazard in unique_list]

                    # if precision_column == "country" : 
                    #     print(vector1)
                    #     print(vector2)
    
                    # Convert the vectors to numpy arrays and reshape them
                    vector1 = np.array(vector1).reshape(1, -1)
                    vector2 = np.array(vector2).reshape(1, -1)
    
                    # Compute the cosine similarity
                    cos_sim = cosine_similarity(vector1, vector2)[0][0]
                    results[precision_column]["psum"] += cos_sim
                    results[precision_column]["count"] += 1
    
                #For Location and Date, the accuracy look is a value is found when one should be found
                #Do not look at the exact value
                elif precision_column in ["startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay"] :
                    # Create binary vectors for the two lists
                    n_tmp = sum(1 for value in tmp_labelled[precision_column].unique() if (value != 'NULL') and (value != "missing"))
                    n_tmp2 = sum(1 for value in tmp_chat[precision_column].unique() if (value != 'NULL') and (value != "missing"))
    
                    #cos_sim = cosine_similarity(vector1, vector2)[0][0]
                    if n_tmp != 0 :
                        results[precision_column]["psum"] += n_tmp2/n_tmp
                        results[precision_column]["count"] += 1

            #If the column for accuracy is not part of the grouping
            #Compare the list of unique informations found 
            else :          
                # keys_chat = tmp_labelled_event.groups.keys()   
                # keys_labelled = tmp_chat_event.groups.keys()

                # #Compute the accuracy per event 
                # for i in keys:
                #     labelled_event_loop = reports_labelled_event.get_group(i) 
                        
                n_tmp = sum(1 for value in tmp_labelled[precision_column].unique() if (value != 'NULL') and (value != "missing"))
                n_tmp2 = sum(1 for value in tmp_chat[precision_column].unique() if (value != 'NULL') and (value != "missing"))
                if n_tmp != 0 :
                    results[precision_column]["psum"] += n_tmp2/n_tmp
                    results[precision_column]["count"] += 1
    # Calculate precision and create a DataFrame
    precision_values = []
    for precision_column in precision_columns_list:
        if results[precision_column]["count"] > 0:
            precision = results[precision_column]["psum"] / results[precision_column]["count"]
        else:
            precision = float('nan')  # Handle case where there is no data to calculate precision
        precision_values.append(precision)

    precision_df = pd.DataFrame([precision_values], columns=precision_columns_list)
    return precision_df

def calculate_precision_per_hazardType(df_chat, df_labelled, precision_columns_list, unique_dict=unique_dict):
    precision_dict = {}
    for hazard in unique_dict["hazardType"] :
        df_chat_haz = df_chat.loc[df_chat.hazardType == hazard].copy()
        df_labelled_haz = df_labelled.loc[df_labelled.hazardType == hazard].copy()
        precision_haz = calculate_precision_per_report(df_chat_haz, df_labelled_haz, precision_columns_list, unique_dict)
        precision_dict[hazard] = precision_haz
    return precision_dict

def calculate_precision_per_hazardSubtypes(df_chat, df_labelled, precision_columns_list, unique_dict=unique_dict):
    precision_dict = {}
    for hazardSubtype in unique_dict["hazardSubtypes"] : 
        df_chat_haz = df_chat.loc[df_chat.hazardSubtypes == hazardSubtype].copy()
        df_labelled_haz = df_labelled.loc[df_labelled.hazardSubtypes == hazardSubtype].copy()
        precision_haz = calculate_precision_per_report(df_chat_haz, df_labelled_haz, precision_columns_list, unique_dict)
        precision_dict[hazardSubtype] = precision_haz
    return precision_dict
