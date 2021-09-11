from __future__ import annotations

import re
import sys
import os.path
from typing import Any
from pathlib import Path

import tricot
import tricot.utils
from tricot.command import Command


this = sys.modules[__name__]
this.extractors = {}


def register_extractor(extractor_name: str, extractor_class: type) -> None:
    '''
    Registers an extractor class under the specified name. This function needs to
    be called to make extractors available within of .yml files. Some default
    extractor classes are registerd at the end of this file. Others can be manually
    added.

    Parameters:
        extractor_name      Name of the extractor to use in .yml files
        extractor_class     Reference to the corresponding extractor class

    Returns:
        None
    '''
    this.extractors[extractor_name] = extractor_class


def get_extractor(path: Path, extractor_name: str, param: Any, variables: dict[str:str]) -> Extractor:
    '''
    Searches for the specified extractor name within the registred extractors and
    uses the corresponding class to create an instance for the extractor. This instance
    is returned by the function. If the specified extractor name is not found, the
    function raises an ExtractorError.

    Parameters:
        path                Path to the .yml file that contains the extractor
        extractor_name      Name of the requested extractor
        param               Params to initialize the extractor with
        variables           Variables to initialize the extractor with
    '''
    ext_class = this.extractors.get(extractor_name)

    if ext_class is None:
        raise ExtractorError(path, f"Unable to find specified extractor '{extractor_name}'.")

    return ext_class(path, extractor_name, param, variables)


def get_extractor_list() -> list[str]:
    '''
    Returns a list of currently registered extractor names.

    Parameters:
        None

    Returns:
        extractor_list      List of registred extractors
    '''
    keys = this.extractors.keys()
    return list(keys)


class ExtractException(Exception):
    '''
    Extractors can throw this exception on failing to extract a value. Extractors can be configured
    to silently continue in this case or to throw an error (the corresponding test where the extractor
    was defined in just fails then).
    '''
    def __init__(self, message: str, ext: Extractor) -> None:
        '''
        Just add two additional attributes that are the path to the config file where the extractor is
        defined in and the extractor that caused the exception.
        '''
        self.extractor = ext
        super().__init__(message)


class ExtractorError(Exception):
    '''
    ExtractorErrors are raised when an Extractor was specified with incorrect
    parameters. The corresponding Exception just contains a message describing
    the problem.
    '''
    def __init__(self, path: Path, message: str) -> None:
        '''
        Just add one additional attribute that is the path to the config file where the extractor is
        defined in.
        '''
        self.path = str(path.resolve())
        super().__init__(message)


class Extractor:
    '''
    Extractors can be used within tests to extract parts of the commands output into variables.
    An example could look like this:

        - title: Example Test
          description: |-
              Just an example test

          command:
            - cat
            - /etc/passwd

          extractors:
              - regex:
                  pattern: ':(.+)$'
                  variable: shells
                  default: 'failed'

              - regex:
                  pattern: '^([^:]+):'
                  variable: users
                  default:
                    users: 'failed'
                    users-0: 'failed'
                    users-1: 'failed'

    The assignment of matched values to variables can be handeled differently for each extractor.
    Read the corresponding extractors documentation to get more information onto that.
    '''
    param_type = None
    inner_types = None

    def __init__(self, path: Path, name: str, param: Any, variables: dict[str, Any]) -> None:
        '''
        Initializes the Extractor.

        Parameters:
            path        Path to the .yml file that contains the extractor
            name        Name of the extractor (as specified in the .yml file)
            param       Parameters of the extractor (can be str, dict, int, bool, ...)
            variables   Variables contained in this dict are replaced in all str parameters
        '''
        self.path = path
        self.name = name
        self.param = param
        self.variables = variables

        self.command = None
        self.failure_string = None
        self.failure_color = None

        self.on_miss = self.param.get('on_miss', 'continue')
        self.check_param_type()

    def check_param_type(self) -> None:
        '''
        Checks whether the specified parameter type matches the expected one. If this is not
        the case, an ExtactorError is raised.

        Parameters:
            None

        Returns:
            None
        '''
        self.param = tricot.utils.apply_variables(self.param, self.variables)

        if self.param_type is None:
            return

        if type(self.param) is not self.param_type:
            message = f"Extractor '{self.name}' requires a parameter type of {str(self.param_type)}"
            raise ExtractorError(self.path, message)

        self.check_inner_types()
        self.check_streams()

    def check_inner_types(self) -> None:
        '''
        Extractors that require a dictionary or list types can specify the static class variable 'inner_types'
        to specify which inner types are expected within the collection types. When a list is used,
        'inner_types' is expected to contain a list with allowed types. In case of a dict, 'inner_types'
        is expected to contain a dict, containing the possible parameters as keys and a dict of
        {'required': bool, 'type': type} as value.

        The check is currently only implemented on the first layer (non recursive).

        Parameters:
            None

        Returns:
            None
        '''
        if type(self.param) is dict and type(self.inner_types) is dict:

            for key, value in self.inner_types.items():

                param = self.param.get(key)
                if value['required'] and param is None and not self.check_alternative(key):

                    message = f"Extractor '{self.name}' requires key with name '{key}' and type {value['type']}."
                    raise ExtractorError(self.path, message)

                if param is not None and type(param) is not value['type']:

                    message = f"Extractor '{self.name}' expects type {value['type']} for the '{key}' key."
                    raise ExtractorError(self.path, message)

        elif type(self.param) is list and type(self.inner_types) is list:

            for param in self.param:
                if type(param) not in self.inner_types:
                    message = f"Extractor '{self.name}' requires a parameter type of list[{str(self.inner_types)}."
                    raise ExtractorError(self.path, message)

        self.check_expected()

    def check_alternative(self, key: str) -> bool:
        '''
        Checks whether the specified key has alternative values defined. If so, the function
        checks whether one of these is contained within the parameter dictionary.

        Parameters:
            key         Key to look for

        Returns:
            bool        True if one of the alternatives of key is contained
        '''
        alternatives = self.inner_types[key].get('alternatives', [])

        for item in alternatives:
            if item in self.param:
                return True

        return False

    def check_expected(self) -> None:
        '''
        For Extractors that accept dictionaries, it is possible that typos mess up the test configuration.
        This function validates (for extractors using the inner_types attribute), that there are no keys
        that are not contained within the inner_types dict.

        Parameters:
            None

        Returns:
            None
        '''
        if type(self.param) is dict and type(self.inner_types) is dict:

            expected_keys = set(self.inner_types.keys())
            expected_keys.add('stream')
            expected_keys.add('output')
            expected_keys.add('on_miss')

            for key in self.param.keys():

                if key != 'description' and key not in expected_keys:
                    tricot.logging.Logger.print_yellow('Warning:', end=' ')
                    tricot.logging.Logger.print_mixed_blue_plain('Extractor', self.name, 'contains unexpected key', end=': ')
                    tricot.logging.Logger.print_yellow_plain(key, end=' ')
                    print(f'({self.path})')

    def from_list(path: Path, input_list: dict, variables: dict[str, Any] = {}) -> list[Extractor]:
        '''
        Constructs a new list of Extractors from a python list. The list content is usually
        the specified extractor configuration within a .yml file. Notice that it is tempting
        to use only a dictionary for extractors, as the list seems to be unecessary in most cases.
        However, when you want to use the same extractor twice for one test, you need a list.

        Parameters:
            path        Path to the .yml file that contains the extractor definition
            input_list  Python list as read in from a .yml file
            variables   Global variables that should be inherited by the extractor

        Returns:
            Extractors   Newly constructed Extractor objects
        '''
        if type(input_list) is dict:
            raise ExtractorError(path, "Extractors need to be specified as a list.")

        extractors = list()

        for item in input_list:
            for key, value in item.items():
                val = get_extractor(path, key, value, variables)
                extractors.append(val)

        return extractors

    def resolve_path(self, path: str) -> str:
        '''
        Resolves the specified path relative to the current extractor definition (file location of
        the extractors .yml file). If the input path is already absolute, it is just returned.

        Parameters:
            path        File system path to resolve

        Returns:
            resolved    Resolved file system path
        '''
        if os.path.isabs(path):
            return path

        return str(self.path.parent.joinpath(path).resolve())

    def check_streams(self) -> None:
        '''
        Used to validate stream names if specified. Is run during parsing of tests to prevent
        errors at runtime. Stream names can be specified for each extractor that accepts parameters
        as dictionary values.

        Parameters:
            None

        Returns:
            None
        '''
        if type(self.param) != dict:
            return

        stream = self.param.get('stream')

        if stream is not None:

            if type(stream) != str or stream not in ['stdout', 'stderr', 'both']:
                raise ExtractorError(self.path, "When specified, stream needs to be one of 'stdout', 'stderr' or 'both'.")

    def get_output(self) -> str:
        '''
        Helper function to obtain the actual output of a command execution. Each extractor accepts
        the special key 'stream' within of it's parameters. 'stream' is expected to be either 'both',
        'stdout' or 'stderr'. If it was not specified 'both' is taken as the default. The return value
        of this function is the command output that was captured for the correspoding stream.

        Parameters:
            None

        Returns:
            output      Output captured from stdout, stderr or both
        '''
        if type(self.param) != dict:
            return self.command.get_output()

        stream = self.param.get('stream')

        if stream == 'stdout':
            return self.command.stdout

        elif stream == 'stderr':
            return self.command.stderr

        elif stream == 'both' or stream is None:
            return self.command.get_output()

        raise ExtractorError(self.path, f"Encountered unexpected value for the 'stream' key: {stream}")

    def _extract(self, command: Command, hotplug_variables: dict[str, Any] = None) -> None:
        '''
        This method is called internally to perform the extraction process. It is basically
        a wrapper to the user defined 'extract' method that stores the command result in an
        additional class variable. All exceptions thrown by the actual extractor are encapsulated
        within an ExtractException.

        Parameters:
            command             Command object associated with the current tests
            hotplug_variables   Variables to apply to the extractor at runtime

        Returns:
            None
        '''
        self.command = command
        self.param = tricot.utils.apply_variables(self.param, hotplug_variables)

        try:
            self.extract(hotplug_variables)

        except ExtractException as e:
            raise e

        except Exception as e:
            raise ExtractException(str(e), self)

    def extract(self, hotplug: dict) -> None:
        '''
        Dummy extract method. This one needs to be overwritten by the actual extractor implementations.

        Parameters:
            hotplug             Hotplug variables. Required by the extractor to add new variables.

        Returns:
            None
        '''
        return None


class RegexExtractor(Extractor):
    '''
    The RegexExtractor extracts command output based on a regular expression. The following yaml
    shows an example:

        - title: Example Test
          description: |-
              Just an example test

          command:
            - cat
            - /etc/passwd

          extractors:
              - regex:
                  pattern: ':(.+)$'
                  variable: shells

              - regex:
                  pattern: '^([^:]+):'
                  variable: users
                  default:
                    users: 'failed'
                    users-0: 'failed'
                    users-1: 'failed'

    The extraction results of this extractor can be accessed like variables. It support
    multiple matches and also match groups. The literal variable name gets always assigned the
    first matching item. Additionally, you can access matching items by using 'variablename-#',
    where '#' is the desired match number. When using match groups, you can access matches from
    different groups by using 'variablename-#-#', where the first '#' is the number of the match
    group and the second '#' is the number of the match.
    '''
    param_type = dict
    inner_types = {
            'ascii': {'required': False, 'type': bool},
            'default': {'required': False, 'type': dict},
            'dotall': {'required': False, 'type': bool},
            'ignore_case': {'required': False, 'type': bool},
            'multiline': {'required': False, 'type': bool},
            'pattern': {'required': True, 'type': str},
            'variable': {'required': True, 'type': str},
    }

    def __init__(self, *args, **kwargs) -> None:
        '''
        Regex initializer. This is used to throw ExtractorErrors in case of invalid
        regex specifications already on creation time.
        '''
        super().__init__(*args, **kwargs)

        flags = 0

        if self.param.get('ascii'):
            flags = flags | re.ASCII
        if self.param.get('dotall'):
            flags = flags | re.DOTALL
        if self.param.get('ignore_case'):
            flags = flags | re.IGNORECASE
        if self.param.get('multiline'):
            flags = flags | re.MULTILINE

        try:
            self.pattern = self.param.get('pattern', '')
            self.regex = re.compile(self.pattern, flags)
            self.variable = self.param.get('variable')
            self.defaults = self.param.get('default', {})

        except Exception:
            raise ExtractorError(self.path, f"Specified regex '{self.pattern}' is invalid!")

    def extract(self, hotplug: dict) -> None:
        '''
        Extract parts of the command output into variables.
        '''
        cmd_output = self.get_output()

        matches = self.regex.finditer(cmd_output)

        for key, value in self.defaults.items():
            hotplug[key] = value

        ctr = 0
        for match in matches:

            if ctr == 0:
                hotplug[self.variable] = match.group(0)

            key = f'{self.variable}-{ctr}'
            hotplug[key] = match.group(0)

            key = f'{self.variable}-{ctr}-0'
            hotplug[key] = match.group(0)

            cts = 1

            for group in match.groups():

                key = f'{self.variable}-{ctr}-{cts}'
                hotplug[key] = match.group(cts)
                cts += 1

            ctr += 1

        if ctr == 0:
            raise ExtractException(f"RegexExtractor did not find pattern '{self.pattern}' within the output.", self)


register_extractor("regex", RegexExtractor)
