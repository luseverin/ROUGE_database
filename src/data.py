##paths and variables
import getpass
DATA_PATH_LS = '../Data_backup/'
DATA_PATH_LH = "/scratchx/lhasbini/como_school/"

user = getpass.getuser()
if user == "lhasbini" : 
    DATA_PATH = DATA_PATH_LH
elif user == "lseverino" : ##### TO CHANGE FOR LUCA
    DATA_PATH = DATA_PATH_LS
else:
    raise ValueError(f"Unknown user: {user}")
    
DATA_IN_JSONS = DATA_PATH + 'report_jsons/'
DATA_OUT_LLMS = DATA_PATH + 'results_llm/'
DATA_LABELLED = DATA_PATH + 'labelled/'
DATA_FIGURE = DATA_PATH + 'figure/'