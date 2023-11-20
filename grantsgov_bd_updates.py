
import pandas as pd
import requests, zipfile, io
from datetime import timedelta, datetime
import numpy as np

# class color:
#    PURPLE = '\033[95m'
#    CYAN = '\033[96m'
#    DARKCYAN = '\033[36m'
#    BLUE = '\033[94m'
#    GREEN = '\033[92m'
#    YELLOW = '\033[93m'
#    RED = '\033[91m'
#    BOLD = '\033[1m'
#    UNDERLINE = '\033[4m'
#    END = '\033[0m'



N_DAYS_AGO = 6
today = datetime.now()    
n_days_ago = today - timedelta(days=N_DAYS_AGO)

today = today.strftime("%Y%m%d")
prior = n_days_ago.strftime("%Y%m%d")


zip_old = requests.get('https://www.grants.gov/extract/GrantsDBExtract' + prior + 'v2.zip')
zip_new = requests.get('https://www.grants.gov/extract/GrantsDBExtract' + today + 'v2.zip')


o = zipfile.ZipFile(io.BytesIO(zip_old.content))
o.extractall()

n = zipfile.ZipFile(io.BytesIO(zip_new.content))
n.extractall()


df_old_orig = pd.read_xml("./GrantsDBExtract" + prior + "v2.xml")
df_new_orig = pd.read_xml("./GrantsDBExtract" + today + "v2.xml")


identifying_column = "OpportunityID"
name_column = "OpportunityTitle"
cfda_num_list = [98, 19, 10]
agency_list = ["USAID", "USDS", "USDA"]
message = ""

for agency, cfda_num in zip(agency_list, cfda_num_list):
    
    def see_if_nan (x):
        try:
            return int(x)
        except:
            return 0
        
    df_new = df_new_orig
    df_old = df_old_orig

    cfda_categories_old = [see_if_nan(x) for x in df_old['CFDANumbers'].values.tolist()]
    cfda_categories_new = [see_if_nan(x) for x in df_new['CFDANumbers'].values.tolist()]

    df_new['CFDACategory'] = cfda_categories_new
    df_old['CFDACategory'] = cfda_categories_old

    df_new = df_new[(df_new["CFDACategory"].isin([cfda_num]))]
    df_old = df_old[(df_old["CFDACategory"].isin([cfda_num]))]

    
    old_list = df_old[identifying_column].values.tolist()
    new_list = df_new[identifying_column].values.tolist()

    
    #in old but not in new -- removed
    removed = list(set(old_list) - set(new_list))
    print(removed)

    
    #in new but not in old -- added
    added = list(set(new_list) - set(old_list))
    print(added)

    
    removed_df = df_old[df_old[identifying_column].isin(removed)]
    df_old_final = df_old[~df_old[identifying_column].isin(removed)]

    
    added_df = df_new[df_new[identifying_column].isin(added)]
    df_new_final = df_new[~df_new[identifying_column].isin(added)]

    
    # df_new = df_new.reindex(columns=df_old.columns)

    
    df_new_final = df_new_final.sort_values(by=[identifying_column])
    df_old_final = df_old_final.sort_values(by=[identifying_column])

    
    df_new_final = df_new_final.reset_index(drop=True)
    df_old_final = df_old_final.reset_index(drop=True)

    
    df_new_final.compare(df_old_final)

    
    comparison_df = df_new_final.compare(df_old_final)

    
    if not added_df.empty and not removed_df.empty and not comparison_df.empty:
        agency_title = "<div id='" + agency + "'><hr class='solid'><br><h1 style='text-align: center;'>" + agency.center(100) + "</h1></div>"
    else:
        agency_list.remove(agency)

    if len(added) > 0:
        message += agency_title + "<br><br><b>The following opportunities have been added to Grants.Gov:</b><br>"
        index = 1
        for i, n in zip(added_df['OpportunityTitle'], added_df['OpportunityID']):
            message += "\t" + str(index) + ".) <a href='https://www.grants.gov/web/grants/view-opportunity.html?oppId=" + str(n) + "' target='_blank'>" + str(i) + "</a><br>"
            index += 1

    if len(removed) > 0:
        message += "<br><br><b>The following opportunities have been removed from Grants.Gov:</b><br>"
        index = 1
        for i, n in zip(removed_df['OpportunityTitle'], removed_df['OpportunityNumber']):
            message += "\t" + str(index) + ".) " + str(i) + " [ID: " + str(n) + "]<br>"
            index += 1

    
    def to_title(s):
        new_string=""
        for i in s:
            if(i.isupper()):
                new_string+="*"+i
            else:
                new_string+=i
        x=new_string.split("*")
        x.remove('')
        return " ".join(x)

    
    if not comparison_df.empty:
        c = comparison_df.columns.to_numpy()
        res = [c[x].tolist() for x in comparison_df.notna().to_numpy()]
        message += "<br><br><b>The following opportunities and their respective fields have been updated:</b><br><br>"
        index = 1
        for i, c in zip(comparison_df.index, res):

            for t in c:
                if t[1] == "other":
                    c.remove(t)
            cols = [x[0] for x in c]

            message += str(index) + ".) <a href='https://www.grants.gov/web/grants/view-opportunity.html?oppId=" + str(df_new_final.iloc[[i]]['OpportunityID'].values[0]) + "'>" + df_new_final.iloc[[i]][name_column].values[0] + "</a><br>"
            for item in cols:
                base_val = df_new_final.iloc[[i]][item].values[0]
                original_row = df_old_final.loc[df_old_final['OpportunityID'] == df_new_final.iloc[[i]]['OpportunityID'].values[0]]
                original_val = original_row[item].values[0]
                if "Date" in item:
                    if isinstance(base_val, (int, float, np.integer)):
                        if np.isnan(base_val):
                            message += "<p style='margin-left: 30px; margin-bottom: 0px;'><b>The " + to_title(item) + ":</b> was removed</p><br>"
                        else:
                            val = str(int(base_val))
                            date_str = datetime.strptime(val, '%m%d%Y').strftime("%m/%d/%Y")

                            try:
                                val_orig = str(int(original_val))
                                date_str_orig = datetime.strptime(val_orig, '%m%d%Y').strftime("%m/%d/%Y")
                            except:
                                date_str_orig = "Was empty and"

                            message += "<p style='margin-left: 30px; margin-bottom: 0px;'><b>The " + to_title(item) + ":</b> " + date_str_orig + " was changed to " + date_str + "</p><br>"
                    elif isinstance(base_val, str):
                        val = str(base_val)
                        message += "<p style='margin-left: 30px; margin-bottom: 0px;'><b>The " + to_title(item) + ":</b> " + str(val) + "</p><br>"
                    
                elif 'Version' in item:
                    continue
                else:
                    val = str(base_val)
                    message += "<p style='margin-left: 30px; margin-bottom: 0px;'><b>The " + to_title(item) + ":</b> " + str(val) + "</p><br>"

            message += "<br>"
            index += 1

head_str = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Grant.gov Data</title>
  <style>
    body {
      background-color: #dae19a;
      background-image: url('https://haverfordlibrary.org/wp-content/uploads/2017/03/Grants-Gov-Logo.png'); 
      background-repeat: no-repeat; 
      background-attachment: fixed; 
      background-position: center; 
      background-blend-mode: color-dodge;
    }
    /* Add a black background color to the top navigation */
    .topnav {
      background-color: #333;
      overflow: hidden;
      display: flex;
      justify-content: space-between;
    }

    /* Style the links inside the navigation bar */
    .topnav a {
      float: left;
      color: #f2f2f2;
      text-align: center;
      padding: 14px 16px;
      text-decoration: none;
      font-size: 17px;
    }

    /* Change the color of links on hover */
    .topnav a:hover {
      background-color: #ddd;
      color: black;
    }

    /* Add a color to the active/current link */
    .topnav a.active {
      background-color: #AEBC37;
      color: white;
    }
  </style>
</head>
"""

nav = "<div class='topnav' style='position: fixed; top: 0; width: 100%; margin-left: -0.7%;'><div><p style='font-family: Courier New, monospace; color: white;'> --- [pdsr custom reports: grants.gov weekly updates] --- </p></div><div>"

for agency in agency_list:
    nav += '<a href="#' + agency + '">' + agency + '</a>'
nav += '</div></div>'


with open("grants_gov_all_weekly_report_" + today + ".html", "w") as file:
    file.write(head_str +"<body style='background-color: #dae19a'>" + nav + message + "</body>")


