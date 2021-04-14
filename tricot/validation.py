from __future__ import annotations

import re
import sys
import shutil
import os.path
from typing import Any
from pathlib import Path

import tricot
import tricot.utils
from tricot.command import Command


this = sys.modules[__name__]
this.validators = {}


def register_validator(validator_name: str, validator_class: type) -> None:
    '''
    Registers a validator class under the specified name. This function needs to
    be called to make validators available within of .yml files. Some default
    validator classes are registerd at the end of this file. Others can be manually
    added by users that use tricot as a library.

    Parameters:
        validator_name      Name of the validator to use in .yml files
        validator_class     Reference to the corresponding validator class

    Returns:
        None
    '''
    this.validators[validator_name] = validator_class


def get_validator(path: Path, validator_name: str, param: Any, variables: dict[str:str]) -> Validator:
    '''
    Searches for the specified validator name within the registred validators and
    uses the corresponding class to create an instance for the validator. This instance
    is returned by the function. If the specified validator name is not found, the
    function raises a ValidatorError.

    Parameters:
        path                Path to the .yml file that contains the validator
        validator_name      Name of the requested validator
        param               Params to initialize the validator with
        variables           Variables to initialize the validator with
    '''
    val_class = this.validators.get(validator_name)

    if val_class is None:
        raise ValidatorError(path, f"Unable to find specified validator '{validator_name}'.")

    return val_class(path, validator_name, param, variables)


def get_validator_list() -> list[str]:
    '''
    Returns a list of currently registered validator names.

    Parameters:
        None

    Returns:
        validator_list      List of registred validators
    '''
    keys = this.validators.keys()
    return list(keys)


class ValidationException(Exception):
    '''
    ValidationExceptions are raised by Validators when their validation procedure
    failed. Custom validators should always raise this exception to indicate a
    failure.
    '''


class ValidatorError(Exception):
    '''
    ValidatorErrors are raised when a Validator was specified with incorrect
    parameters. The corresponding Exception just contains a message describing
    the problem.
    '''
    def __init__(self, path: Path, message: str) -> None:
        '''
        Just add one additional attribute that is the path to the config file where the validator is
        defined in.
        '''
        self.path = str(path.resolve())
        super().__init__(message)


class Validator:
    '''
    The Validator class is basically an abstract class with the only purpose of
    being extended by other classes. All possible validation options implemented in
    tricot are based on this superclass that contains some shared methods that are
    useful for all validators.

    Within test.yaml files, Validators can be defined in different ways:

        * example-validator: This is a value
        * example-validator2:
            param1: value1
            param2: value2
            ...
        * example-validator3:
            - value1
            - value2
            ...

    Which form to choose depends on the corresponding Validator requirements. When
    choosing the first version, the 'param' attribute of the Validator just contains
    the value specified in the yaml file. When choosing the second or third form, the
    'param' attribute contains a dictionary or list with the specified parameters.

    Validators can use the 'param_type' class variable to indicate which type of parameters
    they expect. For collection types like dict or list, it is also possible to specify
    the 'inner_types' attribute to specify requirements on the containing types.
    To understand this feature you probably want to look at the ContainsValidator in
    this file, which uses the 'inner_types' variable.

    Custom Validators should at least overwrite the 'run' method to perform their
    validation operation. Other methods can be overwritten or added on demand. The run
    method should just return if the validation was successful. A validation error
    should be indicated by raising a ValidationException. Errors that are caused by
    invalid configuration within the .yml file should cause a ValidatorError, but
    it is recommended to only raise this error during initialization and not within
    the 'run' method (check the RegexValidator for an example).
    '''
    param_type = None
    inner_types = None

    def __init__(self, path: Path, name: str, param: Any, variables: dict[str, Any]) -> None:
        '''
        Initializes the Validator.

        Parameters:
            path        Path to the .yml file that contains the validator
            name        Name of the Validator (as specified in the .yml file)
            param       Parameters of the Validator (can be str, dict, int, bool, ...)
            variables   Variables contained in this dict are replaced in all str parameters
        '''
        self.path = path
        self.name = name
        self.param = param
        self.variables = variables
        self.check_param_type()

        self.command = None

    def check_param_type(self) -> None:
        '''
        Checks whether the specified parameter type matches the expected one. If this is not
        the case, a ValidatorError is raised.

        Parameters:
            None

        Returns:
            None
        '''
        self.param = tricot.utils.apply_variables(self.param, self.variables)

        if self.param_type is None:
            return

        if type(self.param) is not self.param_type:
            message = f"Validator '{self.name}' requires a parameter type of {str(self.param_type)}"
            raise ValidatorError(self.path, message)

        self.check_inner_types()
        self.check_streams()

    def check_inner_types(self) -> None:
        '''
        Validators that require a dictionary or list can specify the static class variable 'inner_types'
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
                if value['required'] and not param and not self.check_alternative(key):

                    message = f"Validator '{self.name}' requires key with name '{key}' and type {value['type']}."
                    raise ValidatorError(self.path, message)

                if param is not None and type(param) is not value['type']:

                    message = f"Validator '{self.name}' expects type {value['type']} for the '{key}' key."
                    raise ValidatorError(self.path, message)

                self.check_expected()

        elif type(self.param) is list and type(self.inner_types) is list:

            for param in self.param:
                if type(param) not in self.inner_types:
                    message = f"Validator '{self.name}' requires a parameter type of list[{str(self.inner_types)}."
                    raise ValidatorError(self.path, message)

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
        For validators that accept dictionaries, it is possible that typos mess up the test configuration.
        E.g. when using the 'ignore_case' key within the ContainsValidator, a user might misspell it, and
        the check is performed case sensitive instead. This function validates (for Validators using the
        inner_types attribute), that there are no keys that are not contained within the inner_types dict.

        Parameters:
            None

        Returns:
            None
        '''
        if type(self.param) is dict and type(self.inner_types) is dict:

            expected_keys = self.inner_types.keys()

            for key in self.param.keys():

                if key != 'description' and key not in expected_keys:
                    tricot.logging.Logger.print_yellow('Warning:', end=' ')
                    tricot.logging.Logger.print_mixed_blue_plain('Validator', self.name, 'contains unexpected key', end=': ')
                    tricot.logging.Logger.print_yellow_plain(key, end=' ')
                    print(f'({self.path})')

    def from_list(path: Path, input_list: dict, variables: dict[str, Any] = {}) -> list[Validator]:
        '''
        Constructs a new list of Validators from a python list. The list content is usually
        the specified validator configuration within a .yml file. Notice that it is tempting
        to use only a dictionary for validators, as the list seems to be unecessary in most cases.
        However, when you want to use the same validator twice for one test, you need a list.

        Parameters:
            path        Path to the .yml file that contains the validator
            input_list  Python list as read in from a .yml file
            variables   Global variables that should be inherited by the validator

        Returns:
            Validator   Newly constructed Validator objects
        '''
        if type(input_list) is dict:
            raise ValidatorError(path, "Validators need to be specified as a list.")

        validators = list()

        for item in input_list:
            for key, value in item.items():
                val = get_validator(path, key, value, variables)
                validators.append(val)

        return validators

    def resolve_path(self, path: str) -> str:
        '''
        Resolves the specified path relative to the current validator definition (file location of
        the validators .yml file). If the input path is already absolute, it is just returned.

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
        errors at runtime. Stream names can be specified for each validator that accepts parameters
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
                raise ValidatorError(self.path, "When specified, stream needs to be one of 'stdout', 'stderr' or 'both'.")

    def get_output(self) -> str:
        '''
        Helper function to obtain the actual output of a command execution. Each validator accepts
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

        raise ValidatorError(self.path, f"Encountered unexpected value for the 'stream' key: {stream}")

    def _run(self, command: Command, hotplug_variables: dict[str, Any] = None) -> None:
        '''
        This method is called internally to perform the validation process. It is basically
        a wrapper to the user defined 'run' method that stores the command result in an
        additional class variable.

        Parameters:
            command             Command object associated with the current tests
            hotplug_variables   Variables to apply to the validator at runtime

        Returns:
            None
        '''
        self.command = command
        self.param = tricot.utils.apply_variables(self.param, hotplug_variables)
        self.run()

    def run(self) -> None:
        '''
        Dummy run method. This one needs to be overwritten by the actual validator implementations.

        Parameters:
            None

        Returns:
            None
        '''
        return None


class ContainsValidator(Validator):
    '''
    The ContainsValidator checks whether the command output contains the specified string values.
    The values are expected to be stored as list within the 'values' key. Additionally, the Validator
    accepts the 'ignore_case' key, to specify whether the case should be ignored and the 'invert' key
    to invert the match.

    Example:

        validators:
            - contains:
                ignore_case: True
                values:
                    - match this
                    - and this
                invert:
                    - not match this
                    - and this
    '''
    param_type = dict
    inner_types = {
            'ignore_case': {'required': False, 'type': bool},
            'values': {'required': True, 'type': list, 'alternatives': ['invert']},
            'invert': {'required': True, 'type': list, 'alternatives': ['values']}
    }

    def run(self) -> None:
        '''
        Check whether the command output contains the specified string value.
        '''
        cmd_output = self.get_output()

        invert = self.param.get('invert', [])
        values = self.param.get('values', [])
        ignore_case = self.param.get('ignore_case', False)

        if ignore_case:
            cmd_output = cmd_output.lower()

        for value in values:

            if ignore_case:
                value = value.lower()

            if value not in cmd_output:
                raise ValidationException(f"String '{value}' was not found in command output.")

        for value in invert:

            if ignore_case:
                value = value.lower()

            if value in cmd_output:
                raise ValidationException(f"String '{value}' was found in command output.")


class MatchValidator(Validator):
    '''
    The MatchValidator checks whether there is an exact match of the command output and the
    specified value. The value is expected within the 'value' key. Additionally, the validator
    accepts the 'ignore_case' key, to specify whether the case should be ignored.

    Example:

        validators:
            - match:
                ignore_case: True
                value: Match this!
    '''
    param_type = dict
    inner_types = {
            'ignore_case': {'required': False, 'type': bool},
            'value': {'required': True, 'type': str}
    }

    def run(self) -> None:
        '''
        Check whether command output matches the specified value.
        '''
        value = self.param['value'].rstrip('\n')
        cmd_output = self.get_output().rstrip('\n')

        if self.param.get('ignore_case') is True:
            if value.lower() != cmd_output.lower():
                raise ValidationException(f"String '{value}' does not match command output.")

        else:
            if value != cmd_output:
                raise ValidationException(f"String '{value}' does not match command output.")


class RegexValidator(Validator):
    '''
    The RegexValidator checks whether the command output matches the specified regex.

    Example:

        validators:
            - regex: .+(match this| or this).+
    '''
    param_type = str

    def __init__(self, *args, **kwargs) -> None:
        '''
        Regex initializer. This is used to throw ValidationErrors in case of invalid
        regex specifications already on creation time.
        '''
        super().__init__(*args, **kwargs)

        try:
            self.regex = re.compile(self.param)

        except Exception:
            raise ValidatorError(self.path, f"Specified regex '{self.param}' is invalid!")

    def run(self) -> None:
        '''
        Check whether command output contains the specified regex.
        '''
        cmd_output = self.get_output()

        if not self.regex.search(cmd_output):
            raise ValidationException(f"Regex '{self.param}' was not found in command output.")


class StatusCodeValidator(Validator):
    '''
    The StatusCodeValidator checks whether the exit code of the command matches the specified value.

    Example:

        validators:
            - status: 0
    '''
    param_type = int

    def run(self) -> None:
        '''
        Check whether the exit code of the command matches the specified value.
        '''
        status = self.command.status

        if self.param != status:
            raise ValidationException(f"Obtained status code '{status}' does not match the expected code '{self.param}'.")


class ErrorValidator(Validator):
    '''
    The ErrorValidator just checks the status code of the command for an error (status_code != 0). If the
    Validator was used with False as argument, it checks the other way around.

    Example:

        validators:
            - error: False
    '''
    param_type = bool

    def run(self) -> None:
        '''
        Check that status code of command is not equal 0.
        '''
        status = self.command.status

        if status == 0 and self.param is True:
            raise ValidationException("Obtained no error, despite error was expected.")

        if status != 0 and self.param is False:
            raise ValidationException("Obtained error, despite no error was expected.")


class FileExistsValidator(Validator):
    '''
    The FileExistsValidator takes a list of filenames and checks whether they exist on the file
    system. This can be useful, when your testing command is expected to create files.

    Example:

        validators:
            - file_exists:
                cleanup: True
                files:
                    - /tmp/test1
                    - /tmp/test2
                    ...
    '''
    param_type = dict
    inner_types = {
            'cleanup': {'required': False, 'type': bool},
            'files': {'required': True, 'type': list, 'alternatives': ['invert']},
            'invert': {'required': True, 'type': list, 'alternatives': ['files']}
    }

    def run(self) -> None:
        '''
        Check the existence of files and optionally clean them up.
        '''
        not_found = list()

        files = self.param.get('files', [])
        invert = self.param.get('invert', [])

        for file_name in files:

            file_name = self.resolve_path(file_name)
            if os.path.isfile(file_name):

                if self.param.get('cleanup') is True:
                    os.remove(file_name)

                continue

            not_found.append(file_name)

        if not_found:
            file_names = ', '.join(not_found)
            raise ValidationException(f"File '{file_names}' does not exist.")

        for file_name in invert:
            file_name = self.resolve_path(file_name)
            if os.path.isfile(file_name):
                raise ValidationException(f"File '{file_name}' does exist.")


class DirectoryExistsValidator(Validator):
    '''
    The DirectoryExistsValidator takes a list of directory names and checks whether they exist
    on the file system. This can be useful, when your testing command is expected to create
    directories.

    Example:

        validators:
            - dir_exists:
                cleanup: True
                force: False
                dirs:
                    - /tmp/test1
                    - /tmp/test2
                    ...
    '''
    param_type = dict
    inner_types = {
            'cleanup': {'required': False, 'type': bool},
            'force': {'required': False, 'type': bool},
            'dirs': {'required': True, 'type': list, 'alternatives': ['invert']},
            'invert': {'required': True, 'type': list, 'alternatives': ['dirs']}
    }

    def run(self) -> None:
        '''
        Check the existence of directories and optionally clean them up.
        '''
        not_found = list()

        dirs = self.param.get('dirs', [])
        invert = self.param.get('invert', [])

        for dir_name in dirs:

            dir_name = self.resolve_path(dir_name)
            if os.path.isdir(dir_name):

                if self.param.get('cleanup', False):

                    try:
                        os.rmdir(dir_name)

                    except OSError as e:

                        if 'Directory not empty' in str(e) and self.param.get('force', False):
                            shutil.rmtree(dir_name)

                continue

            not_found.append(dir_name)

        if not_found:
            dir_names = ', '.join(not_found)
            raise ValidationException(f"Directory '{dir_names}' does not exist.")

        for dir_name in invert:
            dir_name = self.resolve_path(dir_name)
            if os.path.isdir(dir_name):
                raise ValidationException(f"Directory '{dir_name}' does exist.")


class FileContainsValidator(Validator):
    '''
    The FileContainsValidator takes a list of filenames and strings that represent their
    expected content. It when validates whether the files contain the corresponding content.

    Example:

        validators:
            - file_contains:
                - file: /etc/passwd
                  contains:
                    - root
                    - bin
                - file: /etc/hosts
                  contains:
                    - localhost
                    - 127.0.0.1
    '''
    param_type = list
    inner_types = [dict]

    def run(self) -> None:
        '''
        Check the specified files for their expected content.
        '''
        for check in self.param:

            invert = check.get('invert', [])
            contains = check.get('contains', [])

            file_name = self.resolve_path(check['file'])
            if not os.path.isfile(file_name):
                raise ValidationException(f"Specified file '{file_name}' does not exist.")

            with open(file_name) as f:
                content = f.read()

                for item in contains:
                    if item not in content:
                        raise ValidationException(f"String '{item}' was not found in '{file_name}'.")

                for item in invert:
                    if item in content:
                        raise ValidationException(f"String '{item}' was found in '{file_name}'.")


class RuntimeValidator(Validator):
    '''
    The RuntimeValidator checks whether the overall runtime of the command was lower or greater
    than the user specified value. It also supports equal, but this should be useles :D

    Example:

        validators:
            - runtime:
                lt: 10
                gt: 5
    '''
    param_type = dict
    inner_types = {
            'lt': {'required': True, 'type': int, 'alternatives': ['gt', 'eq']},
            'gt': {'required': True, 'type': int, 'alternatives': ['lt', 'eq']},
            'eq': {'required': True, 'type': int, 'alternatives': ['lt', 'gt']},
    }

    def run(self) -> None:
        '''
        Check that the runtime fulfills the user specified condition.
        '''
        for operation in self.param.keys():

            if operation == 'lt':
                if self.command.runtime >= self.param['lt']:
                    expected = f"(expected: runtime < {self.param['lt']})"
                    raise ValidationException(f"Command execution took {self.command.runtime} {expected}")

            if operation == 'gt':
                if self.command.runtime <= self.param['gt']:
                    expected = f"(expected: runtime > {self.param['gt']})"
                    raise ValidationException(f"Command execution took {self.command.runtime} {expected}")

            if operation == 'eq':
                if self.command.runtime == self.param['eq']:
                    expected = f"(expected: runtime == {self.param['eq']})"
                    raise ValidationException(f"Command execution took {self.command.runtime} {expected}")


register_validator("contains", ContainsValidator)
register_validator("match", MatchValidator)
register_validator("regex", RegexValidator)
register_validator("status", StatusCodeValidator)
register_validator("error", ErrorValidator)
register_validator("file_exists", FileExistsValidator)
register_validator("dir_exists", DirectoryExistsValidator)
register_validator("file_contains", FileContainsValidator)
register_validator("runtime", RuntimeValidator)
