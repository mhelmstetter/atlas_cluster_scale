import requests
from requests.auth import HTTPDigestAuth
import json
import argparse
import sys
import copy

header1 = {"Accept": "application/vnd.atlas.2023-11-15+json", "Content-Type": "application/json" }

keys_to_delete = ['connectionStrings', 'tags', 'backupEnabled', 'biConnector', 'createDate', 'diskSizeGB', 'diskWarmingMode', 'labels']

tiers = ["M10", "M20", "M30", "M40", "M50", "M60", "M80", "M140", "M200", "M300", "M400", "M700"]


def getClusterConfig():
    response = requests.get(apiEndpoint
            ,auth=HTTPDigestAuth(args.username,args.apiKey), verify=False, headers=header1)
    response.raise_for_status()
    json_data = response.json()
    
    for key in keys_to_delete:
        if key in json_data:
            del json_data[key]
    return json_data

def printClusterConfig():

    json_data = getClusterConfig()
    region0 = ['replicationSpecs', 0, 'regionConfigs', 0]
    autoScalingCompute = region0 + ["autoScaling", "compute"]
    electableSpecsSize = region0 + ["electableSpecs", "instanceSize"]
    readOnlySpecsSize = region0 + ["readOnlySpecs", "instanceSize"]

    print("autoScalingCompute: " + json.dumps(get_value_by_path(json_data, autoScalingCompute)))
    print("electableSpecsSize: " + json.dumps(get_value_by_path(json_data, electableSpecsSize)))
    print("readOnlySpecsSize: " + json.dumps(get_value_by_path(json_data, readOnlySpecsSize)))

    configsStr = json.dumps(json_data, indent=4)
    print(configsStr)


def scaleDown():
    json_data = getClusterConfig()
    regions = get_value_by_path(json_data, ['replicationSpecs', 0, 'regionConfigs'])
    for index in range(len(regions)):
        #print("***************")
        #print(json.dumps(region, indent=4))
        region0 = ['replicationSpecs', 0, 'regionConfigs', index]
        autoScalingCompute = region0 + ["autoScaling", "compute"]
        electableSpecsTier = region0 + ["electableSpecs", "instanceSize"]
        readOnlySpecsTier = region0 + ["readOnlySpecs", "instanceSize"]

        #autoScalingMinPrevTier = get_previous_tier(args.autoScalingMinTier)
        #print("*** autoScalingMinPrevTier: " + str(autoScalingMinPrevTier))

        electablePrevTier = get_previous_tier(get_value_by_path(json_data, electableSpecsTier))
        readOnlyPrevTier = get_previous_tier(get_value_by_path(json_data, readOnlySpecsTier))

        replace_or_remove_by_path(json_data, autoScalingCompute + ["minInstanceSize"], args.clusterTier)
        #replace_or_remove_by_path(json_data, autoScalingCompute + ["maxInstanceSize"], "M40")
        replace_or_remove_by_path(json_data, autoScalingCompute + ["scaleDownEnabled"], True)
        replace_or_remove_by_path(json_data, electableSpecsTier, electablePrevTier)
        replace_or_remove_by_path(json_data, readOnlySpecsTier, readOnlyPrevTier)

    configsStr = json.dumps(json_data, indent=4)
    print(configsStr)

    if args.dryRun:
        print("dry run, exiting")
        return

    response = requests.patch(apiEndpoint,
                    auth=HTTPDigestAuth(args.username,args.apiKey),
                    verify=False,
                    data=json_data,
                    headers=header1)
    if response.status_code != 200:
        print(f"Error Status Code: {response.status_code}")
        print(f"Response Reason: {response.reason}")
        print(f"Response Content: {response.text}")  # Detailed error message
        print(f"Response Headers: {response.headers}")
        print(f"Response Cookies: {response.cookies}")
        print(f"Request URL: {response.url}")
        print(f"Request Headers: {response.request.headers}")
        print(f"Request Body: {response.request.body}")
        print(f"Time Elapsed: {response.elapsed}")
    response.raise_for_status()
    print("Scale down complete: " + json.dumps(response.json()))

def scaleUp():
    json_data = getClusterConfig()
    regions = get_value_by_path(json_data, ['replicationSpecs', 0, 'regionConfigs'])
    for index in range(len(regions)):
        region0 = ['replicationSpecs', 0, 'regionConfigs', index]
        autoScalingCompute = region0 + ["autoScaling", "compute"]
        electableSpecsSize = region0 + ["electableSpecs", "instanceSize"]
        readOnlySpecsSize = region0 + ["readOnlySpecs", "instanceSize"]

        # Possible failures of note:
        #   - Compute auto-scaling min instance size must be unset when scale down is disabled
        #   - BASE_INSTANCE_SIZE_MUST_MATCH, Electable and read-only nodes must all have the same instance size.
        replace_or_remove_by_path(json_data, autoScalingCompute + ["minInstanceSize"], remove=True)
        #replace_or_remove_by_path(json_data, autoScalingCompute + ["maxInstanceSize"], "M40")
        replace_or_remove_by_path(json_data, autoScalingCompute + ["scaleDownEnabled"], False)
        replace_or_remove_by_path(json_data, electableSpecsSize, args.clusterTier)
        replace_or_remove_by_path(json_data, readOnlySpecsSize, args.clusterTier)

    configsStr = json.dumps(json_data, indent=4)
    print(configsStr)

    if args.dryRun:
        print("dry run, exiting")
        return

    response = requests.patch(apiEndpoint,
                    auth=HTTPDigestAuth(args.username,args.apiKey),
                    verify=False,
                    data=json.dumps(json_data),
                    headers=header1)
    if response.status_code != 200:
        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")

    response.raise_for_status()
    print("Scale up complete: " + json.dumps(response.json()))

def get_previous_tier(value):
    if value in tiers:
        index = tiers.index(value)
        if index > 0:
            return tiers[index - 1]
        else:
            return tiers[0]
    print("tier not found: " + str(value))
    return None  # Value not found in the list

def get_next_tier(value):
    if value in tiers:
        index = tiers.index(value)
        if index < len(tiers) - 1:
            return tiers[index + 1]
        else:
            return None  # No next value if it's the last one in the list
    return None  # Value not found in the list

def get_value_by_path(data, path, default=None):
    """Recursively access a nested dictionary using a list of keys/indices, with error handling."""
    try:
        for key in path:
            data = data[key]
        return data
    except (KeyError, IndexError, TypeError):
        return default
 
def replace_or_remove_by_path(json_data, path, new_value=None, remove=False):
    """
    Replace the value of a nested key by specifying its path, or remove the key.
    The 'remove' flag must be explicitly set to True to remove a key.
    
    Args:
        json_data (dict or list): The JSON object (Python dict or list).
        path (list): The path to the key as a list of keys and/or indices.
        new_value: The new value to assign to the key or index. This can be any type.
        remove (bool): If True, the key at the specified path will be removed.

    Raises:
        KeyError: If the specified key is not found for removal.
        IndexError: If the specified index is out of range for a list.
        TypeError: If the structure doesn't match (e.g., trying to access a list as a dictionary).
    """
    current = json_data

    # Traverse the path except for the final key or index
    for key in path[:-1]:
        if isinstance(current, dict):
            if key not in current:
                if remove:
                    return  # If removing, stop early if key doesn't exist
                current[key] = {}  # Create a new dictionary if it doesn't exist
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int):
            # Ensure the list is large enough; otherwise, extend it
            while len(current) <= key:
                if remove:
                    return  # If removing, stop early if index doesn't exist
                current.append({})  # Append a new dictionary if index doesn't exist
            current = current[key]
        else:
            raise TypeError(f"Expected dict or list at '{key}', but got {type(current)}.")

    # Handle the final key or index
    final_key = path[-1]
    if isinstance(current, dict):
        if remove:
            current.pop(final_key, None)  # Remove key if it exists
        else:
            current[final_key] = new_value  # Set the new value, creating the key if necessary
    elif isinstance(current, list) and isinstance(final_key, int):
        if remove:
            if 0 <= final_key < len(current):
                current.pop(final_key)  # Remove the item at the specified index
        else:
            while len(current) <= final_key:
                current.append(None)  # Append None or another default value if index doesn't exist
            current[final_key] = new_value
    else:
        raise TypeError(f"Expected dict or list at the final step, but got {type(current)}.")



#
# main
#

requests.packages.urllib3.disable_warnings()

parser = argparse.ArgumentParser(description="Manage alerts from MongoDB Ops/Cloud Manager")

# Add global arguments that are common across all subcommands
parser.add_argument("--projectId", help="The Atlas project id", required=True)
parser.add_argument("--username", help="Atlas user name", required=True)
parser.add_argument("--apiKey", help="Atlas API key for the user", required=True)
parser.add_argument("--clusterName", help="Atlas Cluster name", required=True)

# Create subparsers for different actions
subparsers = parser.add_subparsers(dest="command", help="Available actions")

# Subparser for the 'printClusterConfig' action
print_config_parser = subparsers.add_parser('printClusterConfig', help="Print cluster configurations")
print_config_parser.set_defaults(func=printClusterConfig)

# Subparser for the 'scaleDown' action
scale_down_parser = subparsers.add_parser('scaleDown', help="Scale down cluster configuration")
scale_down_parser.add_argument("--clusterTier", help="Auto-scale minimum cluster size", required=True)
scale_down_parser.set_defaults(func=scaleDown)

# Subparser for the 'scaleUp' action
scale_up_parser = subparsers.add_parser('scaleUp', help="Scale up cluster configuration")
scale_up_parser.add_argument("--clusterTier", help="Auto-scale maximum cluster size", required=True)
scale_up_parser.set_defaults(func=scaleUp)

# Global optional argument
parser.add_argument("--dryRun", action="store_true", default=False, help="Dry run mode")

args = parser.parse_args()

apiEndpoint = "https://cloud.mongodb.com/api/atlas/v2/groups/" + args.projectId +"/clusters/" + args.clusterName

# Call the appropriate function based on the subcommand
if args.command is None:
    parser.print_help()
else:
    args.func()


