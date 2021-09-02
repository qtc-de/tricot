from __future__ import annotations

import os
import tricot
from typing import Any
from pathlib import Path


class TricotRuntimeVariableError(Exception):
    '''
    A TricotRuntimeVariableError is raised, when a runtime variable was specified within
    the .yml test configuration, but was not defined at runtime.
    '''
    pass


class TricotEnvVariableError(Exception):
    '''
    A TricotEnvVariableError is raised, when an environment variable was specified within
    the .yml test configuration, but was not found at runtime.
    '''
    pass


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
