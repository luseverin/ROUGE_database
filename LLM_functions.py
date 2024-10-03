import pandas as pd
import json
from collections import Counter
import numpy as np
import re
import pycountry
from sklearn.metrics.pairwise import cosine_similarity


unique_hazards = ['Drought', 'Flood', 'Storm', 'Tornado', 'Storm surge', 'Heatwave', 'Coldwave', 'Mass movement', 'Cyclone', 'Tidal Wave', 'Wildfire'] 
unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
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
                if precision_column in ['Hazard', 'Country'] : 
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
                elif precision_column in ['Locations', 'Start_Date', 'End_Date'] : 
                    # Create binary vectors for the two lists
                    n_tmp = sum(1 for value in tmp[precision_column] if value != 'NULL')
                    n_tmp2 = sum(1 for value in tmp2[precision_column] if value != 'NULL')

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
