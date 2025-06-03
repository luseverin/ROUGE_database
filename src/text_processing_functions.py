import re
import numpy as np
import pandas as pd
import ast
import spacy
from text_to_num import text2num
from number_spacy import find_numbers
from spacy.tokens import Span
from pint import UnitRegistry



nlp = spacy.load("en_core_web_sm")

# Change the type of hazard to the modified version
# Caution, several hazards can be present in 'disasterTypeReclassified'
def change_hazard(reports, dict_hazards_grouped):
    reports_changed = []
    hazards = dict_hazards_grouped.keys()

    #Loop over the repotrs
    for rep in reports :
        #Separate the hazards into individual types
        disasters_list = rep['disasterTypeReclassified'].split(', ')
        new_disasters = []
        for disaster in disasters_list :
            if disaster in hazards :
                for haz in hazards :
                    if disaster in dict_hazards_grouped[haz] :
                        new_disasters.append(disaster)
        #print(new_disasters)
        rep['disasterTypeReclassified'] = np.unique(new_disasters).tolist()

        # Save the report if at least one natural hazard is found
        #print(len(rep['disasterTypeReclassified']))
        if len(rep['disasterTypeReclassified']) != 0 :
            reports_changed.append(rep)
    return reports_changed

# Define hazard types based on keywords
def check_hazard_type_keyword(text, hazard_patterns):
    text = text.lower()
    hazards = []
    for hazard, pattern in hazard_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            hazards.append(hazard)

    return hazards

# Function to clean the text
#def clean_text(text):
#    # Remove hyperlinks
#    text = re.sub(r'http\S+|www\S+', '', text)
#    # Remove special characters except for basic punctuation (e.g., commas, periods)
#    #text = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', text)
#    # Remove newlines
#    text = text.replace('\n', ' ')
#    # Remove multiple spaces
#    text = re.sub(r'\s+', ' ', text).strip()
#    return text

#format numbers
def replace_numbers(text_in):
    """
    Replace numbers written out in words with their numeric equivalent.

    Args:
        text_in (str): The text to replace numbers in.

    Returns:
        str: The text with numbers replaced.
    """
    nlp = spacy.blank('en')
    nlp.add_pipe('find_numbers')
    doc = nlp(text_in)
    # Process the text
    doc = nlp(text_in)

    # Reconstruct text by replacing numbers
    modified_tokens = []
    for token in doc:
        if token.like_num:  # Check if the token is like a number and convert if possible
            try:
                # Convert the token's text to a number
                number = int(token.text) if token.text.isdigit() else text2num(token.text, "en")
                modified_tokens.append(str(number))
            except ValueError:
                modified_tokens.append(token.text)  # If conversion fails, keep the original
        else:
            modified_tokens.append(token.text)

    # Join the tokens back into a string
    return " ".join(modified_tokens)


def replace_commas_in_numbers(text):
    # Replace commas in numbers
    """
    Replace commas in numbers.

    For example, "1,000" is replaced with "1000".
    """
    return re.sub(r'(?<=\d),(?=\d)', '', text)


# Function to convert and replace units in a sentence
def standardize_units(text):

    ureg = UnitRegistry()

    # Define unit conversion mapping
    unit_mapping = {
        "acre": "km**2",
        "acres": "km**2",
        "feet": "m",
        "foot": "m",
        "ft": "m",
        "meter": "m",
        "metres": "m",
        "kilometers": "km",
        "kilometres": "km",
        "hectares": "km**2",
        "ha": "km**2",
        "squared kilometers": "km**2",
        "square kilometers": "km**2",
        "square km": "km**2",
        "pounds": "kg",
        "lbs": "kg",
        "tons": "ton",
        "tonnes": "ton"
    }
    doc = nlp(text)
    new_text = text

    for token in doc:
        # Check if token is a number followed by a unit
        if token.like_num:
            #if token can be converted to float, proceed to conversion else continue
            try :
                num = float(token.text)
            except ValueError:
                continue
            next_token = token.nbor(1) if token.i + 1 < len(doc) else None

            if  next_token and next_token.text.lower() in unit_mapping:
                unit = next_token.text.lower()
                si_unit = unit_mapping[unit]

                # Perform conversion
                quantity = num * ureg(unit)
                converted_quantity = quantity.to(si_unit)
                converted_value = converted_quantity.magnitude
                converted_unit = converted_quantity.units

                # Replace in the text
                replacement = f"{converted_value:.8g} {converted_unit}"
                old = f"{token.text} {next_token.text}"
                new_text = new_text.replace(old, replacement)

    return new_text


def clean_text(text, remove_numbers=False, remove_stopwords=False, format_numbers=False):
    # Remove hyperlinks
    text = re.sub(r'http\S+|www\S+', '', text)

    # Remove some special characters, leaving basic punctuation (e.g., commas, periods)
    text = re.sub(r'[^a-zA-Z0-9\s.,!?%]', '', text)

    # Remove numbers if the option is enabled
    if remove_numbers:
        text = re.sub(r'\d+', '', text)

    # Remove newlines
    text = text.replace('\n', ' ')

    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove stopwords if the option is enabled
    if remove_stopwords:
        stop_words = set(stopwords.words('english'))
        text = ' '.join([word for word in text.split() if word.lower() not in stop_words])

    if format_numbers:
        text = replace_numbers(text)
        text = replace_commas_in_numbers(text)

    return text

def extract_entities(text):
    # Process the text with spaCy
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

def extract_causal_relationships(sentence, relationship_list ,hazard_patterns):
    doc = nlp(sentence)
    causes = []

    # Iterate over the tokens in the sentence
    for token in doc:
        #prev_token = doc[token.i - 1]
        #next_token = doc[token.i + 1]
        # Check if the token is a verb and in the list of causal verbs
        if token.lemma_ in relationship_list and token.pos_ == 'VERB':
            # Find the subject (nsubj) and object (dobj) of the verb
            subject = None
            effect = None

            for child in token.children:
                if child.dep_ == 'nsubj' and len(check_hazard_type_keyword(child.text, hazard_patterns)) > 0:  # Subject (the cause)
                    subject = child.text #check_hazard_type_keyword(child.text, hazard_patterns)
                if child.dep_ in ['dobj', 'pobj'] and len(check_hazard_type_keyword(child.text, hazard_patterns)) > 0:  # Object (the effect)
                    effect = child.text #check_hazard_type_keyword(child.text, hazard_patterns)
            # If both subject and object (effect) are found, return the relationship
            if subject and effect:
                causes.append((subject, token.lemma_, effect))

    return causes

def select_hazard_description(text):
    id_top = None
    id_end = None
    for id_s, sentence in enumerate(text) :
        sentence = sentence.lower()
        if (re.search(r"the situation|the disaster|background|description of the crisis|what happened, where and when|description of the disaster|description of the event", sentence, re.IGNORECASE)) and (id_top==None):
            #Save where the text should begin
            id_top = id_s
        if (re.search(r"coordination and partnerships|red cross red crescent action|operational developments|the response so far|summary of|previous operations|current national society actions", sentence, re.IGNORECASE)) and (id_end==None) and (id_top!=None):
            # Fix a minimum of 5 sentences for the description of the hazard
            if ((id_s-id_top) >= 5) :
                id_end = id_s
    return text[id_top:id_end]

