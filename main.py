import requests
import json, io, csv
from requests_ntlm2 import HttpNtlmAuth
import graph_api
from config import CONFIG


def verbose_print(x):
    """Attempt to print JSON without altering it, serializable objects as JSON, and anything else as default."""
    if CONFIG["verbose"] and len(x) > 0:
        if isinstance(x, str):
            print(x)
        else:
            try:
                print(json.dumps(x, indent=4))
            except:
                print(x)


def get_cc_report(report_url):
    """Get data from Campus Cafe's Reporting Services and return list of dicts."""
    auth = HttpNtlmAuth(
        CONFIG["CampusCafe"]["report_user"], CONFIG["CampusCafe"]["report_password"]
    )
    r = requests.get(url=report_url, auth=auth)
    r.raise_for_status()

    r.encoding = "utf-8-sig"
    reader = csv.DictReader(io.StringIO(r.text))
    data = list(reader)

    return data


# Main body of the program
pending_changes = False

for k, v in CONFIG["sync_groups"].items():
    # Get list of members from Campus Cafe
    verbose_print(f"Getting report from: {v['source']}")
    cc_membership = get_cc_report(v["source"])
    cc_membership = {m["USERNAME"].lower(): m for m in cc_membership}
    verbose_print("Campus Cafe membership:" + str(len(cc_membership)))
    verbose_print(cc_membership)

    # Get list of members from Graph
    graph_membership = graph_api.get_group_members(v["id"])
    graph_membership = {m["userPrincipalName"].lower(): m for m in graph_membership}
    verbose_print(graph_membership)

    # Compare lists
    missing = [x for x in cc_membership if x not in graph_membership]
    verbose_print("Missing users: " + str(len(missing)))
    verbose_print(
        [
            f"{cc_membership[x]['ID_NUMBER']}: {cc_membership[x]['FIRST_NAME']} {cc_membership[x]['LAST_NAME']}"
            for x in missing
        ]
    )
    extra = [x for x in graph_membership if x not in cc_membership]
    verbose_print("Extra users: " + str(len(extra)))
    verbose_print(
        [
            f"{graph_membership[x]['userPrincipalName']}: {graph_membership[x]['displayName']}"
            for x in extra
        ]
    )

    # Add missing users to Azure group
    for m in missing:
        verbose_print(f"Looking up user {m}, {cc_membership[m]['ID_NUMBER']}")
        user = graph_api.get_user(m, cc_membership[m]["USERNAME"])
        if user:
            pending_changes = True
            verbose_print(f"Adding user {user} to group {k}")
            graph_api.add_group_member(k, user)
        else:
            verbose_print(f"User not found: {m}")

    # Remove extra users from Azure group
    for user in extra:
        pending_changes = True
        verbose_print(f"Removing user {user} from group {k}")
        graph_api.remove_group_member(k, user)


graph_api.deinit(pending_changes)
