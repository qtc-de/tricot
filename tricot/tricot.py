from __future__ import annotations

import copy
import yaml
import glob
from shutil import which
from typing import Any, Union
from pathlib import Path

import tricot.utils
from tricot.docker import TricotContainer
from tricot.logging import Logger
from tricot.validation import Validator, ValidationException
from tricot.extractor import Extractor
from tricot.plugin import Plugin
from tricot.command import Command
from tricot.condition import Condition


skip_until = None
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


class TricotRequiredFile(Exception):
    '''
    Custom exception class for a missing required file.
    '''


class TricotRequiredCommand(Exception):
    '''
    Custom exception class for a missing required command.
    '''


class TricotVersionMismatch(Exception):
    '''
    Custom exception class when a mismatching tricot version was used.
    '''


class ExceptionWrapper(Exception):
    '''
    Custom exception class that wraps around the actual exception and
    allows storing additional information.
    '''
    def __init__(self, original: Exception, path: Path = None) -> None:
        '''
        Store the original exception as well as the path of the file that
        caused it.
        '''
        self.path = str(path.resolve())
        self.original = original
        super().__init__(str(original))


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

                        if val[ctr] == key and type(value) is list:
                            val[ctr:ctr+1] = value

                        else:
                            val[ctr] = val[ctr].replace(key, str(value))

                    else:
                        val[ctr] = str(val[ctr])

        if type(val) is not list:
            raise ValueError(f"The '{k}' key needs to be a list within the ")

        return val

    def from_dict(path: Path, input_dict: dict, variables: dict[str, Any] = {}, error_mode: str = 'continue',
                  environment: dict = {}, conditionals: set[Condition] = set(), output_conf: dict = {},
                  parent_groups: list[list[str]] = list(), suggested_id: str = None) -> Test:
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
            suggested_id    Tets ID suggested by the id_pattern

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
                        conditions, conditionals, j.get('id', suggested_id), groups)

            test.set_logfile(j.get('logfile'))
            test.set_output(tricot.utils.merge(output_conf, j.get('output', {}), 'output', path))

            return test

        except KeyError as e:
            raise TestKeyError(str(e), path)

        except ValueError as e:
            raise TestKeyError(None, path, str(e))

    def from_list(path: Path, input_list: list, variables: dict[str, Any] = {}, error_mode: str = 'continue',
                  env: dict = {}, conditionals: set[Condition] = set(), output_conf: dict = {},
                  parent_groups: list[list[str]] = list(), id_pattern: str = None) -> list[Test]:
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
            id_pattern      Pattern to create test IDs from

        Returns
            list[Test]      List of Test objects created from the .yml input
        '''
        tests = list()

        if type(input_list) is not list:
            raise TestKeyError(None, path, 'Test defintions need to be specified as list within the ')

        for ctr in range(len(input_list)):

            if id_pattern is not None:
                suggested_id = id_pattern.format(ctr)

            else:
                suggested_id = None

            try:
                test = Test.from_dict(path, input_list[ctr], variables, error_mode, env, conditionals,
                                      output_conf, parent_groups, suggested_id)
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
            Logger.cprint('skipped.', color='grey')
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

    def __init__(self, path: Path, title: str, variables: dict[str, Any], tests: list[Test], testers: list[Tester],
                 containers: list[TricotContainer], plugins: list[Plugin], conditions: dict, conditionals: set[Condition],
                 error_mode: str, tester_id: str, test_groups: list[list[str]], requires: dict) -> None:
        '''
        Initializes a new Tester object.

        Parameters:
            path            Path object to the Testers configuration file
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
            requires        Requirements to run the tester

        Returns:
            None
        '''
        self.path = path
        self.title = title
        self.variables = variables
        self.tests = tests
        self.testers = testers
        self.containers = containers
        self.plugins = plugins
        self.conditions = conditions
        self.conditionals = conditionals
        self.error_mode = error_mode

        if tester_id is None:
            self.id = self.title

        else:
            self.id = str(tester_id)

            if self.id in assigned_ids:
                raise DuplicateIDError(f"ID '{self.id}' was assigned twice.")

            assigned_ids.add(self.id)

        self.groups = test_groups
        self.requires = requires

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
            id_pattern = tricot.utils.verify_id_pattern(t.get('id_pattern'), path)

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

                    testers_to_add = []
                    for ff in sorted(glob.glob(str(f))):

                        if Path(ff).is_file() and (ff.endswith('.yml') or ff.endswith('.yaml')):
                            tester = Tester.from_file(ff, variables, None, error_mode, env, conds, output_c, groups)
                            testers_to_add.append(tester)

                    testers_to_add.sort(key=lambda x: x.id)
                    tester_list += testers_to_add

            tests = None
            if definitions and type(definitions) is list:
                tests = Test.from_list(path, definitions, variables, error_mode, env, conds, output_c, groups, id_pattern)

            elif not tester_list:
                raise TesterKeyError('tests', path, optional='testers')

            new_tester = Tester(path, t['title'], variables, tests, tester_list, containers, plugins,
                                run_conds, conds, error_mode, t.get('id'), groups, t.get('requires'))
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

            try:
                config_dict = yaml.safe_load(f.read())

            except yaml.parser.ParserError as e:
                raise ExceptionWrapper(e, Path(filename))

        if '$env' not in initial_vars:
            tricot.utils.add_environment(initial_vars)

        if runtime_vars is not None and '$runtime' not in initial_vars:
            initial_vars['$runtime'] = runtime_vars

        return Tester.from_dict(config_dict, initial_vars, Path(filename), error_mode, env, conditionals,
                                output_conf, test_groups)

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
            self.runall = True
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
            self.runall = True
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

    def check_requirements(self):
        '''
        Checks whether all requirements for the current tester are satisfied. Since a
        successful run also requires successful sub-testers, sub-tester requirements are
        also checked.

        Parameters:
            None

        Returns:
            None
        '''
        if not self.requires or type(self.requires) is not dict:
            return

        requires = tricot.utils.apply_variables(self.requires, self.variables)

        for file in requires.get('files', []):

            if type(file) is str and not Path(file).exists():
                raise ExceptionWrapper(TricotRequiredFile(file), self.path)

            elif type(file) is dict:

                if not tricot.utils.file_integrity(file):
                    raise ExceptionWrapper(TricotRequiredFile(file.get('filename') + " (wrong hash value)"), self.path)

        for command in requires.get('commands', []):

            if which(command) is None:
                raise ExceptionWrapper(TricotRequiredCommand(command), self.path)

        version = requires.get('tricot')
        if not tricot.utils.match_version(version):

            message = ''
            for item in ['lt', 'le', 'eq', 'gt', 'ge']:

                ver = version.get(item)

                if ver is not None:
                    message += f'{item}: {ver} '

            raise ExceptionWrapper(TricotVersionMismatch(message), self.path)

        for tester in self.testers:
            tester.check_requirements()

    def filter(self, ids: set[str], groups: list[list[str]], exclude: set[str],
               exclude_groups: list[list[str]]) -> bool:
        '''
        Walks down the tester tree and removes all tests / testers that should be excluded
        by the current test configuration. If filtering is desired, this should be run before
        the tester.run method. The return value indicates whether the current tester has
        tests / testers left after the filtering has applied.

        Parameters:
            ids                 Set of Test / Tester IDs to run
            groups              List of group lists to run
            exclude             Set of Test / Tester IDs to exclude
            exclude_groups      List of group lists to exclude

        Returns:
            bool                Whether or not the tester has tests / testers left
        '''
        if self.skip_test(exclude, exclude_groups):
            return False

        elif not self.contains_id(ids) or not self.contains_group(groups):
            return False

        elif tricot.skip_until:

            if tricot.skip_until == self.id:
                tricot.skip_until = None

        if self.runall:
            self.filter_tests(None, None, exclude, exclude_groups)
            self.filter_testers(None, None, exclude, exclude_groups)

        else:
            self.filter_tests(ids, groups, exclude, exclude_groups)
            self.filter_testers(ids, groups, exclude, exclude_groups)

        if not self.tests and not self.testers:
            return False

        return True

    def filter_testers(self, ids: set[str], groups: list[list[str]], exclude: set[str],
                       exclude_groups: list[list[str]]) -> None:
        '''
        Iterates the tester array and removes all testers that should not be included by
        the current filter configuration.

        Parameters:
            ids                 Set of Test / Tester IDs to run
            groups              List of group lists to run
            exclude             Set of Test / Tester IDs to exclude
            exclude_groups      List of group lists to exclude

        Returns:
            None
        '''
        if not self.testers:
            return

        for tester in list(self.testers):
            if not tester.filter(ids, groups, exclude, exclude_groups):
                self.testers.remove(tester)

    def filter_tests(self, ids: set[str], groups: list[list[str]], exclude: set[str],
                     exclude_groups: list[list[str]]) -> None:
        '''
        Iterates the test array and removes all tests that should not be included by the
        current filter configuration.

        Parameters:
            ids                 Set of Test / Tester IDs to run
            groups              List of group lists to run
            exclude             Set of Test / Tester IDs to exclude
            exclude_groups      List of group lists to exclude

        Returns:
            None
        '''
        if not self.tests:
            return

        for test in list(self.tests):

            if tricot.skip_until:

                if tricot.skip_until == test.id:
                    tricot.skip_until = None

                else:
                    self.tests.remove(test)
                    continue

            if test.skip_test(exclude, exclude_groups):
                self.tests.remove(test)

            elif ids and not {test.id}.issubset(ids):
                self.tests.remove(test)

            elif groups and not tricot.utils.groups_contain(groups, test.groups):
                self.tests.remove(test)

    def run(self, hotplug_variables: dict[str, Any] = dict()) -> None:
        '''
        Runs the tester. Iterates over the tests and tester array and runs all
        tests / testers inside of it.

        Parameters:
            hotplug_variables   Hotplug variables to use during the test

        Returns:
            None
        '''
        if not self.tests and not self.testers:
            Logger.print_mixed_yellow('Skipping empty test:', self.title)
            return

        if not Condition.check_conditions(self.conditions, self.conditionals):
            Logger.print_mixed_yellow('Skipping test:', self.title)
            return

        tricot.Logger.print('')
        Logger.add_logfile(self.logfile)
        Logger.print_mixed_yellow('Starting test:', self.title, end=' ')

        if self.id and self.id != self.title:
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

        self.run_tests(hotplug)
        self.run_childs(hotplug)

        for container in self.containers:
            container.stop_container()

        for plugin in self.plugins:
            plugin._stop()

        Logger.remove_logfile(self.logfile)
        Logger.decrease_indent()

    def run_tests(self, hotplug_variables: dict[str, Any]) -> None:
        '''
        Wrapper function that executes the tests specified in a tester.

        Parameters:
            hotplug_variables   Hotplug variables to use during the test

        Returns:
            None
        '''
        if not self.tests:
            return

        Logger.print('')

        for ctr in range(len(self.tests)):
            self.tests[ctr].run(f'{ctr+1}.', hotplug_variables)

    def run_childs(self, hotplug_variables: dict[str, Any]) -> None:
        '''
        Runs the child testers of the current tester.

        Parameters:
            hotplug_variables   Hotplug variables to use during the test

        Returns:
            None
        '''
        for tester in self.testers:

            try:
                tester.run(hotplug_variables)

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
