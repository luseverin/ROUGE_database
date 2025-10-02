import pandas as pd
#import json
#from collections import Counter
import numpy as np
#import regex as re
#import pycountry
from sklearn.metrics.pairwise import cosine_similarity
#import copy as cp
from src.geocoding import remove_admin_words
#import ast
#from geopy.distance import geodesic

from sklearn.metrics.pairwise import cosine_similarity

def vectorize(cell_values, unique_values):
    """vectorizing function for categorical columns"""
    #cell_values = list() if not cell_values else cell_values
    cell_values = [cell_values] if not isinstance(cell_values, list) else cell_values
    vector = [1 if unique_value in cell_values else 0 for unique_value in unique_values]
    return np.array(vector)

def make_cosine_matrix(vec_df1, vec_df2, matching_cols):
    """Build cosine similarity matrix based on matching columns of vectorized dataframes"""
    sim_mat = np.full((len(vec_df1), len(vec_df2), len(matching_cols)), np.nan)

    for k, col in enumerate(matching_cols):
        # Convert Series of arrays/lists to 2D numpy arrays
        X = np.stack(vec_df1[col].values) #nsamples, nfeatures
        Y = np.stack(vec_df2[col].values)
        # Compute cosine similarity
        sim_mat[:,:,k] = cosine_similarity(X, Y)
    return sim_mat

def split_nans_df(df,key):
    """split a dataframe into two, according to whether the column key contains nans"""
    not_nan_ids, nan_ids = get_nan_ids(df,key)
    return df.loc[not_nan_ids], df.loc[nan_ids]

def get_nan_ids(df,key):
    """split a dataframe into two, according to whether the column key contains nans"""
    return df[~df[key].isna()].index.values, df[df[key].isna()].index.values

def split_nans(ext_df, lab_df, key, loose_nan_policy=True):
    """
    Split DataFrames into rows with and without NaNs in the given key column.

    Parameters
    ----------
    ext_df : pd.DataFrame
        Extracted DataFrame.
    lab_df : pd.DataFrame
        Labelled DataFrame.
    key : str
        Column name to check for NaN values.
    loose_nan_policy : bool, optional
        If True, allow NaNs from one side to be matched with all rows
        from the other side. Default is True.

    Returns
    -------
    not_nan_ext_df, not_nan_lab_df, nan_ext_df, nan_lab_df : pd.DataFrame
        DataFrames split into NaN and non-NaN subsets according to the policy.
    """
    not_nan_id_ext, nan_id_ext = get_nan_ids(ext_df, key)
    not_nan_id_lab, nan_id_lab = get_nan_ids(lab_df, key)

    # Always define the non-NaN subsets
    not_nan_ext_df = ext_df.loc[not_nan_id_ext]
    not_nan_lab_df = lab_df.loc[not_nan_id_lab]

    # Defaults: no NaN matches
    nan_ext_df = pd.DataFrame()
    nan_lab_df = pd.DataFrame()

    if len(nan_id_ext) and len(nan_id_lab):
        # Both have NaNs → match them separately
        nan_ext_df = ext_df.loc[nan_id_ext]
        nan_lab_df = lab_df.loc[nan_id_lab]

    elif len(nan_id_ext):  # Only ext has NaNs
        if loose_nan_policy:
            nan_ext_df = ext_df.loc[nan_id_ext]
            nan_lab_df = lab_df

    elif len(nan_id_lab):  # Only lab has NaNs
        if loose_nan_policy:
            nan_ext_df = ext_df
            nan_lab_df = lab_df.loc[nan_id_lab]

    return not_nan_ext_df, not_nan_lab_df, nan_ext_df, nan_lab_df

def IoU(geom1, geom2):
    """Compute intersection over union between two geometries."""
    intersection = geom1.intersection(geom2)
    if not intersection.is_empty:
        inter_area = intersection.area
        union_area = geom1.area + geom2.area - inter_area
        return inter_area / union_area if union_area != 0 else 0
    else:
        return 0

def compute_iou(gdf_left, gdf_right):
    """Compute intersections over union between all rows of two geodataframes."""
    # ensure both are in the same CRS
    gdf_left = gdf_left.to_crs(gdf_right.crs)

    # Create empty matrix for IoUs
    iou_matrix = np.zeros((len(gdf_left), len(gdf_right)))

    ##only compute ious on intersections to speed up
    #joined = gpd.sjoin(gdf_left, gdf_right, how="inner", predicate="intersects")

    # Compute pairwise IoUs
    for i, geom_left in enumerate(gdf_left.geometry):
        for j, geom_right in enumerate(gdf_right.geometry):
            iou_matrix[i, j] = IoU(geom_left, geom_right)

    return iou_matrix

def scaled_value_diff(v1, v2):
    """Scaled difference between two vectors"""
    v1 = np.asarray(v1)
    v2 = np.asarray(v2)
    res = (v1 - v2) / v1
    return res

def max_value_diff(v1, v2):
    """
    Compute maximum of scaled differences between two vectors v1 and v2.

    Parameters
    ----------
    v1, v2 : numpy arrays
        Vectors to compute maximum scaled difference between.

    Returns
    -------
    max_scaled_diff : numpy array
        Maximum of scaled differences between v1 and v2.
    """
    return np.array([np.abs(scaled_value_diff(v1, v2)), np.abs(scaled_value_diff(v2, v1))]).max(axis=0)

def calc_value_sim(v1, v2, clip=(0,1)):
    """Scaled absolute difference between two vectors"""

    return 1 - np.clip(max_value_diff(v1, v2), 0, 1)

def compute_weighted_sim(dist_mat, matching_cols, matching_cols_weights):
    weights = np.array([matching_cols_weights[col] for col in matching_cols])
    weights = weights.reshape((1,1,weights.size))
    return np.nansum(weights*dist_mat, axis=2) / np.nansum(weights)

def find_match_sim(dist_mat, matching_cols, matching_cols_weights):
    """Find best match between extracted and labelled dataframes by maxing weighted similarity"""
    agg_sim  = compute_weighted_sim(dist_mat, matching_cols, matching_cols_weights) #aggregate score for all matching columns (#ext, #lab)
    max_sim = np.max(agg_sim, axis=1) #find max similarity value (#ext)
    tol = 1e-12
    candidates_id_sim = np.argwhere(np.abs(agg_sim - max_sim[:, None]) < tol)
    #candidates_id_sim = np.argwhere(agg_sim == max_sim[:,None]) #possible candidates with max similarity
    id_match_ext, id_match_lab = candidates_id_sim[:,0], candidates_id_sim[:,1]
    return id_match_ext, id_match_lab

def find_match_value(ext_df, lab_df, id_match_ext, id_match_lab):
    """Find best match between extracted and labelled dataframes by minimizing value difference"""
    #calculate diff
    vdiff_candidates = np.abs(ext_df.iloc[id_match_ext]["impactValue"].values -
                              lab_df.iloc[id_match_lab]["impactValue"].values)
    vdiff_candidates = pd.DataFrame({"id_ext":id_match_ext, "id_lab":id_match_lab, "vdiff":vdiff_candidates})
    tol = 1e-12 #tolerance for matching to account for rounding errors
    id_match_ext = np.array([]) #reset idx arrays
    id_match_lab = np.array([])
    for idx, group in vdiff_candidates.groupby("id_ext"):
        min_value = group["vdiff"].min()
        min_idx = np.argwhere(np.abs(group["vdiff"].values - min_value) < tol).flatten()
        id_match_ext = np.append(id_match_ext, group.iloc[min_idx]["id_ext"].values)
        id_match_lab = np.append(id_match_lab, group.iloc[min_idx]["id_lab"].values)

    return id_match_ext.astype(int), id_match_lab.astype(int) #ensure indices are ints

def reindex_match(id_match, orig_df):
    """Reindex match to original index from entire dataframe containing all reports"""
    return orig_df.iloc[id_match]["orig_index"].values.flatten()

def split_nans_sim_matrix(dist_mat, nan_id_ext, nan_id_lab):
    """Split similarity matrix between rows that have impactValue nan and those that don't
    If both ext and lab have nans, only not nan rows are match with not nan rows and vice versa.
    If only one of ext or lab have nans, do a partial separation; allow matches between not nan and nan rows
    If there are non nans in both, non-nan mat is original mat and nan mat is empty
    Returns:
        dist_mat_notna: similarity matrix for rows that have impactValue not nan
        dist_mat_na: similarity matrix for rows that have impactValue nan
    """
    dist_mat_notna = dist_mat.copy()
    dist_mat_na = dist_mat.copy()
    if len(nan_id_ext):
        if len(nan_id_lab):
            #if both ext and lab have nans, put nans from ext and lab in separate mat and remove them from the original
            dist_mat_notna = np.delete(np.delete(dist_mat_notna, nan_id_ext, axis=0), nan_id_lab, axis=1)
            dist_mat_na = dist_mat_na[nan_id_ext, :, :][:,nan_id_lab,:]
        else:
            dist_mat_notna = np.delete(dist_mat_notna, nan_id_ext, axis=0)
            dist_mat_na = dist_mat_na[nan_id_ext, :, :]
    else:
        if len(nan_id_lab):
            dist_mat_notna  = np.delete(dist_mat_notna, nan_id_lab, axis=1)
            dist_mat_na = dist_mat_na[:, nan_id_lab, :]#np.array([])
        else:
            dist_mat_notna = dist_mat_notna
            dist_mat_na = np.array([])
    dist_mat_na = None if dist_mat_na.size == 0 else dist_mat_na
    dist_mat_notna = None if dist_mat_notna.size == 0 else dist_mat_notna
    return dist_mat_notna, dist_mat_na

def match_rows(ext_df, lab_df, ext_vec, lab_vec, matching_cols, similarity_cols, matching_cols_weights, geo_match=False, value_match_pre=False, value_match_post=False):
    """Match rows between extracted and labelled dataframes"""

    #compute cosine distance
    dist_mat = make_cosine_matrix(ext_vec, lab_vec, similarity_cols)
    # geo matching
    if geo_match:
        #expand dist_mat to store results
        iou_mat = compute_iou(ext_df, lab_df)
        dist_mat = np.append(dist_mat, iou_mat[:,:, None], axis=2)

    #calculate diff
    if value_match_pre:
        value_diff = calc_value_sim(ext_df["impactValue"].values.reshape(-1,1),
                                     lab_df["impactValue"].values.reshape(1,-1))
        dist_mat = np.append(dist_mat, value_diff[:,:, None], axis=2)
    else:
        #be sure to remove impactValue from matching_cols
        if "impactValue" in matching_cols:
            matching_cols = matching_cols.copy()
            matching_cols.remove("impactValue")

    #matching based on similarity only
    id_match_ext, id_match_lab = find_match_sim(dist_mat, matching_cols, matching_cols_weights)

    # refine best candidates by minimizing value diff
    if value_match_post:
        id_match_ext, id_match_lab = find_match_value(ext_df, lab_df, id_match_ext, id_match_lab)

    #reindex back in original df
    reid_match_ext = reindex_match(id_match_ext, ext_df)
    reid_match_lab = reindex_match(id_match_lab, lab_df)

    #slice dist_mat only including best candidates to store accuracy results
    accuracy_matrix = dist_mat[id_match_ext, id_match_lab, :]

    #add aggregated similarity scores
    #if value_match_pre or value_match_post:
    #    value_diff_all = np.abs(ext_df.iloc[id_match_ext]["impactValue"].values.reshape(-1,1) -
    #                            lab_df.iloc[id_match_lab]["impactValue"].values.reshape(1,-1)).diagonal()
    #    accuracy_matrix = np.append(accuracy_matrix, value_diff_all.reshape(-1,1), axis=1)
    agg_sim_candidates = compute_weighted_sim(accuracy_matrix, matching_cols, matching_cols_weights)
    accuracy_matrix = np.append(accuracy_matrix, agg_sim_candidates.reshape(-1,1), axis=1)##!! in which order columns are added

    return reid_match_ext, reid_match_lab, accuracy_matrix

## deprecated?
#unique_countries_ISO = [country.alpha_3 for country in pycountry.countries]
#unique_country_names = [country.name for country in pycountry.countries]
#pattern = '|'.join(map(re.escape, unique_country_names))
#unique_dict = {
#    'hazardType' : list(maintype_to_subytpe_emdat.keys()),
#    'hazardSubtypes' : ast.literal_eval(hazard_all_subtype_emdat),
#    'country' : unique_country_names,
#    'startYear' : np.arange(1980, 2025),
#    'startMonth' : np.arange(1, 13),
#    'startDay' : np.arange(1, 32),
#    'endYear' : np.arange(1980, 2025),
#    'endMonth' : np.arange(1, 13),
#    'endDay' : np.arange(1, 32),
#    'impactSubtypes' : impactSubtype_list
#}
#
#list_hazard_words = [
#    "tropical", "cyclone", "hurricane", "typhoon", "storm", "extra-tropical"
#]

#def remove_hazard_words(hazardName_str) :
#    for word in list_hazard_words:
#        hazardName_str = hazardName_str.replace(word, "").strip()
#    hazardName_str = ' '.join(hazardName_str.split())
#    return hazardName_str
#
## Functions for accuracy computation with cosine similarity & Jaccard distance
#def calculate_precision_per_report(df_chat, df_labelled, precision_columns_list,
#                                   unique_dict=unique_dict,
#                                  grouping_columns = ["hazardType", "hazardSubtypes", "country", "startYear", "startMonth", "startDay", #"endYear", "endMonth", "endDay"]):
#    '''
#    df_chat : Test DataFrame
#    df_labelled : Labbeled DataFrame
#
#    unique_dist : Dictionnary listing all the possible values. Used of the hazardType, hazardSubtypes and country
#    '''
#    # Replace "nan" with empty string in df2 for specified columns
#    for column in precision_columns_list:
#        df_labelled[column] = ["" if str(value) == "nan" else value for value in df_labelled[column]]
#
#    # Initialize results dictionary
#    results = {col: {"psum": 0, "count": 0} for col in precision_columns_list}
#
#    # Group by 'doi' and calculate precision for each column
#    for id, df_chat_rep in df_chat.groupby("appealCode"):
#        tmp_labelled = df_labelled[df_labelled["appealCode"] == id].reset_index(drop=True)
#        tmp_chat = df_chat_rep.reset_index(drop=True)
#
#        #Group by event
#        tmp_labelled[grouping_columns] = tmp_labelled[grouping_columns].fillna('missing')
#        tmp_labelled_event = tmp_labelled.groupby(grouping_columns)
#
#        tmp_chat[grouping_columns] = tmp_chat[grouping_columns].fillna('missing')
#        tmp_chat_event = tmp_chat.groupby(grouping_columns)
#
#        for precision_column in precision_columns_list:
#            if precision_column in grouping_columns :
#                index = grouping_columns.index(precision_column)
#
#                tmp_labelled_event_unique = [haz[index] for haz in tmp_labelled_event.groups.keys()]
#                tmp_chat_event_unique = [haz[index] for haz in tmp_chat_event.groups.keys()]
#
#                #For Hazard and Country, accuracy is computed by checking is the found attributes are matching
#                if precision_column in ["hazardType", "hazardSubtypes", "country", "startYear", "startMonth", "startDay", "endYear", #"endMonth", "endDay"] :
#                    unique_list = unique_dict[precision_column]
#
#                    # Create binary vectors for the two lists
#                    if not isinstance(unique_list[0], str) :
#                        tmp_labelled_event_unique = [x for x in tmp_labelled_event_unique if isinstance(x, (int, float))]
#                        tmp_chat_event_unique = [x for x in tmp_chat_event_unique if isinstance(x, (int, float))]
#
#                    vector1 = [1 if hazard in sorted(tmp_labelled_event_unique) else 0 for hazard in unique_list]
#                    vector2 = [1 if hazard in sorted(tmp_chat_event_unique) else 0 for hazard in unique_list]
#
#                    # Convert the vectors to numpy arrays and reshape them
#                    vector1 = np.array(vector1).reshape(1, -1)
#                    vector2 = np.array(vector2).reshape(1, -1)
#
#                    # Compute the cosine similarity
#                    cos_sim = cosine_similarity(vector1, vector2)[0][0]
#                    results[precision_column]["psum"] += cos_sim
#                    results[precision_column]["count"] += 1
#
#                #For Location and Date, the accuracy look is a value is found when one should be found
#                #Do not look at the exact value
#                #elif precision_column in ["startYear", "startMonth", "startDay", "endYear", "endMonth", "endDay"] :
#                else :
#                    #Compute the Jaccard distance
#                    set1 = set(tmp_labelled_event_unique)
#                    set2 = set(tmp_chat_event_unique)
#                    intersection = set1.intersection(set2)
#                    union = set1.union(set2)
#                    jaccard_dist = len(intersection) / len(union) if union else 0
#
#                    results[precision_column]["psum"] += jaccard_dist
#                    results[precision_column]["count"] += 1
#
#                    # # Create binary vectors for the two lists
#                    # n_tmp = sum(1 for value in tmp_labelled[precision_column].unique() if (value != 'NULL') and (value != "missing"))
#                    # n_tmp2 = sum(1 for value in tmp_chat[precision_column].unique() if (value != 'NULL') and (value != "missing"))
#
#                    # #cos_sim = cosine_similarity(vector1, vector2)[0][0]
#                    # if n_tmp != 0 :
#                    #     results[precision_column]["psum"] += n_tmp2/n_tmp
#                    #     results[precision_column]["count"] += 1
#
#            #If the column for accuracy is not part of the grouping
#            #Compare the list of unique information found and compute the Jaccard Similarity
#            else :
#                #Clean string list
#                if precision_column in ['country', 'region', 'city', 'location', 'hazardName'] :
#                    # Convert to lower cases :
#                    tmp_labelled_process = [x.lower() for x in tmp_labelled[precision_column].dropna()]
#                    tmp_chat_process     = [x.lower() for x in tmp_chat[precision_column].dropna()]
#                    if precision_column == 'hazardName' :
#                        tmp_labelled_process = [remove_hazard_words(str(x)) for x in tmp_labelled_process]
#                        tmp_chat_process = [remove_hazard_words(str(x)) for x in tmp_chat_process]
#                    else :
#                        tmp_labelled_process = [remove_admin_words(str(x)) for x in tmp_labelled_process]
#                        tmp_chat_process     = [remove_admin_words(str(x)) for x in tmp_chat_process]
#                    set1 = set(tmp_labelled_process)
#                    set2 = set(tmp_chat_process)
#                else :
#                    set1 = set(tmp_labelled[precision_column])
#                    set2 = set(tmp_chat[precision_column])
#                intersection = set1.intersection(set2)
#                union = set1.union(set2)
#                jaccard_dist = len(intersection) / len(union) if union else 0
#
#                results[precision_column]["psum"] += jaccard_dist
#                results[precision_column]["count"] += 1
#
#    # Calculate precision and create a DataFrame
#    precision_values = []
#    for precision_column in precision_columns_list:
#        if results[precision_column]["count"] > 0:
#            precision = results[precision_column]["psum"] / results[precision_column]["count"]
#        else:
#            precision = float('nan')  # Handle case where there is no data to calculate precision
#        precision_values.append(precision)
#
#    precision_df = pd.DataFrame([precision_values], columns=precision_columns_list)
#    return precision_df
#
#def calculate_precision_per_hazardType(df_chat, df_labelled, precision_columns_list, unique_dict=unique_dict):
#    precision_dict = {}
#    for hazard in unique_dict["hazardType"] :
#        df_chat_haz = df_chat.loc[df_chat.hazardType == hazard].copy()
#        df_labelled_haz = df_labelled.loc[df_labelled.hazardType == hazard].copy()
#        precision_haz = calculate_precision_per_report(df_chat_haz, df_labelled_haz, precision_columns_list, unique_dict)
#        precision_dict[hazard] = precision_haz
#    return precision_dict
#
#def calculate_precision_per_hazardSubtypes(df_chat, df_labelled, precision_columns_list, unique_dict=unique_dict):
#    precision_dict = {}
#    for hazardSubtype in unique_dict["hazardSubtypes"] :
#        df_chat_haz = df_chat.loc[df_chat.hazardSubtypes == hazardSubtype].copy()
#        df_labelled_haz = df_labelled.loc[df_labelled.hazardSubtypes == hazardSubtype].copy()
#        precision_haz = calculate_precision_per_report(df_chat_haz, df_labelled_haz, precision_columns_list, unique_dict)
#        precision_dict[hazardSubtype] = precision_haz
#    return precision_dict
#
####### ACCURACY FOR THE IMPACT
#
#def calculate_accuracy_impact_per_report(df_chat, df_labelled, precision_columns_list,
#                                   unique_dict=unique_dict):
#    '''
#    df_chat : Test DataFrame
#    df_labelled : Labbeled DataFrame
#
#    unique_dist : Dictionnary listing all the possible values. Used of the hazardType, hazardSubtypes and country
#    '''
#    # Replace "nan" with empty string in df2 for specified columns
#    for column in precision_columns_list:
#        df_labelled[column] = ["" if str(value) == "nan" else value for value in df_labelled[column]]
#
#    # Initialize results dictionary
#    results = {col: {"psum": 0, "count": 0} for col in precision_columns_list}
#
#    # Group by 'doi' and calculate precision for each column
#    for id, df_chat_rep in df_chat.groupby("appealCode"):
#        tmp_labelled = df_labelled[df_labelled["appealCode"] == id].reset_index(drop=True)
#        tmp_chat = df_chat_rep.reset_index(drop=True)
#
#        for precision_column in precision_columns_list:
#            # if precision_column in ['country', 'region', 'city', 'location', 'hazardName'] :
#            #         # Convert to lower cases :
#            #         tmp_labelled_process = [x.lower() for x in tmp_labelled[precision_column].dropna()]
#            #         tmp_chat_process     = [x.lower() for x in tmp_chat[precision_column].dropna()]
#            #         if precision_column == 'hazardName' :
#            #             tmp_labelled_process = [remove_hazard_words(str(x)) for x in tmp_labelled_process]
#            #             tmp_chat_process = [remove_hazard_words(str(x)) for x in tmp_chat_process]
#            #         else :
#            #             tmp_labelled_process = [remove_admin_words(str(x)) for x in tmp_labelled_process]
#            #             tmp_chat_process     = [remove_admin_words(str(x)) for x in tmp_chat_process]
#            #         set1 = set(tmp_labelled_process)
#            #         set2 = set(tmp_chat_process)
#            #     else :
#            #         set1 = set(tmp_labelled[precision_column])
#            #         set2 = set(tmp_chat[precision_column])
#
#            #For Hazard and Country, accuracy is computed by checking is the found attributes are matching
#            if precision_column in ["impactSubtypes", "country"] :
#                unique_list = unique_dict[precision_column]
#
#                # # Create binary vectors for the two lists
#                # if not isinstance(unique_list[0], str) :
#                #     set1 = [x for x in set1 if isinstance(x, (int, float))]
#                #     set2 = [x for x in set2 if isinstance(x, (int, float))]
#
#                vector1 = [1 if hazard in sorted(tmp_labelled[precision_column]) else 0 for hazard in unique_list]
#                vector2 = [1 if hazard in sorted(tmp_chat[precision_column]) else 0 for hazard in unique_list]
#
#                # Convert the vectors to numpy arrays and reshape them
#                vector1 = np.array(vector1).reshape(1, -1)
#                vector2 = np.array(vector2).reshape(1, -1)
#
#                # Compute the cosine similarity
#                cos_sim = cosine_similarity(vector1, vector2)[0][0]
#                results[precision_column]["psum"] += cos_sim
#                results[precision_column]["count"] += 1
#
#    # Calculate precision and create a DataFrame
#    precision_values = []
#    for precision_column in precision_columns_list:
#        if results[precision_column]["count"] > 0:
#            precision = results[precision_column]["psum"] / results[precision_column]["count"]
#        else:
#            precision = float('nan')  # Handle case where there is no data to calculate precision
#        precision_values.append(precision)
#
#    precision_df = pd.DataFrame([precision_values], columns=precision_columns_list)
#    return precision_df
#
#
#from collections import Counter
## Compute accuracy with recall, precision and f1 score
#def calculate_recall_precision_f1_per_report(df_chat, df_labelled,
#                                   precision_columns_list = ["hazardType", "hazardSubtypes", "country"],
#                                   unique_dict=unique_dict,
#                                   grouping_columns = ["hazardType", "hazardSubtypes", "country", "startYear", "startMonth", "startDay", #"endYear", "endMonth", "endDay"]):
#    '''
#    df_chat : Test DataFrame
#    df_labelled : Labbeled DataFrame
#
#    unique_dist : Dictionnary listing all the possible values. Used of the hazardType, hazardSubtypes and country
#    '''
#    # Replace "nan" with empty string in df2 for specified columns
#    scores = ["recall", "precision", "f1_score"]
#
#    for column in precision_columns_list:
#        df_labelled[column] = ["" if str(value) == "nan" else value for value in df_labelled[column]]
#
#    # Initialize results dictionary
#    results = {col: {"precision": 0, "recall": 0, "f1_score": 0, "count": 0} for col in precision_columns_list}
#
#    # Group by 'doi' and calculate precision for each column
#    for id, df_chat_rep in df_chat.groupby("appealCode"):
#        tmp_labelled = df_labelled[df_labelled["appealCode"] == id].reset_index(drop=True)
#        tmp_chat = df_chat_rep.reset_index(drop=True)
#
#        #Group by event
#        tmp_labelled[grouping_columns] = tmp_labelled[grouping_columns].fillna('missing')
#        tmp_labelled_event = tmp_labelled.groupby(grouping_columns)
#
#        tmp_chat[grouping_columns] = tmp_chat[grouping_columns].fillna('missing')
#        tmp_chat_event = tmp_chat.groupby(grouping_columns)
#
#        for precision_column in precision_columns_list:
#            if precision_column in grouping_columns :
#                index = grouping_columns.index(precision_column)
#
#                #Select the unique set
#                vector1 = [haz[index] for haz in tmp_labelled_event.groups.keys()]
#                vector2 = [haz[index] for haz in tmp_chat_event.groups.keys()]
#
#                #set1, set2 = set(vector1), set(vector2)
#                counter1, counter2 = Counter(vector1), Counter(vector2)
#                # print("counter1", counter1, "vector1", vector1)
#                # print("counter2", counter2, "vector2", vector2)
#
#                TP = sum((counter1 & counter2).values())  # Intersection of both lists, keeping counts
#                FP = sum((counter2 - counter1).values())  # Extra occurrences in vector2
#                FN = sum((counter1 - counter2).values())
#
#                # print("TP : ", TP, "FP : ", FP, "FN", FN)
#                # TP = len(set1 & set2)
#                # FP = len(set2 - set1)
#                # FN = len(set1 - set2)
#
#                precision = TP / (TP+FP) if (TP + FP)>0 else 0
#                recall = TP / (TP+FN) if (TP+FN)>0 else 0
#                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
#
#                results[precision_column]["precision"] += precision
#                results[precision_column]["recall"] += recall
#                results[precision_column]["f1_score"] += f1_score
#                results[precision_column]["count"] +=1
#
#                # unique_list = unique_dict[precision_column]
#
#                # # Create binary vectors for the two lists
#                # vector1 = [1 if hazard in sorted(tmp_labelled_event_unique) else 0 for hazard in unique_list]
#                # vector2 = [1 if hazard in sorted(tmp_chat_event_unique) else 0 for hazard in unique_list]
#
#                # TP = np.sum(vector1[np.where(vector1 == vector2)[0]])#np.sum(np.minimum(vector1, vector2))
#                # v1_v2 = list(set(vector2) - set(vector1))
#                # FN = v1_v2[np.where(v1_v2>=0)].sum()
#                # # index_0_v1 = np.where(vector1 == 0)[0]
#                # # index_0_v2 = np.where(vector2 == 0)[0]
#                # # TN = len(np.intersect1d(index_0_v1, index_0_v2))
#                # v2_v1 = list(set(vector2) - set(vector1))
#                # FP = v2_v1[np.where(v2_v1>=0)].sum()
#                # precision = TP / (TP+FP)
#                # recall = TP / (TP +FN)
#                # f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
#
#                results[precision_column]["precision"] += precision
#                results[precision_column]["recall"] += recall
#                results[precision_column]["f1_score"] += f1_score
#                results[precision_column]["count"] +=1
#            else :
#                vector1 = tmp_labelled[precision_column].unique()
#                vector2 = tmp_chat[precision_column].unique()
#
#                set1, set2 = set(vector1), set(vector2)
#                TP = len(set1 & set2)
#                FP = len(set2 - set1)
#                FN = len(set1 - set2)
#
#                precision = TP / (TP+FP) if (TP + FP)>0 else 0
#                recall = TP / (TP+FN) if (TP+FN)>0 else 0
#                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
#
#                results[precision_column]["precision"] += precision
#                results[precision_column]["recall"] += recall
#                results[precision_column]["f1_score"] += f1_score
#                results[precision_column]["count"] +=1
#
#    # Calculate precision and create a DataFrame
#    accuracy_values = []
#    for precision_column in precision_columns_list:
#        acc_score = []
#        for score in scores :
#            if results[precision_column]["count"] > 0:
#                acc = results[precision_column][score] / results[precision_column]["count"]
#            else:
#                acc = float('nan')  # Handle case where there is no data to calculate precision
#            #print(acc)
#            acc_score.append(acc)
#        accuracy_values.append(acc_score)
#
#    precision_df = pd.DataFrame(accuracy_values, index=precision_columns_list, columns=scores)
#    return precision_df
#
## Compute distance in locations
#def centeroidnp(arr):
#    length = arr.shape[0]
#    sum_x = np.sum(arr[:, 0])
#    sum_y = np.sum(arr[:, 1])
#    return sum_x/length, sum_y/length
#
#def centroid_per_event(reports, grouping_columns = ["appealCode", "hazardType", "hazardSubtypes", "country"]) :
#    """
#    Group per event defined with grouping columns
#    """
#    reports_centroids = pd.DataFrame(columns = grouping_columns+["longitude", "latitude"])
#
#    reports[grouping_columns] = reports[grouping_columns].fillna('missing')
#    reports_events = reports.groupby(grouping_columns)
#
#    #Compute the centroid per event
#    keys_events = reports_events.groups.keys()
#
#    #Compute the accuracy per event
#    for event in keys_events:
#        report_event_loop = reports_events.get_group(event)
#        coordinates_event_loop = np.column_stack((report_event_loop["longitude"], report_event_loop["latitude"]))
#        centroid = centeroidnp(coordinates_event_loop)
#
#        report_event_centroid = pd.DataFrame([event], columns=grouping_columns)
#        report_event_centroid['longitude'] = centroid[0]
#        report_event_centroid['latitude'] = centroid[1]
#        reports_centroids = pd.concat([reports_centroids, report_event_centroid], axis=0)
#    return reports_centroids
#
#def compute_distance(df):
#    """
#    Compute the geodesic distance (in km) between two points given by
#    (longitude, latitude) and (longitude_chat, latitude_chat).
#    Returns NaN if any coordinate is NaN.
#    """
#    def haversine(row):
#        if pd.isna(row['longitude']) or pd.isna(row['latitude']) or pd.isna(row['longitude_chat']) or pd.isna(row['latitude_chat']):
#            return np.nan
#        return geodesic((row['latitude'], row['longitude']), (row['latitude_chat'], row['longitude_chat'])).km
#
#    df['distance_km'] = df.apply(haversine, axis=1)
#    return df