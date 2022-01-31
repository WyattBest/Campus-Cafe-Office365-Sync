import json
import requests
import graph_auth
# import subprocess
from os import getcwd
from config import CONFIG

graph_endpoint = CONFIG["Microsoft"]["graph_endpoint"]

# Create persistent HTTP session without Content-Type header
sess_graph = requests.Session()
sess_graph.headers.update({"Authorization": graph_auth.get_auth_header()})

# Create persistent HTTP session with Content-Type: application/json header
sess_graph_j = requests.Session()
sess_graph_j.headers.update(
    {"Authorization": graph_auth.get_auth_header(), "Content-Type": "application/json"}
)


# Create a PowerShell script to be executed at the end of the program.
# Temporary hack until Graph API supports modifying distribution groups.
# See https://docs.microsoft.com/en-us/powershell/exchange/app-only-auth-powershell-v2?view=exchange-ps#step-2-assign-api-permissions-to-the-application
# and https://adamtheautomator.com/exchange-online-v2/#Assigning_an_Azure_AD_Role_to_the_Application
script_ps = open("output_tasks.ps1", "w")
script_ps.write("Start-Transcript 'PowerShell_Transcript.log';\n")
script_ps.write(
    "$cert_pw = ConvertTo-SecureString '{}' -AsPlainText -Force;\n".format(
        CONFIG["Microsoft"]["certificate_password"]
    )
)
script_ps.write(
    "Connect-ExchangeOnline -AppId '{}' -CertificateFilePath '{}' -CertificatePassword $cert_pw -Organization '{}';\n".format(
        CONFIG["Microsoft"]["application_id"],
        getcwd() + "\\" + CONFIG["Microsoft"]["certificate"],
        CONFIG["Microsoft"]["organization"],
    )
)


def deinit(pending_changes):
    """Save and execute the PowerShell shim script."""
    script_ps.write("Exit;")
    script_ps.close()
    if not pending_changes:
        print("No changes to apply.")
        # Wipe out the script to Task Manager doens't waste time running it
        open("output_tasks.ps1", "w").close()
    elif CONFIG["dry_run"]:
        print(
            "Dry run: No changes were made. See output_tasks.ps1 for proposed distribution group changes."
        )
    # else:
        # For some reason this doesn't work if Python is run via Task Scheduler.
        # Workaround: Add second step to Task Scheduler to run PowerShell script.
        # subprocess.run(
        #     [
        #         "powershell.exe",
        #         "-ExecutionPolicy Unrestricted",
        #         "-File output_tasks.ps1",
        #     ]
        # )


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


def get_user(employee_id, upn):
    """Look up a user by employeeId or UPN."""

    parameters = {"$select": "id,mail,userPrincipalName,employeeId"}

    # Todo: Make a proper try/catch block for handling 404s
    if upn:
        r = sess_graph.get(f"{graph_endpoint}/users/{upn}", params=parameters)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        r = json.loads(r.text)
        return r
    elif employee_id:
        r = sess_graph.get(
            f"{graph_endpoint}/users?$filter=employeeId eq '{employee_id}'",
            params=parameters,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        response = json.loads(r.text)
        return r
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


def add_dist_group_member(group_id, upn):
    """Adds a user to a group via a PowerShell shim."""

    script_ps.write(
        "Add-DistributionGroupMember -Identity '{}' -Member '{}';\n".format(
            group_id, upn
        )
    )


def remove_dist_group_member(group_id, upn):
    """Removes a user from a group via a PowerShell shim."""

    script_ps.write(
        "Remove-DistributionGroupMember -Identity '{}' -Member '{}' -Confirm:$false;\n".format(
            group_id, upn
        )
    )


def add_group_member(group_id, user_id):
    """Adds a user to a group. Returns HTTP status code; 204 indicates success."""

    body = {"@odata.id": f"{graph_endpoint}/directoryObjects/{user_id}"}

    if CONFIG["dry_run"]:
        return None
    else:
        try:
            r = sess_graph_j.post(
                graph_endpoint + f"/groups/{group_id}/members/$ref",
                data=json.dumps(body),
            )
            # debug_print(r.text)
            r.raise_for_status()
        except requests.HTTPError:
            # Why does this 404 sometimes? User licensing issue?
            if r.status_code == 404:
                print(r.text)
            else:
                raise
        return r.status_code


def remove_group_member(group_id, user_id):
    """Removes the specified user from the specified group. Returns HTTP status code; 204 indicates success."""

    if CONFIG["dry_run"]:
        return None
    else:
        r = sess_graph.delete(
            f"{graph_endpoint}/groups/{group_id}/members/{user_id}/$ref"
        )
        # debug_print(r.text)
        r.raise_for_status()
        return r.status_code
