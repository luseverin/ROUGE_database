import pandas as pd
import json
from collections import Counter
import numpy as np
import re
import pycountry
from sklearn.metrics.pairwise import cosine_similarity
import copy as cp


unique_hazards = ['Drought', 'Flood', 'Storm', 'Tornado', 'Storm surge', 'Heatwave', 'Coldwave', 'Mass movement', 'Cyclone', 'Tidal Wave', 'Wildfire'] 
unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
unique_country_names = [country.name for country in pycountry.countries]
pattern = '|'.join(map(re.escape, unique_country_names))
unique_dict = {
    'Hazard' : unique_hazards, 
    'Country' : unique_countries_ISO
}

def country_name_to_iso3(name):
    try:
        country = pycountry.countries.lookup(name)
        return country.alpha_3
    except LookupError:
        return None

# Convert json to dataframe 
def clean_output_df(results_json, out_cols=['Hazard','Country','Location','Start_Date','End_Date']):
    df_all_list = []
    for report_id, report in results_json.items():
        results = report['results']
        results_process = cp.deepcopy(results)
        results_process = re.sub('[\{\}]', '', results_process)
        results_process= results_process.split("\n")
        results_process = results_process[1: -1]
        columns=['Hazard','Country','Location','Start_Date','End_Date']
        #df_results = pd.DataFrame(columns=columns)
        df_list = []
        haz_list = []
        dict_results = dict()
        for i, pair in enumerate(results_process[:]):
            #print(str(i)+": "+pair)
            if len(pair.split(":")) == 2:
                key, value = pair.split(":")
            else:
                pass
            key = re.sub("[\", ]","",key)  

            if key == 'Hazard':
                haz_list.append(re.sub("[\", ]","",key))
                dict_haz = cp.copy(results_process[i:i+5]) 
                dict_res={}
                for j in np.arange(i,i+5):
                    pairj = results_process[j]
                    keyj, valuej = pairj.split(":")
                    keyj = re.sub("[\", ,,]","",keyj)
                    valuej = re.sub("[\",\[,\]]","",valuej)
                    dict_res[keyj] = valuej[1:]#valuej
                df_list.append(pd.DataFrame(dict_res,index=[0]))
            
            df_all = pd.concat(df_list)
            df_all['appealCode'] = report_id

            #Separate if several countries are found  
            expanded_df = pd.DataFrame(columns=df_all.columns)
            for id_row, row in df_all.iterrows() : 
                matched_countries = re.findall(pattern, row['Country'])
                # If more than one country found 
                #if len(matched_countries) > 1 :
                for country in matched_countries:
                    new_row = row.copy()
                    new_row['Country'] = country
                    expanded_df = pd.concat([expanded_df, pd.DataFrame([new_row])], ignore_index=True)
                        
        df_all_list.append(expanded_df)#.append(df_all)
    return pd.concat(df_all_list)

# Functions for accuracy computation 
def calculate_precision(df1, df2, precision_columns_list, unique_dict=unique_dict):
    '''
    df1 : Test DataFrame
    df2 : Labbeled DataFrame
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

        if tmp.shape[0] == tmp2.shape[0]:
            for precision_column in precision_columns_list:
                #For Hazard and Country, accuracy is computed by checking is the found attributes are matching 
                if precision_column in ['Hazard', 'Hazard_main', 'Country'] : 
                    unique_list = unique_dict[precision_column]
                    
                    # Create binary vectors for the two lists
                    vector1 = [1 if hazard in sorted(tmp[precision_column]) else 0 for hazard in unique_list]
                    vector2 = [1 if hazard in sorted(tmp2[precision_column]) else 0 for hazard in unique_list]
        
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
def calculate_precision_v2(df1, df2, precision_columns_list, unique_dict=unique_dict):
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
    
