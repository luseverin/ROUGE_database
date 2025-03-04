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
                # print(row.region)
                regions = ast.literal_eval(row.region)
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