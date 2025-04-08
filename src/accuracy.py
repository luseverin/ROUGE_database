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
from geopy.distance import geodesic


unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
unique_country_names = [country.name for country in pycountry.countries]
pattern = '|'.join(map(re.escape, unique_country_names))
unique_dict = {
    'hazardType' : maintype_to_subytpe_emdat.keys(),
    'hazardSubtypes' : ast.literal_eval(hazard_all_subtype_emdat),
    'country' : unique_country_names, 
    'startYear' : np.arange(1980, 2025), 
    'startMonth' : np.arange(1, 13), 
    'startDay' : np.arange(1, 32), 
    'endYear' : np.arange(1980, 2025), 
    'endMonth' : np.arange(1, 13), 
    'endDay' : np.arange(1, 32), 
    
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


# Functions for accuracy computation with cosine similarity method
def calculate_precision_per_report(df_chat, df_labelled, precision_columns_list, 
                                   unique_dict=unique_dict, 
                                  grouping_columns = ["hazardType", "hazardSubtypes", "country", "startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay"]):
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
        tmp_labelled[grouping_columns] = tmp_labelled[grouping_columns].fillna('missing')
        tmp_labelled_event = tmp_labelled.groupby(grouping_columns)
        
        tmp_chat[grouping_columns] = tmp_chat[grouping_columns].fillna('missing')
        tmp_chat_event = tmp_chat.groupby(grouping_columns)

        for precision_column in precision_columns_list:
            if precision_column in grouping_columns : 
                index = grouping_columns.index(precision_column)

                tmp_labelled_event_unique = [haz[index] for haz in tmp_labelled_event.groups.keys()]
                tmp_chat_event_unique = [haz[index] for haz in tmp_chat_event.groups.keys()]
                
                #For Hazard and Country, accuracy is computed by checking is the found attributes are matching
                if precision_column in ["hazardType", "hazardSubtypes", "country", "startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay"] :
                    unique_list = unique_dict[precision_column]

                    # Create binary vectors for the two lists
                    vector1 = [1 if hazard in sorted(tmp_labelled_event_unique) else 0 for hazard in unique_list]
                    vector2 = [1 if hazard in sorted(tmp_chat_event_unique) else 0 for hazard in unique_list]
                    
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
                    #Compute the Jaccard distance 
                    set1 = set(tmp_labelled_event_unique)
                    set2 = set(tmp_chat_event_unique)
                    intersection = set1.intersection(set2)
                    union = set1.union(set2)
                    jaccard_dist = len(intersection) / len(union) if union else 0
                    
                    results[precision_column]["psum"] += jaccard_dist
                    results[precision_column]["count"] += 1

                    # # Create binary vectors for the two lists
                    # n_tmp = sum(1 for value in tmp_labelled[precision_column].unique() if (value != 'NULL') and (value != "missing"))
                    # n_tmp2 = sum(1 for value in tmp_chat[precision_column].unique() if (value != 'NULL') and (value != "missing"))
    
                    # #cos_sim = cosine_similarity(vector1, vector2)[0][0]
                    # if n_tmp != 0 :
                    #     results[precision_column]["psum"] += n_tmp2/n_tmp
                    #     results[precision_column]["count"] += 1

            #If the column for accuracy is not part of the grouping
            #Compare the list of unique information found and compute the Jaccard Similarity 
            else : 
                # n_tmp = sum(1 for value in tmp_labelled[precision_column].unique() if (value != 'NULL') and (value != "missing"))
                # n_tmp2 = sum(1 for value in tmp_chat[precision_column].unique() if (value != 'NULL') and (value != "missing"))
                # if n_tmp != 0 :
                #     results[precision_column]["psum"] += n_tmp2/n_tmp
                #     results[precision_column]["count"] += 1
                set1 = set(tmp_labelled[precision_column])
                set2 = set(tmp_chat[precision_column])
                intersection = set1.intersection(set2)
                union = set1.union(set2)
                jaccard_dist = len(intersection) / len(union) if union else 0
                
                results[precision_column]["psum"] += jaccard_dist
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

from collections import Counter
# Compute accuracy with recall, precision and f1 score 
def calculate_recall_precision_f1_per_report(df_chat, df_labelled, 
                                   precision_columns_list = ["hazardType", "hazardSubtypes", "country"], 
                                   unique_dict=unique_dict, 
                                   grouping_columns = ["hazardType", "hazardSubtypes", "country", "startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay"]):
    '''
    df_chat : Test DataFrame
    df_labelled : Labbeled DataFrame

    unique_dist : Dictionnary listing all the possible values. Used of the hazardType, hazardSubtypes and country
    '''
    # Replace "nan" with empty string in df2 for specified columns
    scores = ["recall", "precision", "f1_score"]
    
    for column in precision_columns_list:
        df_labelled[column] = ["" if str(value) == "nan" else value for value in df_labelled[column]]

    # Initialize results dictionary
    results = {col: {"precision": 0, "recall": 0, "f1_score": 0, "count": 0} for col in precision_columns_list}

    # Group by 'doi' and calculate precision for each column
    for id, df_chat_rep in df_chat.groupby("appealCode"):
        tmp_labelled = df_labelled[df_labelled["appealCode"] == id].reset_index(drop=True)
        tmp_chat = df_chat_rep.reset_index(drop=True)

        #Group by event  
        tmp_labelled[grouping_columns] = tmp_labelled[grouping_columns].fillna('missing')
        tmp_labelled_event = tmp_labelled.groupby(grouping_columns)
        
        tmp_chat[grouping_columns] = tmp_chat[grouping_columns].fillna('missing')
        tmp_chat_event = tmp_chat.groupby(grouping_columns)

        for precision_column in precision_columns_list:
            if precision_column in grouping_columns : 
                index = grouping_columns.index(precision_column)
    
                #Select the unique set
                vector1 = [haz[index] for haz in tmp_labelled_event.groups.keys()]
                vector2 = [haz[index] for haz in tmp_chat_event.groups.keys()]

                #set1, set2 = set(vector1), set(vector2)
                counter1, counter2 = Counter(vector1), Counter(vector2)
                # print("counter1", counter1, "vector1", vector1)
                # print("counter2", counter2, "vector2", vector2)

                TP = sum((counter1 & counter2).values())  # Intersection of both lists, keeping counts
                FP = sum((counter2 - counter1).values())  # Extra occurrences in vector2
                FN = sum((counter1 - counter2).values())

                # print("TP : ", TP, "FP : ", FP, "FN", FN)
                # TP = len(set1 & set2)  
                # FP = len(set2 - set1)
                # FN = len(set1 - set2)

                precision = TP / (TP+FP) if (TP + FP)>0 else 0
                recall = TP / (TP+FN) if (TP+FN)>0 else 0
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

                results[precision_column]["precision"] += precision
                results[precision_column]["recall"] += recall
                results[precision_column]["f1_score"] += f1_score
                results[precision_column]["count"] +=1 
                
                # unique_list = unique_dict[precision_column]
                
                # # Create binary vectors for the two lists
                # vector1 = [1 if hazard in sorted(tmp_labelled_event_unique) else 0 for hazard in unique_list]
                # vector2 = [1 if hazard in sorted(tmp_chat_event_unique) else 0 for hazard in unique_list]

                # TP = np.sum(vector1[np.where(vector1 == vector2)[0]])#np.sum(np.minimum(vector1, vector2))
                # v1_v2 = list(set(vector2) - set(vector1))
                # FN = v1_v2[np.where(v1_v2>=0)].sum()
                # # index_0_v1 = np.where(vector1 == 0)[0]
                # # index_0_v2 = np.where(vector2 == 0)[0]
                # # TN = len(np.intersect1d(index_0_v1, index_0_v2))
                # v2_v1 = list(set(vector2) - set(vector1))
                # FP = v2_v1[np.where(v2_v1>=0)].sum()
                # precision = TP / (TP+FP)
                # recall = TP / (TP +FN)
                # f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

                results[precision_column]["precision"] += precision
                results[precision_column]["recall"] += recall
                results[precision_column]["f1_score"] += f1_score
                results[precision_column]["count"] +=1 
            else : 
                vector1 = tmp_labelled[precision_column].unique()
                vector2 = tmp_chat[precision_column].unique()

                set1, set2 = set(vector1), set(vector2)
                TP = len(set1 & set2)  
                FP = len(set2 - set1)
                FN = len(set1 - set2)

                precision = TP / (TP+FP) if (TP + FP)>0 else 0
                recall = TP / (TP+FN) if (TP+FN)>0 else 0
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

                results[precision_column]["precision"] += precision
                results[precision_column]["recall"] += recall
                results[precision_column]["f1_score"] += f1_score
                results[precision_column]["count"] +=1 
            
    # Calculate precision and create a DataFrame
    accuracy_values = []
    for precision_column in precision_columns_list:
        acc_score = []
        for score in scores :
            if results[precision_column]["count"] > 0: 
                acc = results[precision_column][score] / results[precision_column]["count"]
            else:
                acc = float('nan')  # Handle case where there is no data to calculate precision
            #print(acc)
            acc_score.append(acc)
        accuracy_values.append(acc_score)

    precision_df = pd.DataFrame(accuracy_values, index=precision_columns_list, columns=scores)
    return precision_df

# Compute distance in locations
def centeroidnp(arr):
    length = arr.shape[0]
    sum_x = np.sum(arr[:, 0])
    sum_y = np.sum(arr[:, 1])
    return sum_x/length, sum_y/length

def centroid_per_event(reports, grouping_columns = ["appealCode", "hazardType", "hazardSubtypes", "country"]) :
    """
    Group per event defined with grouping columns 
    """
    reports_centroids = pd.DataFrame(columns = grouping_columns+["longitude", "latitude"])
    
    reports[grouping_columns] = reports[grouping_columns].fillna('missing')
    reports_events = reports.groupby(grouping_columns)

    #Compute the centroid per event 
    keys_events = reports_events.groups.keys()
    
    #Compute the accuracy per event 
    for event in keys_events:
        report_event_loop = reports_events.get_group(event)         
        coordinates_event_loop = np.column_stack((report_event_loop["longitude"], report_event_loop["latitude"]))
        centroid = centeroidnp(coordinates_event_loop)
        
        report_event_centroid = pd.DataFrame([event], columns=grouping_columns)
        report_event_centroid['longitude'] = centroid[0]
        report_event_centroid['latitude'] = centroid[1]
        reports_centroids = pd.concat([reports_centroids, report_event_centroid], axis=0)
    return reports_centroids

def compute_distance(df):
    """
    Compute the geodesic distance (in km) between two points given by 
    (longitude, latitude) and (longitude_chat, latitude_chat).
    Returns NaN if any coordinate is NaN.
    """
    def haversine(row):
        if pd.isna(row['longitude']) or pd.isna(row['latitude']) or pd.isna(row['longitude_chat']) or pd.isna(row['latitude_chat']):
            return np.nan
        return geodesic((row['latitude'], row['longitude']), (row['latitude_chat'], row['longitude_chat'])).km
    
    df['distance_km'] = df.apply(haversine, axis=1)
    return df