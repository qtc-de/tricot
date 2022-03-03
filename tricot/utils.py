from __future__ import annotations

import os
import re
import tricot
import hashlib
from typing import Any
from pathlib import Path


class TricotRuntimeVariableError(Exception):
    '''
    A TricotRuntimeVariableError is raised, when a runtime variable was specified within
    the .yml test configuration, but was not defined at runtime.
    '''


class TricotEnvVariableError(Exception):
    '''
    A TricotEnvVariableError is raised, when an environment variable was specified within
    the .yml test configuration, but was not found at runtime.
    '''


class TricotInvalidVersionException(Exception):
    '''
    Is raised when an invalid version string was specified.
    '''


def resolve_runtime_variables(variables: dict[str, Any], key: str, value: Any) -> Any:
    '''
    This function is responsible for resolving runtime variables.
    When a variable contains the value '$runtime' it checks the
    '$runtime' key within the variables dict for the corresponding
    dictionary key. If it is found, the corresponding value is
    returned. If not, a TricotRuntimeVariableError is raised.

    When the value of a variables is not '$runtime', it is directly
    returned.

    Parameters:
        variables       Variables dictionary created during the Tester initialization
        key             Key of the current variable in question
        value           Value of the current variable in question

    Returns:
        value       Value with possible runtime variables applied
    '''
    if value != '$runtime':
        return value

    try:
        return (variables['$runtime'])[key]

    except KeyError:
        raise TricotRuntimeVariableError(f"Unable to find runtime variable '{key}'.")


def resolve_env_variables(variables: dict[str, Any], key: str, value: Any) -> Any:
    '''
    This function is responsible for resolving environment variables.
    When a variable contains the value '$env' it checks the
    '$env' key within the variables dict for the corresponding
    dictionary key. If it is found, the corresponding value is
    returned. If not, a TricotEnvVariableError is raised.

    When the value of a variables is not '$env', it is directly
    returned.

    Parameters:
        variables       Variables dictionary created during the Tester initialization
        key             Key of the current variable in question
        value           Value of the current variable in question

    Returns:
        value       Value with possible runtime variables applied
    '''
    if value != '$env':
        return value

    try:
        return (variables['$env'])[key]

    except KeyError:
        raise TricotEnvVariableError(f"Unable to find environment variable '{key}'.")


def apply_variables(candidate: Any, var_dict: dict[str, Any]) -> Any:
    '''
    Applies the variables contained in the Plugin on each str value within the
    parameters. For dictionaires and list, the function uses recursion to iterate
    over all possible items.

    Parameters:
        candidate       Current param value. Required for recursion.
        var_dict        Variables to apply.

    Returns:
        None
    '''
    if candidate is None or var_dict is None:
        return candidate

    cur_type = type(candidate)

    if cur_type is dict:
        for key, value in candidate.items():
            candidate[key] = apply_variables(value, var_dict)

    elif cur_type is list:
        for ctr in range(len(candidate)):
            candidate[ctr] = apply_variables(candidate[ctr], var_dict)

    elif cur_type is str:

        for var, var_value in var_dict.items():

            var_value = resolve_runtime_variables(var_dict, var, var_value)
            var_value = resolve_env_variables(var_dict, var, var_value)
            variable_key = '${'+str(var)+'}'

            if candidate == variable_key:
                candidate = var_value

                if type(candidate) is not str:
                    break

            else:
                candidate = candidate.replace(variable_key, str(var_value))

    return candidate


def make_ordinal(n: int) -> str:
    '''
    Convert an integer into its ordinal representation. Used for pretty printing and copied
    from: https://stackoverflow.com/questions/9647202/ordinal-numbers-replacement

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    '''
    n = int(n)
    suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    return str(n) + suffix


def check_keys(expected_keys: list[str], yaml_dict: dict) -> None:
    '''
    What happes quite some time is that validators are indented incorrectly and appear within the test
    section of the .yml definition. This is annoying, as your test seems to work, but was actually never
    validated. This function checks for unexpcted keys within .yml files and prints a warning if one is
    encountered.

    Parameters:
        expected_keys   List of keys that are expected to appear
        yaml_dict       Python dirctionary that represents the .yml file

    Returns:
        None
    '''
    for key in yaml_dict.keys():
        if key not in expected_keys:
            tricot.Logger.print_yellow('Warning:', end=' ')
            tricot.Logger.print_mixed_blue_plain('Test', yaml_dict['title'], 'contains unexpected key', end=': ')
            tricot.Logger.print_yellow_plain(key)


def merge_environment(new: dict, current: dict, path: Path) -> dict:
    '''
    Helper function to merge two environment dictionaries. Is mainly used to handle
    the case where the new environment is not a dictionary.

    Parameters:
        new             New environment variables to add
        current         Current set of environment variables
        path            Path of the currently parsed configuration file

    Returns:
        environment     Merged environment variables
    '''
    current = current or {}

    if new is None:
        return current

    if type(new) is not dict:
        raise tricot.TestKeyError(None, path, "Key 'env' needs to be a dictionary in the ")

    return {**new, **current}


def merge_default_environment(env: dict) -> dict:
    '''
    Merges the current user environment with the specifies environment dictionary.

    Parameters:
        new             dict to combine with the default environment

    Returns:
        environment     Merged environment variables
    '''
    return {**os.environ, **env}


def add_environment(variables: dict[str, Any]) -> None:
    '''
    Adds the current user environment to the available variables within the
    $env key.

    Parameters:
        variables       Variable dictionary

    Returns:
        None
    '''
    variables['$env'] = os.environ


def validate_color(string: str, allow_none: bool = False) -> None:
    '''
    Validates that the input string is a valid color name. If not, an exception is raised.

    Parameters:
        variables       Variable dictionary
        allow_none      Whether None values are allowed

    Returns:
        None
    '''
    if string is None and allow_none:
        return

    colors = ['grey', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
    if string not in colors:
        raise Exception(f'Invalid color was specified: {string}')


def validate_type(name: str, value: Any, expected_type: Any, path: Path = None) -> None:
    '''
    Validates that the input parameter 'value' has a type of 'expected_type'.
    If not, a corresponding exception is raised that contains the 'name' of the
    parameter and it's expected type

    Parameters:
        name            Name of the parameter
        value           Value of the parameter
        expected_type   Expected type of the parameter
        path            Optional path to a configuration file

    Returns:
        None
    '''
    if type(value) is not expected_type:
        raise tricot.TricotException(f"The '{name}' attribute requires type '{expected_type}'.", path)


def merge(dict1: dict, dict2: dict, name: str = None, path: Path = None) -> dict:
    '''
    Merge two dictionaries.

    Parameters:
        dict1       Dictionary one to merge
        dict2       Dictionary two to merge
        name        Optional string to print in exceptions
        path        Optional path to a configuration file

    Returns:
        dict        Merged dictionary
    '''
    if type(dict1) is not dict or type(dict2) is not dict:

        if name:
            raise tricot.TricotException(f"The '{name}' attribute requires type 'dict'.", path)

        else:
            raise tricot.TricotException('Invalid type specified during merge operation.', path)

    return {**dict1, **dict2}


def parse_groups(groups: list[str]) -> list[list[str]]:
    '''
    Parses group specifications. Groups should be specified as comma separated strings. Each
    comma separated part is interpreted as a group. All groups within a string are mandatory
    for a test / tester to match. Braces can be used for or-like statements.

    E.g.:

        java8,networking,filter      -> list(java8, networking, filter)
        java8,{networking,io},filter -> list(list(java8, networking, filter),
                                             list(java8, io, filter))

    Parameters:
        groups          List of group specifications

    Returns:
        list            List of group lists
    '''
    lists = list()
    regex = re.compile(r'\{([^}]+)\}')

    for group_spec in groups:

        or_like = regex.findall(group_spec)
        group_spec = regex.sub('$ORLIKE$', group_spec)

        split = list(filter(None, group_spec.split(',')))
        group_lists = [split]

        for match in or_like:

            new = []

            for group_list in group_lists:

                split = list(filter(None, match.split(',')))

                for item in split:

                    new_list = group_list.copy()

                    for ctr in range(len(new_list)):

                        if new_list[ctr] == '$ORLIKE$':
                            new_list[ctr] = item
                            break

                    new.append(new_list)

            group_lists = new

        lists += group_lists

    return lists


def groups_contain(groups_list: list[list[str]], groups: list[list[str]]) -> bool:
    '''
    Checks whether a specified list of groups contains a particular group of a
    list of specified groups. This separate function is required, as group
    comparison supports wildcards as * or **.

    Parameters:
        groups_list           List of group lists to search in
        groups                Group list to look for

    Returns:
        bool                  True if group is contained in groups
    '''
    for group in groups:

        for items in groups_list:

            ctr = 0
            match = True
            items = items.copy()

            try:

                while len(items) != 0:

                    item = items.pop(0)

                    if item == '*' or group[ctr] == item:

                        ctr += 1
                        continue

                    if item == '**':

                        item = items.pop(0)
                        while group[ctr] != item and ctr != len(group):
                            ctr += 1

                        if ctr == len(group):
                            match = False
                            break

                        ctr += 1
                        continue

                    match = False
                    break

                if match:
                    return True

            except IndexError:
                pass

    return False


def merge_groups(parent_groups: list[list[str]], new_groups: list[str]) -> list[list[str]]:
    '''
    This function is called by tests and testers to join groups that are defined within
    the test / tester definition with group lists that have been specified for upper testers.
    Each group in the test / tester specification is appened to the parent defined groups.

    Paramaters:
        parent_groups           Group lists inherited by the parent
        new_groups              Groups specified for the test / tester

    Returns:
        merged                  Merge result
    '''
    merged = list()

    for parent_group in (parent_groups or [[]]):

        if new_groups:

            for new_group in new_groups:
                copy = parent_group.copy()
                copy.append(new_group)
                merged.append(copy)

        else:
            merged.append(parent_group.copy())

    return merged


def verify_id_pattern(pattern: str, path: Path) -> str:
    '''
    Checks whether the specified ID pattern is valid. If invalid, a TricotException
    is raised.

    Parameters:
        pattern         ID pattern defined in a tester
        path            Path of the currently parsed configuration file

    Returns:
        str             If valid, the id pattern
    '''
    if pattern is not None:

        if type(pattern) is not str:
            raise tricot.TricotException("Tester attribute 'id_pattern' needs to be string.", path)

        regex = re.compile(r'\{(?::[0-9<>=^+bcdoxXneEfFgGn% -]+)?\}')
        matches = regex.findall(pattern)

        if len(matches) != 1:
            msg = "Tester attribute 'id_pattern' needs to contain exactly one '{}' sequence."
            raise tricot.TricotException(msg, path)

    return pattern


def match_version(version_dict: dict) -> bool:
    '''
    Checks if the currently running tricot installation matches the version specified
    in version_dict. version_dict is a dictionary that has to contain at least one of
    the following keys: eq, lt, gt.

    Paramaters:
        version_dict        Version dictionary containing at least one of eq, lt, gt

    Returns:
        bool                True if matching, False otherwise
    '''
    if version_dict is None:
        return True

    try:

        cur_ver = tricot.constants.VERSION

        for comperator in ['lt', 'le', 'eq', 'gt', 'ge']:

            version = version_dict.get(comperator)

            if version is None:
                continue

            result = compare_versions(cur_ver, version)

            if 'e' in comperator and result == 0:
                pass

            elif 'l' in comperator and result == -1:
                pass

            elif 'g' in comperator and result == 1:
                pass

            else:
                return False

    except TricotInvalidVersionException:
        return False

    return True


def split_version(version_string: str) -> list[int]:
    '''
    Splits a version string into it's three different components.

    Parameters:
        version_string          Incoming version string

    Returns:
        list[str]               List containing the different version components
    '''
    version_list = list()
    split = version_string.split('.')

    for item in split:

        if not item.isdigit():
            raise TricotInvalidVersionException(version_string)

        version_list.append(int(item))

    while len(version_list) < 3:
        version_list.append(0)

    return version_list


def compare_versions(one: str, other: str) -> int:
    '''
    Compares two version strings with each other. If equal,
    zero is reqturned. -1 if first is lower, +1 if other is lower.

    Parameters:
        one             Version string
        other           Version string

    Returns:
        int             0 -> equal, -1 -> one < other, +1 -> one > other
    '''
    split1 = split_version(one)
    split2 = split_version(other)

    for ctr in range(0, 3):

        if split1[ctr] < split2[ctr]:
            return -1

        elif split1[ctr] > split2[ctr]:
            return 1

    return 0


def file_integrity(file_dict: dict) -> bool:
    '''
    Checks whether the filename matches the specified checksums.
    The filename is expected under the 'filename' key of the specified
    dicitionary. Checksum keys can be md5, sha1, sha256, sha512

    Parameters:
        file_dict           Dictionary containing the filename and checksums

    Returns:
        bool                True if file exists and has the correct hash
    '''
    filename = file_dict.get('filename')

    if not filename or not Path(filename).exists():
        return False

    for hash_type in ['md5', 'sha1', 'sha256', 'sha512']:

        hash_value = file_dict.get(hash_type)

        if hash_value is not None:

            with open(filename, 'rb') as f:
                content = f.read()

            if hashlib.new(hash_type, content).hexdigest() != hash_value:
                return False

    return True
