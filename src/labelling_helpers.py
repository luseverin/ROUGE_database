
import pandas as pd
import requests

def sort_appeal_type(x):
    pref_order = ["DREF Operation Final Report", "DREF Operation Update", "DREF Operation", "Operations Update"]
    for appealtype in pref_order:
        if appealtype in list(x['appealType']):
            return x[x['appealType'] == appealtype]

def select_report_by_appealCode(appeal_code, report_df):
    report = report_df.where(report_df.appealCode == appeal_code).dropna()
    return report

def print_report(appeal_code, report, text_field="nathaz_text"):
    print(f"{appeal_code}: {report.date}")
    text = report[text_field]
    print("\n".join(text))

def add_report_date(report, impact_dict_or_list):
    if isinstance(impact_dict_or_list, dict):
        impact_dict_or_list["reportDate"] = report.date
    elif isinstance(impact_dict_or_list, list):
        for i in range(len(impact_dict_or_list)):
            impact_dict_or_list[i]["reportDate"] = report.date
    else:
        raise TypeError("impact_dict_or_list must be a dictionary or a list of dictionaries")
    return impact_dict_or_list

def download_report(report, savelocation):
    link = report["reportLink"]
    savename = report["origType"]+".pdf"
    r = requests.get(link)
    with open(savelocation / savename, 'wb') as f:
        f.write(r.content)

def report_dict_to_df(labelled_reports_dict):
    df_list = []
    for k,v in labelled_reports_dict.items():
        df = pd.DataFrame(v)
        df['appealCode'] = k
        df_list.append(df)
    df_all = pd.concat(df_list)
    df_all.reset_index(inplace=True, drop=True)
    return df_all