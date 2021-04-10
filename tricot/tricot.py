#!/usr/bin/python3

from __future__ import annotations

import yaml
import subprocess
from pathlib import Path
from typing import Any, Union

import tricot.utils
from tricot.docker import TricotContainer
from tricot.logging import Logger
from tricot.validation import Validator, ValidationException
from tricot.plugin import Plugin


class TricotRuntimeError(Exception):
    '''
    Custom exception class for exceptions raised when running the external command.
    '''
    def __init__(self, exception: Exception) -> None:
        '''
        Custom exception class that stores the original exception within a variable.
        '''
        self.original = exception
        super().__init__('Runtime Error')


class TricotException(Exception):
    '''
    Custom exception class for general purpose and tricot related exceptions.
    '''


class TesterKeyError(Exception):
    '''
    TesterKeyErrors are raised when the .yml test definition file misses
    required keys for constructing a Tester object.
    '''

    def __init__(self, key: str, path: Path, optional: str = None, section: str = None) -> None:
        '''
        As these Exception is only used internally, we give it a static content
        that only takes the missing key as argument.
        '''
        if optional is not None:
            self.message = f"Test configuration requires either the '{key}' or the '{optional}' key"
            self.message += "within the 'global' section."

        elif section is not None:
            self.message = f"Test configuration misses required key {key} in the '{section}' section."

        else:
            self.message = f"Test configuration misses required key {key} in the 'global' section."

        self.path = str(path.resolve())
        super().__init__(self.message)


class TestKeyError(Exception):
    '''
    TestKeyErrors are raised when the .yml test definition file misses
    required keys for constructing a Test object.
    '''

    def __init__(self, key: str, path: Path, message: str = None) -> None:
        '''
        As these Exception is only used internally, we give it a static content
        that only takes the missing key as argument. Optionally, we allow to add
        a custom message if required.
        '''
        if message:
            self.message = message

        else:
            self.message = f"Test configuration misses required key {key} within the "

        self.path = str(path.resolve())
        self.number = None

        super().__init__(self.message)

    def add_number(self, ctr: int) -> None:
        '''
        The default content of the exception indicates a missing key within a test configuration.
        This function can be used to add the position of the corresponding test within the .yml
        file.
        '''
        self.number = ctr

    def __str__(self) -> str:
        '''
        Depending whether the execption contains the test number (self.number), the exception
        is formatted a little bit differently.
        '''
        message = self.message

        if self.number:
            ordinal = tricot.utils.make_ordinal(self.number)
            message += f'{ordinal} test in the '

        return message + 'tests section.'


class Test:
    '''
    The Test class represents a single command test specified within a .yml file.
    Test objects contain all required information like the command definition, the
    specified variables and the required validators. During a test, Test objects are
    evaluated by executing their 'run' method.
    '''
    expected_keys = ['title', 'description', 'command', 'arguments', 'validators', 'timeout']

    def __init__(self, path: Path, title: str, error_mode: str, variables: dict[str, Any], command: list,
                 timeout: int, validators: list[Validator]) -> None:
        '''
        Initializer for a Test object.

        Parameters:
            path            Path object to the file that contains the tests configuration
            title           The title of the test - is displayed during execution.
            error_mode      Decides what to do if a validator fails (break|continue)
            variables       Dictionary of variables that are replaced in the command
            command         The command that is run by this test
            timeout         Timeout in seconds to wait for the specified command
            validators      List of validators to apply on the command output

        Returns:
            None
        '''
        self.path = path
        self.title = title
        self.error_mode = error_mode
        self.variables = variables
        self.command = command
        self.timeout = timeout
        self.validators = validators

    def apply_variables(val: Union(str, list), variables: dict[str, Any], k: str = 'command') -> list:
        '''
        Applies variables to a command or argument list/string. This method needs to be
        static, as it is applied right at the object creation. This is the only way to
        allow command lists to be specified within variables while simoultaneously checking
        types on object creation.

        Parameters:
            val             Value to replace variables in. Usually the command or arguments portion of .yml files
            variables       Variables to apply
            k               Current key value (command|arguments)

        Returns:
            None
        '''
        if val is None:
            return []

        for key, value in variables.items():

            key = '${'+key+'}'
            value = tricot.utils.resolve_runtime_variables(variables, key, value)

            if type(val) is str:
                if val == key and type(value) is list:
                    val = value.copy()

                else:
                    val = val.replace(key, str(value))

            elif type(val) is list:
                for ctr in range(len(val)):
                    if type(val[ctr]) is str:
                        val[ctr] = val[ctr].replace(key, str(value))

                    else:
                        val[ctr] = str(val[ctr])

        if type(val) is not list:
            raise ValueError(f"The '{k}' key needs to be a list within the ")

        return val

    def from_dict(path: Path, input_dict: dict, variables: dict[str, Any] = {}, error_mode: str = 'continue') -> Test:
        '''
        Creates a Test object from a dictionary. The dictionary is expected to be the content
        read in of a .yml file and needs all keys that are required for a test (validators,
        title and command).

        Parameters:
            path            Path object to the tests configuration file
            input_dict      Dictionary that defines all required information for a test
            variables       Variables that should be inherited from the global scope
            error_mode      Decides whether to break or continue on failure

        Returns:
            Test            Newly generated Test object
        '''
        try:
            j = input_dict
            var = {**variables, **j.get('variables', {})}
            validators = Validator.from_list(path, j['validators'], var)

            e_mode = j.get('error_mode') or error_mode

            command = Test.apply_variables(j['command'], var)
            arguments = Test.apply_variables(j.get('arguments'), var, 'arguments')

            if type(command) is not list:
                raise TestKeyError(None, path, "The 'command' key needs to be a list within the ")

            if arguments:

                if type(arguments) is not list:
                    raise TestKeyError(None, path, "The 'arguments' key needs to be a list within the ")

                command += arguments

            Test.check_keys(input_dict)
            return Test(path, j['title'], e_mode, var, command, j.get('timeout'), validators)

        except KeyError as e:
            raise TestKeyError(str(e), path)

        except ValueError as e:
            raise TestKeyError(None, path, str(e))

    def from_list(path: Path, input_list: list, variables: dict[str, Any] = {}, error_mode: str = 'continue') -> list[Test]:
        '''
        Within .yml files, Tests are specified in form of a list. This function takes such a list,
        that contains each single test definition as another dictionary (like it is created when
        reading the .yml file) and returns a corresponding list of Test objects.

        Parameters:
            path            Path object to the tests configuration file
            input_list      List of test definitions as read in from a .yml file
            variables       Variables that should be inherited from the global scope
            error_mode      Decides whether to break or continue on failure

        Returns
            list[Test]      List of Test objects created from the .yml input
        '''
        tests = list()

        if type(input_list) is not list:
            raise TestKeyError(None, path, 'Test defintions need to be specified as list within the ')

        for ctr in range(len(input_list)):

            try:
                test = Test.from_dict(path, input_list[ctr], variables, error_mode)
                tests.append(test)

            except TestKeyError as e:
                e.add_number(ctr + 1)
                raise e

        return tests

    def run(self, prefix: str = '-', hotplug_variables: dict[str, Any] = None) -> None:
        '''
        Runs the Test and applies all specified validators to the command output.
        Depending on the current error_mode, the function may raise exceptions and
        let the caller handle them. Furthermore, it generates output regarding the
        success or error of a Test.

        Parameters:
            prefix              Optional prefix to include for each test title
            hotplug_variables   Variables that are applied at runtime.

        Returns:
            None
        '''
        Logger.increase_indent()
        Logger.print_blue(f'{prefix} {self.title}...', end=' ', flush=True)
        success = True

        output = self.run_wrapper(hotplug_variables)

        for validator in self.validators:

            try:
                validator._run(output, hotplug_variables)

            except Exception as e:

                if success:
                    Logger.print_plain_red("failed.")

                Logger.handle_error(e, validator, self.command)

                if self.error_mode == "break":
                    Logger.decrease_indent()
                    raise ValidationException('')

                else:
                    success = False

        if success:
            Logger.print_plain_green("success.")

        hotplug_variables['$prev'] = output
        hotplug_variables['$prev-cmd'] = self.command
        Logger.decrease_indent()

    def run_wrapper(self, hotplug_variables: dict[str, Any] = None) -> str:
        '''
        Just a wrapper around the actual command execution function. It is basically used
        to reduce the complexity of the run function and to handle the special case of
        the ${prev} variable within the command specification.

        Parameters:
            hotplug_variables   Variables that are applied at runtime.

        Returns:
            cmd_output      Command output in the form [status_code, stdout & stderr]
        '''
        if self.command[0] != '${prev}':
            self.command = Test.apply_variables(self.command, hotplug_variables)

            try:
                output = self._run()

            except Exception as e:
                Logger.print_plain_red("error.")
                raise TricotRuntimeError(e)

            except KeyboardInterrupt as e:
                Logger.print_plain_red("canceled.")
                raise KeyboardInterrupt(e)

        else:
            prev = hotplug_variables.get('$prev')
            prev_cmd = hotplug_variables.get('$prev-cmd')

            if prev is not None and prev_cmd is not None:
                output = prev
                self.command = prev_cmd

            else:
                Logger.print_plain_red("error.")
                raise TricotException("Special '${prev}' variable was used, but no previous output exists.")

        return output

    def _run(self) -> list[int, str]:
        '''
        This is a helper method that performs the actual command execution. It returns
        the output of a command in form of a list that contains the status code at first
        and the command output as second element.

        Parameters:
            None

        Returns:
            cmd_output      Command output in the form [status_code, stdout & stderr]
        '''
        try:
            process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.path.parent)
            output, _ = process.communicate(timeout=self.timeout)
            return_code = process.returncode

        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=self.timeout)
            return_code = 99

        except subprocess.CalledProcessError as e:
            output = e.output
            return_code = e.returncode

        return [return_code, output.decode('utf-8')]

    def check_keys(yaml_dict: dict) -> None:
        '''
        What happes quite some time is that validators are indented incorrectly and appear within the test
        section of the .yml definition. This is annoying, as your test seems to work, but was actually never
        validated. This function checks for unexpcted keys within .yml files and prints a warning if one is
        encountered.
        '''
        for key in yaml_dict.keys():
            if key not in Test.expected_keys:
                Logger.print_yellow('Warning:', end=' ')
                Logger.print_mixed_blue_plain('Test', yaml_dict['title'], 'contains unexpected key', end=': ')
                Logger.print_yellow_plain(key)


class Tester:
    '''
    The Tester class represents a single .yml file that contains Test definitions. It is basically
    an Object that contains the tester configuration and a reference to each Test object that should
    be executed during a run. A command test with tricot is intended to be started by a Tester object,
    by calling its 'run' method.
    '''
    tester_count = 0

    def __init__(self, path: Path, name: str, title: str, variables: dict[str, Any], tests: list[Test], testers: list[Tester],
                 containers: list[TricotContainer], plugins: list[Plugin], error_mode: str) -> None:
        '''
        Initializes a new Tester object.

        Parameters:
            path        Path object to the Testers configuration file
            name        Name of the tester (used for identification)
            title       Title of the test (used for displaying)
            variables   Dictionary of global variables that should be applied to all Tests and Validators
            tests       List of Test objects that should run during a test
            testers     List of Tester object, that allows to nest tester objects
            containers  List of TricotContainer objects for the test
            plugins     List of Plugin objects for the test
            error_mode  Decides what to do if a plugin fails (break|continue)
        '''
        self.name = name
        self.title = title or name
        self.variables = variables
        self.tests = tests
        self.testers = testers
        self.containers = containers
        self.plugins = plugins
        self.error_mode = error_mode

    def from_dict(input_dict: dict, initial_vars: dict[str, Any] = dict(), runtime_vars: dict[str, Any] = None,
                  path: Path = None, e_mode: str = None) -> Tester:
        '''
        Creates a new Tester object from a python dictionary. The dictionary is expected to be
        created by reading a .yml file that contains test defintions. It requires all keys that
        need to be present for creating the Tester and the Test objects. This method walks down
        basically the complete .yml tree and constructs all required objects on its way.

        Parameters:
            input_dict      Python dictionary as read in from a .yml file
            initial_vars    Additional variables. This is used internally when nesting Testers
            runtime_vars    Runtime variables (only specifiable when using tricot as library)
            path            Path object to the testers configuration file
            e_mode          Error mode that was mayve inherited by the parent tester

        Returns:
            Tester          Tester object created from the dictionary
        '''
        try:
            g = input_dict
            t = input_dict['tester']

            error_mode = t.get('error_mode') or e_mode
            testers = g.get('testers')
            definitions = g.get('tests')

            variables = g.get('variables', dict())
            variables = {**variables, **initial_vars}
            variables['cwd'] = path.parent

            plugins = Plugin.from_list(path, g.get('plugins'), variables)
            containers = TricotContainer.from_list(g.get('containers', list()), variables)

            if runtime_vars is not None:
                variables['$runtime'] = runtime_vars

            tester_list = list()
            if testers and type(testers) is list:

                for f in testers:

                    if not Path(f).is_absolute():
                        f = path.parent.joinpath(f)

                    tester = Tester.from_file(f, variables, runtime_vars, error_mode)
                    tester_list.append(tester)

            tests = None
            if definitions and type(definitions) is list:
                tests = Test.from_list(path, definitions, variables, error_mode)

            elif not tester_list:
                raise TesterKeyError('tests', path, optional='testers')

            return Tester(path, t['name'], t.get('title'), variables, tests, tester_list, containers, plugins, error_mode)

        except KeyError as e:
            raise TesterKeyError(str(e), path)

    def from_file(filename: str, initial_vars: dict[str, Any] = dict(), runtime_vars: dict[str, Any] = None,
                  error_mode: str = None) -> Tester:
        '''
        Creates a new Tester object from a .yml file. The .yml file obviously needs to be in the
        expected format and requires all keys that are needed to construct a Tester object.

        Parameters:
            filename        File system path to the corresponding .yml file
            initial_vars    Additional variables. This is used internally when nesting Testers
            runtime_vars    Runtime variables (only specifiable when using tricot as library)

        Returns:
            Tester          Tester object created from the file
        '''
        with open(filename, 'r') as f:
            config_dict = yaml.safe_load(f.read())

        return Tester.from_dict(config_dict, initial_vars, runtime_vars, Path(filename), error_mode)

    def contains_testers(self, testers: list[str]) -> bool:
        '''
        Checks whether the specified tester name is contained within the current test tree.

        Parameters:
            testers         List of tester names to look for

        Returns:
            bool            True if tester is contained within test tree
        '''
        if len(testers) == 0:
            return True

        for tester in testers:

            if self.name == tester:
                return True

        for tester in self.testers:

            if tester.contains_testers(testers):
                return True

        return False

    def run(self, testers: list[str] = (), numbers: list[str] = (), hotplug_variables: dict[str, Any] = {}) -> None:
        '''
        Runs the test: Prints the title of the tester and iterates over all contained
        Test objects and calls their 'run' method.

        Parameters:
            tester              Can be specified to only run tests within the specified testers
            numbers             Can be specified to only run the specified test numbers
            hotplug_variables   Dictionary of variables that are applied at runtime.

        Returns:
            None
        '''
        if not self.contains_testers(testers):
            return

        Tester.increase()
        Logger.print_mixed_yellow('Starting test:', self.title)
        hotplug = hotplug_variables.copy()

        Logger.increase_indent()

        for container in self.containers:
            container.start_container()
            hotplug = {**hotplug, **container.get_container_variables()}

        for plugin in self.plugins:
            plugin._run(hotplug)

        if self.tests and (len(testers) == 0 or self.name in testers):
            Logger.print('')
            for ctr in range(len(self.tests)):
                if len(numbers) == 0 or str(ctr+1) in numbers:
                    self.tests[ctr].run(f'{ctr+1}.', hotplug)

        self.run_childs(testers, numbers, hotplug)

        for container in self.containers:
            container.stop_container()

        for plugin in self.plugins:
            plugin._stop()

        Logger.decrease_indent()

    def run_childs(self, testers: list[str] = (), numbers: list[str] = (), hotplug_variables: dict[str, Any] = {}) -> None:
        '''
        Runs the child testers of the current tester.

        Parameters:
            tester              Can be specified to only run tests within the specified testers
            numbers             Can be specified to only run the specified test numbers
            hotplug_variables   Dictionary of variables that are applied at runtime.

        Returns:
            None
        '''
        for tester in self.testers:
            try:

                if self.name in testers:
                    tester.run(numbers=numbers, hotplug_variables=hotplug_variables)

                else:
                    tester.run(testers, numbers, hotplug_variables)

            except tricot.PluginException as e:

                tricot.Logger.print("")

                if self.error_mode == 'break':
                    raise e

                else:
                    tricot.Logger.print_mixed_yellow('Caught', 'PluginException', 'during plugin execution.', e=True)
                    tricot.Logger.print_mixed_blue('Original exception:', f'{type(e.original).__name__} - {e.original}')
                    tricot.Logger.print_blue('Tester is skipped.', e=True)

    def increase() -> None:
        '''
        Helper function that increases the global tester count and prints an offset
        if the current tester is not the first one.
        '''
        if Tester.tester_count != 0:
            Logger.print('')

        Tester.tester_count += 1
