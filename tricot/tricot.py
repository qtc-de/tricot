from __future__ import annotations

import copy
import yaml
import glob
from pathlib import Path
from typing import Any, Union

import tricot.utils
from tricot.docker import TricotContainer
from tricot.logging import Logger
from tricot.validation import Validator, ValidationException
from tricot.plugin import Plugin
from tricot.command import Command
from tricot.condition import Condition


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
    expected_keys = ['title', 'description', 'command', 'arguments', 'validators', 'timeout', 'env', 'conditions']

    def __init__(self, path: Path, title: str, error_mode: str, variables: dict[str, Any], command: list,
                 timeout: int, validators: list[Validator], env: dict, conditions: dict, conditionals: set[Condition]) -> None:
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
            env             Environment variables
            conditions      Conditions for running the current test
            conditionals    Conditionals defined by upper testers

        Returns:
            None
        '''
        self.path = path
        self.title = title
        self.error_mode = error_mode
        self.variables = variables
        self.command = Command(command)
        self.timeout = timeout
        self.validators = validators
        self.env = env
        self.conditions = conditions
        self.conditionals = conditionals

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

            value = tricot.utils.resolve_runtime_variables(variables, key, value)
            value = tricot.utils.resolve_env_variables(variables, key, value)
            key = '${'+str(key)+'}'

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

    def from_dict(path: Path, input_dict: dict, variables: dict[str, Any] = {},
                  error_mode: str = 'continue', environment: dict = {}, conditionals: set[Condition] = set()) -> Test:
        '''
        Creates a Test object from a dictionary. The dictionary is expected to be the content
        read in of a .yml file and needs all keys that are required for a test (validators,
        title and command).

        Parameters:
            path            Path object to the tests configuration file
            input_dict      Dictionary that defines all required information for a test
            variables       Variables that should be inherited from the global scope
            error_mode      Decides whether to break or continue on failure
            environment     Environment variables
            conditionals    Conditionals for running the test

        Returns:
            Test            Newly generated Test object
        '''
        try:
            j = input_dict
            var = {**variables, **j.get('variables', {})}
            validators = Validator.from_list(path, j['validators'], var)

            e_mode = j.get('error_mode') or error_mode
            env = tricot.utils.merge_environment(j.get('env'), environment, path)
            conditions = j.get('conditions', {})

            Condition.check_format(path, conditions, conditionals)

            command = Test.apply_variables(j['command'], var)
            arguments = Test.apply_variables(j.get('arguments'), var, 'arguments')

            if type(command) is not list:
                raise TestKeyError(None, path, "The 'command' key needs to be a list within the ")

            if arguments:

                if type(arguments) is not list:
                    raise TestKeyError(None, path, "The 'arguments' key needs to be a list within the ")

                command += arguments

            tricot.utils.check_keys(Test.expected_keys, input_dict)
            return Test(path, j['title'], e_mode, var, command, j.get('timeout'), validators, env, conditions, conditionals)

        except KeyError as e:
            raise TestKeyError(str(e), path)

        except ValueError as e:
            raise TestKeyError(None, path, str(e))

    def from_list(path: Path, input_list: list, variables: dict[str, Any] = {},
                  error_mode: str = 'continue', env: dict = {}, conditionals: set[Condition] = set()) -> list[Test]:
        '''
        Within .yml files, Tests are specified in form of a list. This function takes such a list,
        that contains each single test definition as another dictionary (like it is created when
        reading the .yml file) and returns a corresponding list of Test objects.

        Parameters:
            path            Path object to the tests configuration file
            input_list      List of test definitions as read in from a .yml file
            variables       Variables that should be inherited from the global scope
            error_mode      Decides whether to break or continue on failure
            env             Environment variables
            conditionals    Conditionals specified by the upper tester

        Returns
            list[Test]      List of Test objects created from the .yml input
        '''
        tests = list()

        if type(input_list) is not list:
            raise TestKeyError(None, path, 'Test defintions need to be specified as list within the ')

        for ctr in range(len(input_list)):

            try:
                test = Test.from_dict(path, input_list[ctr], variables, error_mode, env, conditionals)
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

        if not Condition.check_conditions(self.conditions, self.conditionals):
            Logger.print_yellow_plain("skipped.")
            Logger.decrease_indent()
            return

        self.command.run(self.path.parent, self.timeout, hotplug_variables, self.env)

        for validator in self.validators:

            try:
                validator._run(self.command, hotplug_variables)

            except Exception as e:

                if success:
                    Logger.print_plain_red("failed.")

                tricot.constants.LAST_ERROR = tricot.constants.VALIDATION_EXCEPTION
                Logger.handle_error(e, validator)
                Condition.update_conditions(self.conditions, self.conditionals, True)

                if self.error_mode == "break":
                    Logger.decrease_indent()
                    raise ValidationException('')

                else:
                    success = False

        if success:
            Condition.update_conditions(self.conditions, self.conditionals, False)
            Logger.print_plain_green("success.")
            Logger.handle_success(self.command, self.validators)

        hotplug_variables['$prev'] = self.command
        Logger.decrease_indent()


class Tester:
    '''
    The Tester class represents a single .yml file that contains Test definitions. It is basically
    an Object that contains the tester configuration and a reference to each Test object that should
    be executed during a run. A command test with tricot is intended to be started by a Tester object,
    by calling its 'run' method.
    '''
    tester_count = 0

    def __init__(self, path: Path, name: str, title: str, variables: dict[str, Any], tests: list[Test], testers: list[Tester],
                 containers: list[TricotContainer], plugins: list[Plugin], conditions: dict, conditionals: set[Condition],
                 error_mode: str) -> None:
        '''
        Initializes a new Tester object.

        Parameters:
            path            Path object to the Testers configuration file
            name            Name of the tester (used for identification)
            title           Title of the test (used for displaying)
            variables       Dictionary of global variables that should be applied to all Tests and Validators
            tests           List of Test objects that should run during a test
            testers         List of Tester object, that allows to nest tester objects
            containers      List of TricotContainer objects for the test
            plugins         List of Plugin objects for the test
            conditions      Conditions for running the current tester
            conditionals    Conditionals defined by the tester or upper testers
            error_mode      Decides what to do if a plugin fails (break|continue)
        '''
        self.name = name
        self.title = title or name
        self.variables = variables
        self.tests = tests
        self.testers = testers
        self.containers = containers
        self.plugins = plugins
        self.conditions = conditions
        self.conditionals = conditionals
        self.error_mode = error_mode

    def from_dict(input_dict: dict, initial_vars: dict[str, Any] = dict(),
                  path: Path = None, e_mode: str = None, environment: dict = {},
                  conditionals: set[Condition] = set()) -> Tester:
        '''
        Creates a new Tester object from a python dictionary. The dictionary is expected to be
        created by reading a .yml file that contains test defintions. It requires all keys that
        need to be present for creating the Tester and the Test objects. This method walks down
        basically the complete .yml tree and constructs all required objects on its way.

        Parameters:
            input_dict      Python dictionary as read in from a .yml file
            initial_vars    Additional variables. This is used internally when nesting Testers
            path            Path object to the testers configuration file
            e_mode          Error mode that was mayve inherited by the parent tester
            environment     Dictionary of environment variables to use within the test
            conditionals    Conditions inherited from the upper tester

        Returns:
            Tester          Tester object created from the dictionary
        '''
        try:
            g = input_dict
            t = input_dict['tester']

            env = tricot.utils.merge_environment(t.get('env'), environment, path)
            error_mode = t.get('error_mode') or e_mode
            conds = Condition.from_dict(path, t.get('conditionals', {})).union(conditionals)
            run_conds = t.get('conditions', {})

            Condition.check_format(path, run_conds, conds)

            testers = g.get('testers')
            definitions = g.get('tests')

            variables = g.get('variables', dict())
            variables = {**initial_vars, **variables}
            variables['cwd'] = path.parent
            variables = tricot.utils.apply_variables(variables, copy.deepcopy(variables))

            plugins = Plugin.from_list(path, g.get('plugins'), variables)
            containers = TricotContainer.from_list(g.get('containers', list()), path, variables)

            tester_list = list()
            if testers and type(testers) is list:

                for f in testers:

                    if not Path(f).is_absolute():
                        f = path.parent.joinpath(f)

                    for ff in glob.glob(str(f)):
                        tester = Tester.from_file(ff, variables, None, error_mode, env, conds)
                        tester_list.append(tester)

            tests = None
            if definitions and type(definitions) is list:
                tests = Test.from_list(path, definitions, variables, error_mode, env, conds)

            elif not tester_list:
                raise TesterKeyError('tests', path, optional='testers')

            return Tester(path, t['name'], t.get('title'), variables, tests, tester_list, containers, plugins,
                          run_conds, conds, error_mode)

        except KeyError as e:
            raise TesterKeyError(str(e), path)

    def from_file(filename: str, initial_vars: dict[str, Any] = dict(), runtime_vars: dict[str, Any] = None,
                  error_mode: str = None, env: dict = {}, conditionals: set[Condition] = set()) -> Tester:
        '''
        Creates a new Tester object from a .yml file. The .yml file obviously needs to be in the
        expected format and requires all keys that are needed to construct a Tester object.

        Parameters:
            filename        File system path to the corresponding .yml file
            initial_vars    Additional variables. This is used internally when nesting Testers
            runtime_vars    Runtime variables (only specifiable when using tricot as library)
            error_mode      Current error mode setting
            env             Current environment variables
            conditionals    Conditions inherited from the previous tester

        Returns:
            Tester          Tester object created from the file
        '''
        with open(filename, 'r') as f:
            config_dict = yaml.safe_load(f.read())

        if '$env' not in initial_vars:
            tricot.utils.add_environment(initial_vars)

        if runtime_vars is not None and '$runtime' not in initial_vars:
            initial_vars['$runtime'] = runtime_vars

        return Tester.from_dict(config_dict, initial_vars, Path(filename), error_mode, env, conditionals)

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

    def run(self, testers: list[str] = (), numbers: list[str] = (), exclude: list[str] = (),
            hotplug_variables: dict[str, Any] = {}) -> None:
        '''
        Runs the test: Prints the title of the tester and iterates over all contained
        Test objects and calls their 'run' method.

        Parameters:
            tester              Only run testers that match the specified names
            numbers             Only run tests that match the specified numbers
            exclude             Exclude the specified tester names
            hotplug_variables   Dictionary of variables that are applied at runtime.

        Returns:
            None
        '''
        if not self.contains_testers(testers) or self.name in exclude:
            return

        Tester.increase()

        if not Condition.check_conditions(self.conditions, self.conditionals):
            Logger.print_mixed_yellow('Skipping test:', self.title)
            return

        Logger.print_mixed_yellow('Starting test:', self.title)
        hotplug = hotplug_variables.copy()

        Logger.increase_indent()

        for plugin in self.plugins:
            plugin._run(hotplug)

        for container in self.containers:
            container.start_container()
            hotplug = {**hotplug, **container.get_container_variables()}

        if self.tests:
            Logger.print('')
            for ctr in range(len(self.tests)):
                if len(numbers) == 0 or (ctr+1) in numbers:
                    self.tests[ctr].run(f'{ctr+1}.', hotplug)

        self.run_childs(testers, numbers, exclude, hotplug)

        for container in self.containers:
            container.stop_container()

        for plugin in self.plugins:
            plugin._stop()

        Logger.decrease_indent()

    def run_childs(self, testers: list[str] = (), numbers: list[str] = (), exclude: list[str] = (),
                   hotplug_variables: dict[str, Any] = {}) -> None:
        '''
        Runs the child testers of the current tester.

        Parameters:
            tester              Only run testers that match the specified names
            numbers             Only run tests that match the specified numbers
            exclude             Exclude the specified tester names
            hotplug_variables   Dictionary of variables that are applied at runtime.

        Returns:
            None
        '''
        for tester in self.testers:
            try:

                if self.name in testers:
                    tester.run(numbers=numbers, exluce=exclude, hotplug_variables=hotplug_variables)

                else:
                    tester.run(testers, numbers, exclude, hotplug_variables)

            except tricot.PluginException as e:

                tricot.Logger.print("")

                if self.error_mode == 'break':
                    raise e

                else:
                    tricot.Logger.print_mixed_yellow('Caught', 'PluginException', 'from', end='', e=True)
                    tricot.Logger.print_mixed_blue_plain('', e.name, 'plugin in', end=' ')
                    tricot.Logger.print_yellow_plain(e.path.absolute())
                    tricot.Logger.print_mixed_blue('Original exception:', f'{type(e.original).__name__} - {e.original}')
                    tricot.Logger.print_blue('Tester is skipped.', e=True)

                    tricot.constants.LAST_ERROR = tricot.constants.PLUGIN_EXCEPTION

    def increase() -> None:
        '''
        Helper function that increases the global tester count and prints an offset
        if the current tester is not the first one.
        '''
        if Tester.tester_count != 0:
            Logger.print('')

        Tester.tester_count += 1
