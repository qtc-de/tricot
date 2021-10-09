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
from tricot.extractor import Extractor
from tricot.plugin import Plugin
from tricot.command import Command
from tricot.condition import Condition


assigned_ids = set()


class DuplicateIDError(Exception):
    '''
    Custom exception that is raised if two testers/tests use the same ID.
    '''


class TricotException(Exception):
    '''
    Custom exception class for general purpose and tricot related exceptions.
    '''
    def __init__(self, message: str, path: Path = None) -> None:
        '''
        Basically the default Exception class initializer, but accepts also the path
        to a configuration file.
        '''
        self.path = str(path.resolve())
        super().__init__(message)


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
    expected_keys = ['title', 'description', 'command', 'arguments', 'validators', 'timeout', 'env', 'conditions',
                     'logfile', 'shell', 'extractors', 'id', 'groups']

    def __init__(self, path: Path, title: str, error_mode: str, variables: dict[str, Any], command: Command,
                 timeout: int, validators: list[Validator], extractors: list[Extractor], env: dict, conditions: dict,
                 conditionals: set[Condition], test_id: str, test_groups: list[list[str]]) -> None:
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
            extractors      List of extractors to apply on the command output
            env             Environment variables
            conditions      Conditions for running the current test
            conditionals    Conditionals defined by upper testers
            test_id         Identifikation number of the test
            test_groups     Test groups that the test belongs to

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
        self.extractors = extractors
        self.env = env
        self.conditions = conditions
        self.conditionals = conditionals

        if test_id is None:
            self.id = self.title

        else:
            self.id = str(test_id)

            if self.id in assigned_ids:
                raise DuplicateIDError(f"ID '{self.id}' was assigned twice.")

            assigned_ids.add(self.id)

        self.groups = test_groups

        self.logfile = None
        self.success_string = 'success'
        self.failure_string = 'failed'
        self.success_color = 'green'
        self.failure_color = 'red'

    def set_logfile(self, logfile: str) -> None:
        '''
        Sets the logfile attribute on the Test object.

        Parameters:
            logfile         File system path to the logfile

        Returns:
            None
        '''
        if logfile is None:
            return

        logfile = tricot.utils.apply_variables(logfile, self.variables)
        self.logfile = open(logfile, 'w')

    def set_output(self, output_conf: dict) -> None:
        '''
        Parses an optional output dictionary that can be specified on test or tester level.
        The output dictionary can be used to overwrite default output values.

        Parameters:
            output_conf         Dictionary containing values like 'success_string' or 'success_color'

        Returns:
            None
        '''
        if not output_conf:
            return

        if type(output_conf) is not dict:
            raise TestKeyError('', 'When specified, output needs to be a dictionary.', self.path)

        self.success_string = output_conf.get('success_string') or self.success_string
        self.success_color = output_conf.get('success_color') or self.success_color

        self.failure_string = output_conf.get('failure_string') or self.failure_string
        self.failure_color = output_conf.get('failure_color') or self.failure_color

        tricot.utils.validate_color(self.success_color)
        tricot.utils.validate_color(self.failure_color)

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

    def from_dict(path: Path, input_dict: dict, variables: dict[str, Any] = {}, error_mode: str = 'continue',
                  environment: dict = {}, conditionals: set[Condition] = set(), output_conf: dict = {},
                  parent_groups: list[list[str]] = list()) -> Test:
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
            output_conf     Output configuration inherited by the tester
            parent_groups   Test groups inherited from the parent tester

        Returns:
            Test            Newly generated Test object
        '''
        try:
            j = input_dict
            var = tricot.utils.merge(variables, j.get('variables', {}), 'variables', path)
            validators = Validator.from_list(path, j['validators'], var)
            extractors = Extractor.from_list(path, j.get('extractors', []), var)
            groups = tricot.utils.merge_groups(parent_groups, list(map(lambda x: str(x), j.get('groups', []))))

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

            shell = j.get('shell', False)
            command = Command(command, shell)

            tricot.utils.check_keys(Test.expected_keys, input_dict)
            test = Test(path, j['title'], e_mode, var, command, j.get('timeout'), validators, extractors, env,
                        conditions, conditionals, j.get('id'), groups)

            test.set_logfile(j.get('logfile'))
            test.set_output(tricot.utils.merge(output_conf, j.get('output', {}), 'output', path))

            return test

        except KeyError as e:
            raise TestKeyError(str(e), path)

        except ValueError as e:
            raise TestKeyError(None, path, str(e))

    def from_list(path: Path, input_list: list, variables: dict[str, Any] = {}, error_mode: str = 'continue',
                  env: dict = {}, conditionals: set[Condition] = set(), output_conf: dict = {},
                  parent_groups: list[list[str]] = list()) -> list[Test]:
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
            output_conf     Output configuration inherited by the tester
            parent_groups   Test groups inherited from the parent tester

        Returns
            list[Test]      List of Test objects created from the .yml input
        '''
        tests = list()

        if type(input_list) is not list:
            raise TestKeyError(None, path, 'Test defintions need to be specified as list within the ')

        for ctr in range(len(input_list)):

            try:
                test = Test.from_dict(path, input_list[ctr], variables, error_mode, env, conditionals,
                                      output_conf, parent_groups)
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
        Logger.add_logfile(self.logfile)

        if self.id and self.id != self.title:
            Logger.print_blue(f'{prefix} [{self.id}] {self.title}...', end=' ', flush=True)
        else:
            Logger.print_blue(f'{prefix} {self.title}...', end=' ', flush=True)

        success = True

        if not Condition.check_conditions(self.conditions, self.conditionals):
            Logger.print_yellow_plain("skipped.")
            Logger.decrease_indent()
            return

        self.command.run(self.path.parent, self.timeout, hotplug_variables, self.env)
        extractor_error = None

        for extractor in self.extractors:

            try:
                extractor._extract(self.command, hotplug_variables)

            except Exception as e:

                if extractor.on_miss == 'continue':
                    continue

                elif extractor.on_miss == 'warn':
                    Logger.extract_warning(e, extractor)
                    continue

                elif extractor.on_miss == 'break':
                    extractor_error = e
                    break

        for validator in self.validators:

            try:
                validator._run(self.command, hotplug_variables, extractor_error)

            except Exception as e:

                if success:
                    f_color = validator.failure_color or self.failure_color
                    f_string = validator.failure_string or self.failure_string
                    Logger.cprint(f_string, color=f_color)

                if extractor_error is not None:
                    tricot.constants.LAST_ERROR = tricot.constants.EXTRACT_EXCEPTION
                else:
                    tricot.constants.LAST_ERROR = tricot.constants.VALIDATION_EXCEPTION

                Logger.handle_error(e, validator)
                Condition.update_conditions(self.conditions, self.conditionals, True)

                if self.error_mode == "break":
                    Logger.remove_logfile(self.logfile)
                    Logger.decrease_indent()

                    if extractor_error:
                        raise extractor_error

                    raise ValidationException('')

                elif extractor_error is not None:
                    success = False
                    break

                else:
                    success = False

        if success:
            Condition.update_conditions(self.conditions, self.conditionals, False)
            Logger.cprint(self.success_string, color=self.success_color)
            Logger.handle_success(self.command, self.validators)

        hotplug_variables['$prev'] = self.command
        Logger.remove_logfile(self.logfile)

    def skip_test(self, exclude: set[str], exclude_groups: list[list[str]]) -> bool:
        '''
        Checks whether the current test is contained within the exclude lists.

        Parameters:
            exclude             Set of Test / Tester IDs to exclude
            exclude_groups      List of group sets to exclude

        Returns:
            bool
        '''
        if exclude and self.id in exclude:
            return True

        elif exclude_groups and tricot.utils.groups_contain(exclude_groups, self.groups):
            return True

        return False


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
                 error_mode: str, tester_id: str, test_groups: list[list[str]]) -> None:
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
            tester_id       Unique identifikation number of the tester
            test_groups     Test groups that the tester belongs to

        Returns:
            None
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

        if tester_id is None:
            self.id = self.name

        else:
            self.id = str(tester_id)

            if self.id in assigned_ids:
                raise DuplicateIDError(f"ID '{self.id}' was assigned twice.")

            assigned_ids.add(self.id)

        self.groups = test_groups

        self.logfile = None
        self.runall = False

    def from_dict(input_dict: dict, initial_vars: dict[str, Any] = dict(),
                  path: Path = None, e_mode: str = None, environment: dict = {},
                  conditionals: set[Condition] = set(), output_conf: dict = {},
                  test_groups: list[list[str]] = []) -> Tester:
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
            output_conf     Output configuration inherited from the upper tester
            test_groups     List of test groups inherited from the upper tester

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
            output_c = tricot.utils.merge(output_conf, t.get('output', {}), 'output', path)

            Condition.check_format(path, run_conds, conds)

            testers = g.get('testers')
            definitions = g.get('tests')
            groups = tricot.utils.merge_groups(test_groups, list(map(lambda x: str(x), t.get('groups', []))))

            variables = tricot.utils.merge(initial_vars, g.get('variables', {}), 'variables', path)
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
                        tester = Tester.from_file(ff, variables, None, error_mode, env, conds, output_c, groups)
                        tester_list.append(tester)

            tests = None
            if definitions and type(definitions) is list:
                tests = Test.from_list(path, definitions, variables, error_mode, env, conds, output_c, groups)

            elif not tester_list:
                raise TesterKeyError('tests', path, optional='testers')

            new_tester = Tester(path, t['name'], t.get('title'), variables, tests, tester_list, containers, plugins,
                                run_conds, conds, error_mode, t.get('id'), groups)
            new_tester.set_logfile(t.get('logfile'))

            return new_tester

        except KeyError as e:
            raise TesterKeyError(str(e), path)

    def set_logfile(self, logfile: str) -> None:
        '''
        Sets the logfile attribute on the Tester object.

        Parameters:
            logfile         File system path to the logfile

        Returns:
            None
        '''
        if logfile is None:
            return

        logfile = tricot.utils.apply_variables(logfile, self.variables)
        self.logfile = open(logfile, 'w')

    def from_file(filename: str, initial_vars: dict[str, Any] = dict(), runtime_vars: dict[str, Any] = None,
                  error_mode: str = None, env: dict = {}, conditionals: set[Condition] = set(),
                  output_conf: dict = {}, test_groups: list[list[str]] = []) -> Tester:
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
            output_conf     Output configuration inherited from upper tester
            test_groups     List of test groups inherited from the upper tester

        Returns:
            Tester          Tester object created from the file
        '''
        with open(filename, 'r') as f:
            config_dict = yaml.safe_load(f.read())

        if '$env' not in initial_vars:
            tricot.utils.add_environment(initial_vars)

        if runtime_vars is not None and '$runtime' not in initial_vars:
            initial_vars['$runtime'] = runtime_vars

        return Tester.from_dict(config_dict, initial_vars, Path(filename), error_mode, env, conditionals,
                                output_conf, test_groups)

    def set_runall(self, value: bool) -> None:
        '''
        Sets the runall property of a tester. This is required when users specify a tetser ID on the command
        line. In this case, all tests and nested testers should be run, although their ID is not contained
        within the IDs to run. Setting the runall property on a tester disabled ID checking and runs everything
        inside of it anyway.

        Setting the runall property is done recursively for all nested testers.

        Parameters:
            value           Value to set for the runall property.

        Returns:
            None
        '''
        self.runall = value

        for tester in self.testers:
            tester.set_runall(value)

    def contains_id(self, t_ids: set[str]) -> bool:
        '''
        Checks whether the specified Test / Tester IDs are contained within this tester.

        Parameters:
            t_ids           Test / Tester IDs to look for

        Returns:
            bool            True if one of the ids is contained within the tester
        '''
        if not t_ids or self.runall:
            return True

        if self.id and {self.id}.issubset(t_ids):
            self.set_runall(True)
            return True

        if self.tests:

            for test in self.tests:
                if test.id and {test.id}.issubset(t_ids):
                    return True

        for tester in self.testers:
            if tester.contains_id(t_ids):
                return True

        return False

    def contains_group(self, t_groups: list[list[str]]) -> bool:
        '''
        Checks whether the specified Group set exists within the tester.

        Parameters:
            t_groups        List of group lists to check in

        Returns:
            bool            True if set of groups is contained within the tester
        '''
        if not t_groups or self.runall:
            return True

        if tricot.utils.groups_contain(t_groups, self.groups):
            self.set_runall(True)
            return True

        if self.tests:

            for test in self.tests:
                if tricot.utils.groups_contain(t_groups, test.groups):
                    return True

        for tester in self.testers:
            if tester.contains_group(t_groups):
                return True

        return False

    def skip_test(self, exclude: set[str], exclude_groups: list[list[str]]) -> bool:
        '''
        Checks whether the current test is contained within the exclude lists.

        Parameters:
            exclude             Set of Test / Tester IDs to exclude
            exclude_groups      List of group lists to exclude

        Returns:
            bool
        '''
        if exclude and self.id in exclude:
            return True

        elif exclude_groups and tricot.utils.groups_contain(exclude_groups, self.groups):
            return True

        return False

    def run(self, ids: set[str], groups: list[list[str]], exclude: set[str],
            exclude_groups: list[list[str]], hotplug_variables: dict[str, Any] = dict()) -> None:
        '''
        Runs the test: Prints the title of the tester and iterates over all contained
        Test objects and calls their 'run' method.

        Parameters:
            ids                 Set of Test / Tester IDs to run
            groups              List of group lists to run
            exclude             Set of Test / Tester IDs to exclude
            exclude_groups      List of group lists to exclude
            hotplug_variables   Hotplug variables to use during the test

        Returns:
            None
        '''
        if self.skip_test(exclude, exclude_groups):
            return

        if not self.contains_id(ids) or not self.contains_group(groups):
            return

        if not Condition.check_conditions(self.conditions, self.conditionals):
            Logger.print_mixed_yellow('Skipping test:', self.title)
            return

        tricot.Logger.print('')
        Logger.add_logfile(self.logfile)
        Logger.print_mixed_yellow('Starting test:', self.title, end=' ')

        if self.id and self.id != self.name:
            Logger.print_plain_blue(f'[{self.id}]')
        else:
            print()

        hotplug = hotplug_variables.copy()
        Logger.increase_indent()

        for plugin in self.plugins:
            plugin._run(hotplug)

        for container in self.containers:
            container.start_container()
            hotplug = {**hotplug, **container.get_container_variables()}

        self.run_tests(ids, groups, exclude, exclude_groups, hotplug)
        self.run_childs(ids, groups, exclude, exclude_groups, hotplug)

        for container in self.containers:
            container.stop_container()

        for plugin in self.plugins:
            plugin._stop()

        Logger.remove_logfile(self.logfile)
        Logger.decrease_indent()

    def run_tests(self, ids: set[str], groups: list[list[str]], exclude: set[str],
                  exclude_groups: list[list[str]], hotplug_variables: dict[str, Any]) -> None:
        '''
        Wrapper function that executes the tests specified in a tester.

        Parameters:
            ids                 Set of Test / Tester IDs to run
            groups              List of group lists to run
            exclude             Set of Test / Tester IDs to exclude
            exclude_groups      List of group lists to exclude
            hotplug_variables   Hotplug variables to use during the test

        Returns:
            None
        '''
        if not self.tests:
            return

        Logger.print('')
        runall = tricot.utils.groups_contain(groups, self.groups) or (ids and {self.id}.issubset(ids))

        for ctr in range(len(self.tests)):

            test = self.tests[ctr]

            if test.skip_test(exclude, exclude_groups):
                continue

            elif self.runall or runall:
                pass

            elif not ids and not groups:
                pass

            elif ids and {test.id}.issubset(ids):
                pass

            elif groups and tricot.utils.groups_contain(groups, test.groups):
                pass

            else:
                continue

            test.run(f'{ctr+1}.', hotplug_variables)

    def run_childs(self, ids: set[str], groups: list[list[str]], exclude: set[str],
                   exclude_groups: list[list[str]], hotplug_variables: dict[str, Any]) -> None:
        '''
        Runs the child testers of the current tester.

        Parameters:
            ids                 Set of Test / Tester IDs to run
            groups              List of group lists to run
            exclude             Set of Test / Tester IDs to exclude
            exclude_groups      List of group lists to exclude
            hotplug_variables   Hotplug variables to use during the test

        Returns:
            None
        '''
        for tester in self.testers:

            try:
                tester.run(ids, groups, exclude, exclude_groups, hotplug_variables)

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
                    tricot.Logger.decrease_indent()

                    tricot.constants.LAST_ERROR = tricot.constants.PLUGIN_EXCEPTION

    def increase() -> None:
        '''
        Helper function that increases the global tester count and prints an offset
        if the current tester is not the first one.
        '''
        if Tester.tester_count != 0:
            Logger.print('')

        Tester.tester_count += 1
