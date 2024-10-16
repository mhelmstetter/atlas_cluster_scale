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
    print("#### print")
    json_data = getClusterConfig()
    region0 = ['replicationSpecs', 0, 'regionConfigs', 0]
    autoScalingCompute = region0 + ["autoScaling", "compute"]
    electableSpecsSize = region0 + ["electableSpecs", "instanceSize"]
    readOnlySpecsSize = region0 + ["readOnlySpecs", "instanceSize"]

    minInstanceSize = get_value_by_path(json_data, autoScalingCompute + ["minInstanceSize"]) 

    print("autoScalingCompute: " + json.dumps(get_value_by_path(json_data, autoScalingCompute)))
    print(f"    minInstanceSize: {minInstanceSize}")
    print("electableSpecsSize: " + json.dumps(get_value_by_path(json_data, electableSpecsSize)))
    print("readOnlySpecsSize: " + json.dumps(get_value_by_path(json_data, readOnlySpecsSize)))

    configsStr = json.dumps(json_data, indent=4)
    print(configsStr)


def scaleDown():
    print(f"#### scaleDown to tier {args.clusterTier}")
    json_data = getClusterConfig()
    regions = get_value_by_path(json_data, ['replicationSpecs', 0, 'regionConfigs'])
    for index in range(len(regions)):
        region0 = ['replicationSpecs', 0, 'regionConfigs', index]
        autoScalingCompute = region0 + ["autoScaling", "compute"]
        electableSpecsTier = region0 + ["electableSpecs", "instanceSize"]
        readOnlySpecsTier = region0 + ["readOnlySpecs", "instanceSize"]

        minInstanceSize = get_value_by_path(json_data, autoScalingCompute + ["minInstanceSize"]) 

        electablePrevTier = get_previous_tier(get_value_by_path(json_data, electableSpecsTier))
        readOnlyPrevTier = get_previous_tier(get_value_by_path(json_data, readOnlySpecsTier))

        if minInstanceSize is None or is_less_than(args.clusterTier, minInstanceSize):
            replace_or_remove_by_path(json_data, autoScalingCompute + ["minInstanceSize"], args.clusterTier)
        
        replace_or_remove_by_path(json_data, autoScalingCompute + ["scaleDownEnabled"], True)
        replace_or_remove_by_path(json_data, electableSpecsTier, electablePrevTier)
        replace_or_remove_by_path(json_data, readOnlySpecsTier, readOnlyPrevTier)

    configsStr = json.dumps(json_data, indent=4)
    print(configsStr)

    if args.dryRun:
        print("dry run, exiting")
        return

    response = requests.patch(apiEndpoint,
                          auth=HTTPDigestAuth(args.username, args.apiKey),
                          verify=True,
                          data=configsStr,  # Add json.dumps here
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
    print(f"#### scaleUp to tier {args.clusterTier}")
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
        replace_or_remove_by_path(json_data, autoScalingCompute + ["enabled"], True)
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

def is_less_than(s1, s2):
    return tiers.index(s1) < tiers.index(s2)

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

parser = argparse.ArgumentParser(description="MongoDB custom Atlas scaling utility")

# Add global arguments that are common across all subcommands
parser.add_argument("--projectId", help="The Atlas project id", required=True)
parser.add_argument("--username", help="Atlas user name", required=True)
parser.add_argument("--apiKey", help="Atlas API key for the user", required=True)
parser.add_argument("--clusterName", help="Atlas Cluster name", required=True)
parser.add_argument("--printClusterConfig", dest='action', action='store_const', const=printClusterConfig, help="Print cluster configurations", required=False)
parser.add_argument("--scaleUp", dest='action', action='store_const', const=scaleUp, help="Scale up the cluster", required=False)
parser.add_argument("--scaleDown", dest='action', action='store_const', const=scaleDown, help="Scale down the cluster", required=False)
parser.add_argument("--clusterTier", help="Cluster tier to scale up/down to", required=False)

# Global optional argument
parser.add_argument("--dryRun", action="store_true", default=False, help="Dry run mode")

args = parser.parse_args()
if args.action is None:
    parser.parse_args(['-h'])

if args.action in [scaleUp, scaleDown] and args.clusterTier is None:
    parser.error("--clusterTier is required for scaleUp and scaleDown")


apiEndpoint = "https://cloud.mongodb.com/api/atlas/v2/groups/" + args.projectId +"/clusters/" + args.clusterName

args.action()


