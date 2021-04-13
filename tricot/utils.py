import tricot
from typing import Any


class TricotRuntimeVariableError(Exception):
    '''
    A TricotRuntimeVariableError is raised, when a runtime variable was specified within
    the .yml test configuration, but was not defined at runtime.
    '''
    pass


def resolve_runtime_variables(variables: dict[str, Any], key: str, value: Any) -> Any:
    '''
    This function is responsible for resolving runtime variables.
    When a variable contains the value '$runtime' it checks the
    '$runtime' key within the variables dict for the corresponding
    dictionary key. If it is found, the corresponding value is
    returned. If not, a TricotRuntimeVariableError is raised.

    When the value of a variables is not '$runtime', it is simply
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


def apply_variables(candidate: Any, var_dict: dict[str, Any] = None) -> Any:
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
    if var_dict is None:
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
            variable_key = '${'+var+'}'

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
