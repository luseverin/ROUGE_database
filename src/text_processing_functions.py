import regex as re
import numpy as np
import pandas as pd
import ast
import spacy
import unicodedata
from text_to_num import text2num
from number_spacy import find_numbers
from spacy.tokens import Span
from pint import UnitRegistry

import nltk
from nltk.tokenize import sent_tokenize
nltk.download('punkt_tab')
nltk.download('punkt')  # Download sentence tokenizer
nltk.download('stopwords') # Download stopwords

## load spacy nlp
nlp = spacy.load("en_core_web_sm")
nlp.add_pipe("language_detector")
#nlp.add_pipe('find_numbers')

# Define unit conversion mapping
unit_mapping = {
    'km': 'km',
    'km**2': 'km**2',
    'miles': 'km',
    'kg': 'kg',
    'm**3': 'm**3',
    "acre": "km**2",
    "feet": "km",
    "meter": "km",
    "hectare": "km**2",
    "ha": "km**2",
    "mi**2": "km**2",
    "m**2": "km**2",
    "ft**2": "km**2",
    "pound": "kg",
    "ton": "kg",
    "tonne": "kg",
    "liter": "m**3",
    "l": "m**3",
    "gallon": "m**3",
}
std_unit_kw_reclass = {
                    'km' : [r"(?<!\b(squared?)\b)\s\b(kilometers?|kilometres?|kms?)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2)\b)"],
                    'km**2' : [r"\b(?<=(squared?))\s*(kilometers?|kilometres?|kms?)\b",
                            r"\b(kilometers?|kilometres?|kms?)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)"],
                    'm**2' : [r"\b(?<=(squared?)\b)\s*\b(meters?|metres?|m)\b",
                            r"\b(meters?|metres?|m)\s?\b\b(\*\*\s*2|\*\*2|\^2|²|square|squared|2)\b(?<!\.\d)"],
                    'mi**2' : [r"\b(?<=(squared?))\s*(mile|miles|mi)\b",
                            r"\b(mile|miles|mi)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)"],
                    'ft**2' : [r"\b(?<=(squared?))\s*(feet|foot|ft)\b",
                            r"\b(feet|foot|ft)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)"],
                    'kg' : [r"\b(kgs?|kilograms?)\b"],
                    'm**3' : [r"\b(?<=(cube|cubic))\s*(meters?|metres?|m)\b",
                            r"\b(meters?|metres?|m)s?\s?(\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)\b(?<!\.\d)"],
                    "acre": [r"\b(acres?)\b"],
                    "feet": [r"(?<!\b(squared?|cube|cubic)\s*)\b(feet|foot|ft)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3))\b(?!\s+\d+(\.\d+)?)"],
                    "hectare": [r"\b(hectares?|ha|hectors?)\b"],
                    "ton": [r"\b(?<!\b(metric)\s*)(ton|tons)\b"],
                    "tonne": [r"\b(tonne|tonnes|metric ton|metric tons)\b"],
                    "pound": [r"\b(pounds|lbs?)\b"],
                    "meter": [r"(?<!\b(squared?|cube|cubic)\s*)\b(meters?|metres?|m)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3))\b(?!\s+\d+(\.\d+)?)"],
                    "liter": [r"\b(liters?|litres?|l)\b"],
                    "miles": [r"(?<!\b(squared?|cube|cubic)\s*)\b(miles?|mi)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3))\b(?!\s+\d+(\.\d+)?)"],
                    "gallon": [r"\b(gallons|gal)\b"],
}

## Detect language
#https://spacy.io/universe/project/spacy_fastlang
def detect_language(text):
    """
    Detects the language of the given text.

    Args:
        text (str): Text to detect the language of.

    Returns:
        str: Detected language.
    """
    doc = nlp(text)
    return doc._.language  # Check if detected language is English

def written_num(text, lang="en"):
    """Version of like_num using text2num. Able to handle plurals but does not
    detect literal number (e.g. "3")"""
    try:
        text2num(text, lang)
        return True
    except ValueError:
        return False

def is_float_digit(text):
    """
    Check if the given text can be converted to a float.

    Args:
        text (str): The text to check.

    Returns:
        bool: True if the text can be converted to a float, False otherwise.
    """

    try:
        float(text)  # Attempt to convert the text to a float
        return True
    except ValueError:
        return False

#format numbers
def replace_numbers(text_in):
    """
    Replace numbers written out in words with their numeric equivalent.

    Args:
        text_in (str): The text to replace numbers in.

    Returns:
        str: The text with numbers replaced.
    """
    # Process the text
    doc = nlp(text_in)

    # Reconstruct text by replacing numbers
    modified_tokens = []
    last_token_modified = False
    for token in doc:

        #first replace written-out numbers
        if written_num(token.text) and token.pos_ != "PROPN": #must not be part of a proper noun
            number = float(text2num(token.text, "en"))
            #if the next tokens could be a unit and if the previous token is a number replace by the multiple of the two numbers
            next_tokens = take_n_neighb_tokens(token, 2)
            next_tokens = " ".join([next_token.text.lower() for next_token in next_tokens]) if next_tokens else ""
            prev_token = take_n_neighb_tokens(token, -1) #nlp.tokenizer(modified_tokens[-1])[0] if len(modified_tokens) > 0 else None
            prev_token = prev_token[0] if prev_token else None
            if last_token_modified or (prev_token and is_float_digit(prev_token.text)):#and could_be_unit(next_tokens) do not necessarily ask to be a unit?
                if modified_tokens[-1] == " ": #remove whitespace
                    modified_tokens.pop()
                prev_number = float(modified_tokens.pop())
                number *= prev_number
            modified_tokens.append(str(number))
            last_token_modified = True #mark that the last token was modified

        else: #if no number identified, keep as is
            modified_tokens.append(token.text)
            last_token_modified = False

        if token.whitespace_:#keep whitespace
            modified_tokens.append(token.whitespace_)

    # Join the tokens back into a string
    return "".join(modified_tokens)


def replace_commas_in_numbers(text):
    # Replace commas in numbers
    """
    Replace commas in numbers.

    For example, "1,000" is replaced with "1000".
    """
    return re.sub(r'(?<=\d),(?=\d)', '', text)

def replace_count_suffixes(text):
    #do not convert m to milions as might be metre unit!
    """
    Replace count suffixes in text such as 10k => 10000, 1.5m => 1500000.
    """
    return re.sub(
        r'(\d+(\.\d+)?)([kKmM])\b',  # Updated regex for floating-point numbers
        lambda match: str(
            float(match.group(1)) * {'k': 1000, 'K': 1000, 'm': 1000000, 'M': 1000000}[match.group(3).upper()]
        ),
        text
    )

# Function to convert and replace units in a sentence
def take_n_neighb_tokens(token, n):
    """Return n neighboring tokens of a spacy token"""
    neighb_tokens = []
    trange = range(1, n+1) if n > 0 else range(n, 0)
    for i in trange:
        try:
            neighb_tokens.append(token.nbor(i))
        except IndexError:
            break
    if len(neighb_tokens) == 0:
        return None
    return neighb_tokens

def could_be_unit(text):
    """
    Check if a given string could be a unit.

    Return True if any of the regex patterns in std_unit_kw_reclass
    match the given string, else False.
    """
    pot_units = [target_unit for target_unit, unit_patterns in std_unit_kw_reclass.items() if any([re.search(pattern, text, re.IGNORECASE) for pattern in unit_patterns])]
    return len(pot_units) > 0

def standardize_units(text):
    """Standardize units to a common baseline in text"""

    ureg = UnitRegistry()
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
            next_tokens = take_n_neighb_tokens(token, 2) # take next 2 tokens

            if next_tokens:
                next_tokens = " ".join([next_token.text.lower() for next_token in next_tokens])
                pot_units = [target_unit for target_unit, unit_patterns in std_unit_kw_reclass.items() if np.any([re.search(pattern, next_tokens, re.IGNORECASE) for pattern in unit_patterns])]
                if len(pot_units) == 0:
                    continue
                elif len(pot_units) > 1:
                    raise ValueError(f"Multiple potential units found for token: {token.text} {next_tokens}")

                unit = pot_units[0]
                si_unit = unit_mapping[unit]

                # Perform conversion
                quantity = num * ureg(unit)
                converted_quantity = quantity.to(si_unit)
                converted_value = converted_quantity.magnitude
                converted_unit = converted_quantity.units

                # Replace in the text
                replacement = f"{converted_value:.8g} {converted_unit}"
                old = f"{token.text} {next_tokens}"
                new_text = new_text.replace(old, replacement)

    return new_text


def clean_text(text, remove_numbers=False, remove_stopwords=False):
    # Remove hyperlinks
    """
    Clean the text by removing special characters, numbers, newlines, and multiple spaces.

    The function takes an optional argument, `remove_numbers`, which is a boolean that specifies whether numbers should be removed from the text.

    The function takes an optional argument, `remove_stopwords`, which is a boolean that specifies whether stopwords should be removed from the text.

    The function returns the cleaned text.
    """
    text = re.sub(r'http\S+|www\S+', '', text)

    # Remove some special characters, leaving basic punctuation (e.g., commas, periods)
    text = re.sub(r"ﬀ", "ff", text) #need to replace special ff and ae first
    text = re.sub(r"æ", "ae", text)
    #text = re.sub(r'[^a-zA-Z0-9\s.,!?%-/]', '', text)

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

    return text

def fix_pdf_text(text):
    """
    Clean up text extracted from PDFs.

    This function removes invisible characters, removes random whitespaces, and
    converts to lowercase. It is intended to be used on text extracted from PDFs.

    Parameters
    ----------
    text : str
        The text to be cleaned up.

    Returns
    -------
    str
        The cleaned up text.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.replace('\x00', '')
    text= re.sub(r"\s+", " ", text.lower()).strip() #remove random whitespaces
    return text

def select_hazard_description(text, match_above=True):
    """
    Selects a subset of text that describes the hazard event, given a list of sentences.

    The function searches for the first occurrence of a phrase that matches a description of the hazard event, and then selects all sentences until it reaches a phrase that matches a description of the response. If no phrases are found, the whole text is returned.

    Parameters
    ----------
    text : list of str
        List of sentences to be processed
    match_above : bool, optional
        Whether to start the selection from the first match of the hazard description. If False, the function will start from the beginning of the text.

    Returns
    -------
    list of str
        A subset of the original text, describing the hazard event
    """
    id_top = 0
    id_end = None
    for id_s, sentence in enumerate(text) :
        sentence = sentence.lower()
        #match_top = re.search(r"(?:situation analysis|background|description of the crisis|what happened, where and when|description of the disaster|description of the event)\s*(.*)", sentence, re.IGNORECASE)#the situation|the disaster
        match_top = re.search(r"operation summary|situation analysis|background|description of the crisis|what happened, where and when|description of the disaster|description of the event", sentence, re.IGNORECASE)
        if match_above and match_top and (id_top==0):
            #Save where the text should begin
            id_top = id_s
            continue
            #text[id_top] = match_top.group(1)

        #match_end = re.search(r"^(.*?)(?=\s*(operational strategy|coordination and partnerships|red cross red crescent action|operational developments|the response so far|summary of|previous operations|current national society actions))", sentence, re.IGNORECASE)
        match_end = re.search(r"coordination and partnerships|operational strategy|red cross red crescent action|operational developments|summary of response|the response so far|previous operations|current national society actions", sentence, re.IGNORECASE)#summary of
        if match_end and id_end==None:
            if id_s - id_top < 10:
                continue #too short
            id_end = id_s+2
            break
            #text[id_end] = match_end.group(0)
    #keep everything if no match
    id_end = len(text)-1 if id_end == None else id_end
    return text[id_top:id_end]

# Change the type of hazard to the modified version
# Caution, several hazards can be present in 'disasterTypeReclassified'
def change_hazard(reports, dict_hazards_grouped):
    """
    Changes the type of hazard in the 'disasterTypeReclassified' column of a list of reports based on a dictionary of grouped hazards.

    Args:
        reports (list): List of reports with 'disasterTypeReclassified' key.
        dict_hazards_grouped (dict): Dictionary of grouped hazards. The keys are the modified hazard types and the values are lists of the original hazard types.

    Returns:
        list: List of reports with modified 'disasterTypeReclassified' column.
    """
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
    """
    Checks if any of the hazard types in hazard_patterns are present in the text based on their keywords.

    Args:
        text (str): The text to search for hazard types.
        hazard_patterns (dict): Dictionary of hazard types and their corresponding keywords.

    Returns:
        list: List of hazard types found in the text.
    """
    text = text.lower()
    hazards = []
    for hazard, pattern in hazard_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            hazards.append(hazard)

    return hazards

def extract_entities(text):
    # Process the text with spaCy
    """
    Extract named entities from a text.

    The function takes a text as input and processes it with spaCy to extract named entities.
    The function returns a list of tuples, where each tuple contains the text of the entity and its label.

    Parameters
    ----------
    text : str
        The text to be processed.

    Returns
    -------
    entities : list of tuples
        The list of extracted entities, where each tuple contains the text of the entity and its label.
    """
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

def extract_causal_relationships(sentence, relationship_list ,hazard_patterns):
    """
    Extract causal relationships from a sentence.

    The function takes a sentence as input and processes it with spaCy to extract causal relationships.
    The function returns a list of tuples, where each tuple contains the cause, the relationship, and the effect.

    Parameters
    ----------
    sentence : str
        The sentence to be processed.
    relationship_list : list of str
        The list of causal verbs to be considered.
    hazard_patterns : dict
        A dictionary of patterns to be used to check if a word is a hazard type.

    Returns
    -------
    causes : list of tuples
        The list of extracted causal relationships, where each tuple contains the cause, the relationship, and the effect.
    """
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

