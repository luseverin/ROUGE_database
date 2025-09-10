##paths and variables
import getpass
from pathlib import Path
DATA_PATH_LS = Path('../Data_backup/')
# DATA_PATH_LH = "/scratchx/lhasbini/como_school/"
DATA_PATH_LH = Path("c:/Users/lhasbini/ownCloud/Documents/Thèse/Conférences_Discussions/2024_Como_Compound Events Training/data/")

user = getpass.getuser()
if user == "lhasbini" :
    DATA_PATH = DATA_PATH_LH
elif user == "lseverino" : ##### TO CHANGE FOR LUCA
    DATA_PATH = DATA_PATH_LS
else:
    raise ValueError(f"Unknown user: {user}")

DATA_IN_JSONS = DATA_PATH / 'report_jsons/'
DATA_OUT_LLMS = DATA_PATH / 'results_llm/'
DATA_LABELLED = DATA_PATH / 'labelled/'
DATA_FIGURE = DATA_PATH / 'figure/'
DATA_OUT_PROC = DATA_PATH / 'results_proc/'
DATA_EXTERNAL_SOURCE = DATA_PATH / 'external_impact/'
ADMIN_PATH = DATA_PATH / "admin_files/"