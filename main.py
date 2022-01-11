import requests
import graph_auth
import graph_api
import json


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


# Read config file
with open("settings.json") as config_file:
    CONFIG = json.load(config_file)
debug_print(CONFIG)

for group in CONFIG['sync_groups']:
    # Get list of members from Campus Cafe

    # Compare lists and make a list of users who are not in Azure group

    # Add missing users to Azure group
    pass