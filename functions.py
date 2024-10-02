import re
import numpy as np
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
        rep['disasterTypeReclassified'] = np.unique(new_disasters)

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

def clean_text(text, remove_numbers=False, remove_stopwords=False):
    # Remove hyperlinks
    text = re.sub(r'http\S+|www\S+', '', text)

    # Remove some special characters, leaving basic punctuation (e.g., commas, periods)
    text = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', text)

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
        prev_token = doc[token.i - 1]
        next_token = doc[token.i + 1]
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
        hazards = []
        if (re.search(r"the situation|the disaster|background|description of the crisis|what happened, where and when|description of the disaster", sentence, re.IGNORECASE)) and (id_top==None):
            #Save where the text should begin 
            id_top = id_s 
        if (re.search(r"coordination and partnerships|red cross red crescent action|operational developments|the response so far|summary of response|scope and scale", sentence, re.IGNORECASE)) and (id_end==None) and (id_top!=None):   
            # Fix a minimum of 5 sentences for the description of the hazard
            if ((id_s-id_top) >= 5) : 
                id_end = id_s
    return text[id_top:id_end]
