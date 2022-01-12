import requests
import graph_api
import json, io, csv
from requests_ntlm2 import HttpNtlmAuth


def debug_print(x):
    """Attempt to print JSON without altering it, serializable objects as JSON, and anything else as default."""
    if CONFIG["debug"] and len(x) > 0:
        if isinstance(x, str):
            print(x)
        else:
            try:
                print(json.dumps(x, indent=4))
            except:
                print(x)


def get_cc_report(report_url):
    """Get data from Campus Cafe's Reporting Services and return list of dicts."""
    debug_print(f"Getting report from: {report_url}")
    auth = HttpNtlmAuth(
        CONFIG["CampusCafe"]["report_user"], CONFIG["CampusCafe"]["report_password"]
    )
    r = requests.get(url=report_url, auth=auth)
    r.raise_for_status()
    
    r.encoding='utf-8-sig'
    reader = csv.DictReader(io.StringIO(r.text))
    data = list(reader)

    return data


# Read config file
with open("settings.json") as config_file:
    CONFIG = json.load(config_file)
debug_print(CONFIG)

for k, v in CONFIG["sync_groups"].items():
    # Get list of members from Campus Cafe
    cc_membership = get_cc_report(v)
    debug_print(cc_membership)

    # Get list of members from Graph
    graph_membership = graph_api.get_group_members(k)
    debug_print(graph_membership)

    # Compare lists and make a list of users who are not in Azure group

    # Add missing users to Azure group
