import json
import requests
import graph_auth

# Read config file
with open("settings.json") as config_file:
    config = json.load(config_file)
graph_endpoint = config["Microsoft"]["graph_endpoint"]

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
    if config["debug"] and len(x) > 0:
        if isinstance(x, str):
            print(x)
        else:
            try:
                print(json.dumps(x, indent=4))
            except:
                print(x)


def get_group_members(group_id):
    """Return a list of users in a group."""

    parameters = {"$select": "id,displayName,mail,userType,userPrincipalName"}
    r = sess_graph.get(
        graph_endpoint + f"/groups/{group_id}/members",
        params=parameters,
    )
    r.raise_for_status()
    response = json.loads(r.text)
    members = response["value"]

    # Get additional pages from server
    while "@odata.nextLink" in response:
        r = sess_graph.get(response["@odata.nextLink"])
        r.raise_for_status()
        response = json.loads(r.text)
        members.extend(response["value"])

    return members


def add_group_member(group_id, user_id):
    """Adds a user to a group. Returns HTTP status code; 204 indicates success."""

    body = {"@odata.id": f"{graph_endpoint}/education/{user_id}"}

    if config["dry_run"]:
        return None
    else:
        try:
            r = sess_graph_j.post(
                graph_endpoint + f"/groups/{group_id}/members/$ref",
                data=json.dumps(body),
            )
            debug_print(r.text)
            r.raise_for_status()
        except requests.HTTPError:
            # Why does this 404 sometimes? User licensing issue?
            if r.status_code == 404:
                debug_print(r.text)
            else:
                raise
        return r.status_code


def remove_group_member(group_id, user_id):
    """Removes the specified user from the specified group. Returns HTTP status code; 204 indicates success."""

    if config["dry_run"]:
        return None
    else:
        r = sess_graph.delete(
            f"{graph_endpoint}/groups/{group_id}/members/{user_id}/$ref"
        )
        debug_print(r.text)
        r.raise_for_status()
        return r.status_code
