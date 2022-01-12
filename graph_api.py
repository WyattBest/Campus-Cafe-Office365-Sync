import json
import requests
import graph_auth
import subprocess

# Read config file
with open("settings.json") as config_file:
    CONFIG = json.load(config_file)
graph_endpoint = CONFIG["Microsoft"]["graph_endpoint"]

# Create persistent HTTP session without Content-Type header
sess_graph = requests.Session()
sess_graph.headers.update({"Authorization": graph_auth.get_auth_header()})

# Create persistent HTTP session with Content-Type: application/json header
sess_graph_j = requests.Session()
sess_graph_j.headers.update(
    {"Authorization": graph_auth.get_auth_header(), "Content-Type": "application/json"}
)


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


def get_user_by_employeeId(employeeId):
    """Returns a user by employeeId."""

    parameters = {
        "$select": "id,displayName,mail,userType,userPrincipalName,employeeId"
    }
    r = sess_graph.get(
        graph_endpoint + f"/users?$filter=employeeId eq '{employeeId}'",
        params=parameters,
    )
    r.raise_for_status()
    response = json.loads(r.text)
    if len(response["value"]) > 0:
        return response["value"][0]
    else:
        return None


def get_group_members(group_id):
    """Return a list of users in a group."""

    parameters = {
        "$select": "id,displayName,mail,userType,userPrincipalName,employeeId"
    }
    r = sess_graph.get(
        graph_endpoint + f"/groups/{group_id}/members",
        params=parameters,
    )
    r.raise_for_status()
    r = json.loads(r.text)
    members = r["value"]

    # Get additional pages from server
    while "@odata.nextLink" in r:
        r = sess_graph.get(r["@odata.nextLink"])
        r.raise_for_status()
        r = json.loads(r.text)
        members.extend(r["value"])

    return members


# def add_group_member(group_id, user_id):
#     """Adds a user to a group. Returns HTTP status code; 204 indicates success."""

#     body = {"@odata.id": f"{graph_endpoint}/directoryObjects/{user_id}"}

#     if config["dry_run"]:
#         return None
#     else:
#         try:
#             r = sess_graph_j.post(
#                 graph_endpoint + f"/groups/{group_id}/members/$ref",
#                 data=json.dumps(body),
#             )
#             debug_print(r.text)
#             r.raise_for_status()
#         except requests.HTTPError:
#             # Why does this 404 sometimes? User licensing issue?
#             if r.status_code == 404:
#                 debug_print(r.text)
#             else:
#                 raise
#         return r.status_code


# def remove_group_member(group_id, user_id):
#     """Removes the specified user from the specified group. Returns HTTP status code; 204 indicates success."""

#     if config["dry_run"]:
#         return None
#     else:
#         r = sess_graph.delete(
#             f"{graph_endpoint}/groups/{group_id}/members/{user_id}/$ref"
#         )
#         debug_print(r.text)
#         r.raise_for_status()
#         return r.status_code


def add_group_member(group_id, user_id):
    """Adds a user to a group via a PowerShell shim. Temporary hack until Graph API supports modifying distribution groups."""

    # See https://docs.microsoft.com/en-us/powershell/exchange/app-only-auth-powershell-v2?view=exchange-ps#step-2-assign-api-permissions-to-the-application
    # https://adamtheautomator.com/exchange-online-v2/#Assigning_an_Azure_AD_Role_to_the_Application
    if CONFIG["dry_run"]:
        return None
    else:
        subprocess.run(
            [
                "powershell.exe",
                "$cert_pw = ConvertTo-SecureString '{}' -AsPlainText -Force; \
                Connect-ExchangeOnline -AppId '{}' -CertificateFilePath '{}' -CertificatePassword $cert_pw -Organization '{}'; \
                Add-DistributionGroupMember -Identity '{}' -Member '{}'".format(
                    CONFIG["Microsoft"]["certificate_password"],
                    CONFIG["Microsoft"]["application_id"],
                    CONFIG["Microsoft"]["certificate"],
                    CONFIG["Microsoft"]["organization"],
                    group_id,
                    user_id,
                ),
            ]
        )
