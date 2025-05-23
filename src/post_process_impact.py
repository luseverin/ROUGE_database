import pycountry
import pandas as pd
import json
from collections import Counter
import numpy as np
import re
import copy as cp
import ast
import spacy
from src.impact_def import *

nlp = spacy.load("en_core_web_sm")

## Convert text to list object
def parse_to_list(text):
    if isinstance(text, str):
        try:
            result = ast.literal_eval(text)
            if isinstance(result, list):
                return result
        except (ValueError, SyntaxError):
            pass
    return text 

def df_parse_to_list(df, columns_to_parse=["nathaz_text"]) : 
    for col in columns_to_parse : 
        df[col] = df[col].apply(parse_to_list)
    return df 

## Correct sentences outputed by chat
def find_most_similar_sentence(row, text, sentence_query):
    sentences = row[text]
    if isinstance(row[sentence_query], list) :
        query = row[sentence_query][0]
    else : 
        print(row[sentence_query])
        query = row[sentence_query]
    
    if not isinstance(query, str) or not sentences:
        return "", 0.0

    query_doc = nlp(query)
    max_score = -1.0
    best_sentence = ""
    
    for sentence in sentences:
        sent_doc = nlp(sentence)
        score = query_doc.similarity(sent_doc)
        if score > max_score:
            max_score = score
            best_sentence = sentence

    # print(f"LLM sentence : {query}, Best Sentence : {best_sentence}, Similarity : {max_score} ")
    return best_sentence, max_score

def compute_similarity_per_row(df, 
                               text='nathaz_text',
                               sentence_query='impactsAnnotation'):
    similarity_results = df.apply(
        lambda row: find_most_similar_sentence(row, text, sentence_query),
        axis=1
    )
    df[sentence_query+"_corrected"] = similarity_results.apply(lambda x: x[0])
    df[sentence_query+'_similarity_score'] = similarity_results.apply(lambda x: x[1])
    return df

## Correct units per impactCategory 

human_units = ["households", "houses", "homes", "families", "family"]
def correct_units_human(df_input):
    df = cp.deepcopy(df_input)
    for id_row, row in df.iterrows():
        impact_type = row["impactType"]
        unit = row["impactUnit"]
        
        # Check if impactType has a standard unit defined
        if (impact_type in impact_subtypes_human_desc_dict and
            unit != impact_subtypes_unit_dict[impact_type]):
            
            if unit in human_units:
                # Multiply the value by 4 and assign the correct unit
                df.at[id_row, "impactValue"] = row["impactValue"] * 4
                df.at[id_row, "impactUnit"] = "people"
    
    return df

