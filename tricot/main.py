#!/usr/bin/env python3

from __future__ import annotations

import io
import sys
import yaml
import docker
import tricot
import argparse

from tricot.constants import VERSION


class FullHelpParser(argparse.ArgumentParser):
    '''
    Custom ArgumentParser class to show more helpful help messages per default.
    Taken from: https://stackoverflow.com/a/4042861
    '''
    def error(self, message):
        '''
        Show the whole help menu per default.
        '''
        sys.stderr.write(f'error: {message}\n\n')
        self.print_help()
        sys.exit(2)


parser = FullHelpParser(description=f'''tricot v{VERSION} - a trivial command tester to verify that commands,
                                        scripts or executables behave as expected. It uses .yml files for test
                                        definitions and can be used from the command line or as a python library.''',
                                        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=60))

parser.add_argument('--continue-from', dest='continue_from', metavar='id', help='continue from the specified test / tester id')
parser.add_argument('--debug', dest='debug', action='store_true', help='enable debug output')
parser.add_argument('--exclude-ids', dest='eids', metavar='id', nargs='+', default=[], help='exclude the specified test / tester IDs')
parser.add_argument('--exclude-groups', dest='egroups', metavar='group', nargs='+', default=[], help='exclude the specified test groups')
parser.add_argument('file', metavar='file', nargs='+', help='test definition (.yml file)')
parser.add_argument('--groups', metavar='group', nargs='+', default=[], help='only run the specified test groups')
parser.add_argument('--ids', metavar='id', nargs='+', default=[], help='only run the specified test / tester IDs')
parser.add_argument('--logfile', dest='log', metavar='file', type=argparse.FileType('w'), help='mirror output into a logfile')
parser.add_argument('--load', dest='load', metavar='file', nargs='+', default=[], type=argparse.FileType('r'), help='custom validators, extractors and plugins')
parser.add_argument('--positionals', dest='pos', metavar='var', nargs='+', default=[], help='positional variables (accessible by $1, $2, ...)')
parser.add_argument('-q', '--quite', dest='quite', action='store_true', help='disable verbose output during tests')
parser.add_argument('--skip-until', dest='skip_until', metavar='id', help='skip until the specified test / tester id')
parser.add_argument('--template', dest='template', choices=['tester', 'plugin', 'validator', 'extractor'], help='write a template file')
parser.add_argument('--variables', dest='vars', metavar='vars', nargs='+', default=[], help='runtime variables')
parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='enable verbose logging during tests')


def raise_if_debug(args: argparse.Namespace, e: Exception) -> None:
    '''
    Checks whether the debug option is set and if so raises the specified Exception.

    Paramaters:
        args            argparse namespace
        e               Exception to raise if debug is enabled

    Returns:
        None
    '''
    if args.debug:
        raise e from None


def split_variable(var: str, variables: dict) -> None:
    '''
    Attempts to split a key=value string at the equal sign and
    adds it to the variables dictionary.

    Parameters:
        var         key=value string
        variables   Dictionary to add the key, value pair to

    Returns:
        None
    '''
    try:
        key, value = var.split('=')
        variables[key] = value

    except ValueError:
        tricot.Logger.print_mixed_yellow(f"Variable '{var}' does not match the 'key=value' pattern.")
        sys.exit(tricot.constants.VALUE_ERROR)


def write_template(path: str, template_type: str) -> None:
    '''
    Handles the --template option and writes the desired template to the specified
    location. Exits the program afterwards as no other actions are expected.

    Parameters:
        path            Path to write the template file to
        template_type   Type of template to write

    Returns:
        None
    '''
    try:
        tricot.Logger.print_mixed_yellow('Writing template file to', path)
        tricot.write_template(path, template_type)
        sys.exit(0)

    except Exception as e:
        tricot.Logger.print_mixed_blue('Caught', 'unexpected Exception', e=True)
        tricot.Logger.increase_indent()
        tricot.Logger.print_with_indent_blue(str(e), e=True)
        sys.exit(tricot.constants.UNKNOWN)


def initialize_logger(args: argparse.Namespace) -> None:
    '''
    Sets the verbosity level and log file according to the specified options.

    Parameters:
        args        Namespace parsed by argparse

    Returns:
        None
    '''
    if args.verbose:
        tricot.Logger.set_verbosity(2)

    if args.quite:
        tricot.Logger.set_verbosity(0)

    if args.debug:
        tricot.Logger.set_verbosity(3)

    if args.log:
        tricot.Logger.add_logfile(args.log)


def load(files: list[io.TextIOWrapper]) -> None:
    '''
    Loads the content of the specified, opened files and closes them.

    Parameters:
        files       List of opened files by argparse

    Returns:
        None
    '''
    for file in files:
        exec(file.read())
        file.close()


def prepare_variables(args: argparse.Namespace) -> dict:
    '''
    Parses the variables specified on the command line and returns them within a dictionary.

    Parameters:
        args        Namespace parsed by argparse

    Returns:
        variables   Dictionary containing the variables
    '''
    variables = dict()

    for ctr in range(len(args.pos)):
        variables[ctr + 1] = args.pos[ctr]

    for var in args.vars:
        split_variable(var, variables)

    return variables


def main():
    '''
    Simply executes a tricot test using the file system paths specified on the command line.

    Parameters:
        None

    Returns:
        None
    '''
    args = parser.parse_args()
    initialize_logger(args)

    if args.template:
        write_template(args.file[0], args.template)

    load(args.load)
    variables = prepare_variables(args)

    groups = tricot.utils.parse_groups(args.groups)
    egroups = tricot.utils.parse_groups(args.egroups)

    if args.skip_until:
        tricot.skip_until = args.skip_until.strip("[|]")
    elif args.continue_from:
        tricot.skip_until = args.continue_from.strip("[|]")

    tricot.Logger.print_mixed_yellow('tricot', f'v{VERSION}', '- Starting tests...')

    for yml_file in args.file:

        try:
            tester = tricot.Tester.from_file(yml_file, runtime_vars=variables)
            tester.filter_tests(set(args.ids), groups, set(args.eids), egroups)
            tester.filter_testers(set(args.ids), groups, set(args.eids), egroups)
            tester.check_requirements()
            tester.run()

        except KeyboardInterrupt:
            tricot.Logger.reset_indent()
            tricot.Logger.print('')
            tricot.Logger.print_mixed_yellow('Caught', 'KeyboardInterrupt', 'from user.')
            tricot.Logger.print('Stopping current test.')
            sys.exit(tricot.constants.KEYBOARD_INTERRUPT)

        except Exception as excpt:

            raise_if_debug(args, excpt)
            try:
                raise excpt

            except tricot.ValidatorError as e:
                tricot.Logger.print_mixed_red('Caught', 'ValidatorError', 'while parsing test configuration.', e=True)
                tricot.Logger.print('Validator instantiation caused the following error:', e=True)
                tricot.Logger.increase_indent()
                tricot.Logger.print_blue(str(e), e=True)
                tricot.Logger.print_mixed_yellow('Configuration file:', e.path, e=True)
                sys.exit(tricot.constants.VALIDATOR_ERROR)

            except tricot.ValidationException:
                tricot.Logger.print_mixed_yellow('Caught', 'ValidationException', 'while error mode is set to break.', e=True)
                tricot.Logger.print_blue('Stopping test.', e=True)
                sys.exit(tricot.constants.VALIDATION_EXCEPTION)

            except tricot.ExtractException:
                tricot.Logger.print_mixed_yellow('Caught', 'ExtractException', 'while error mode is set to break.', e=True)
                tricot.Logger.print_blue('Stopping test.', e=True)
                sys.exit(tricot.constants.EXTRACT_EXCEPTION)

            except tricot.ExtractorError as e:
                tricot.Logger.print_mixed_red('Caught', 'ExtractorError', 'while parsing test configuration.', e=True)
                tricot.Logger.print('Extractor instantiation caused the following error:', e=True)
                tricot.Logger.increase_indent()
                tricot.Logger.print_blue(str(e), e=True)
                tricot.Logger.print_mixed_yellow('Configuration file:', e.path, e=True)
                sys.exit(tricot.constants.EXTRACTOR_ERROR)

            except (tricot.TestKeyError, tricot.TesterKeyError) as e:
                tricot.Logger.print_mixed_yellow('Caught', 'KeyError', 'while parsing test configuration.', e=True)
                tricot.Logger.print_blue(str(e), e=True)
                tricot.Logger.print_mixed_yellow('Configuration file:', e.path, e=True)
                sys.exit(tricot.constants.TEST_KEY_ERROR)

            except (tricot.utils.TricotRuntimeVariableError, tricot.utils.TricotEnvVariableError) as e:
                tricot.Logger.print_mixed_yellow('Caught', 'KeyError', 'while parsing test configuration.', e=True)
                tricot.Logger.print_blue(str(e), e=True)
                sys.exit(tricot.constants.VARIABLE_ERROR)

            except tricot.PluginError as e:
                tricot.Logger.print_mixed_yellow('Caught', 'PluginError', 'while parsing test configuration.', e=True)
                tricot.Logger.print('Plugin instantiation caused the following error:', e=True)
                tricot.Logger.increase_indent()
                tricot.Logger.print_blue(str(e), e=True)
                tricot.Logger.print_mixed_yellow('Configuration file:', e.path, e=True)
                sys.exit(tricot.constants.PLUGIN_ERROR)

            except tricot.PluginException as e:
                tricot.Logger.print_mixed_yellow('Caught', 'PluginException', 'from', end='', e=True)
                tricot.Logger.print_mixed_blue_plain('', e.name, 'plugin in', end=' ')
                tricot.Logger.print_yellow_plain(e.path.absolute())
                tricot.Logger.print_mixed_blue('Original exception:', f'{type(e.original).__name__} - {e.original}')
                tricot.Logger.print_blue('Stopping test.', e=True)
                sys.exit(tricot.constants.PLUGIN_EXCEPTION)

            except tricot.ConditionFormatException as e:
                tricot.Logger.print_mixed_yellow('Caught', 'ConditionFormatException', 'while parsing test configuration.', e=True)
                tricot.Logger.print('Condition instantiation caused the following error:', e=True)
                tricot.Logger.increase_indent()
                tricot.Logger.print_blue(str(e), e=True)
                tricot.Logger.print_mixed_yellow('Configuration file:', e.path, e=True)
                sys.exit(tricot.constants.CONDITION_FORMAT_ERROR)

            except tricot.TricotException as e:
                tricot.Logger.print('Encountered an unexpected error.', e=True)
                tricot.Logger.print_blue(str(e), e=True)

                if e.path:
                    tricot.Logger.print_mixed_yellow('Configuration file:', e.path, e=True)

                sys.exit(tricot.constants.TRICOT_EXCEPTION)

            except FileNotFoundError as e:
                tricot.Logger.print_mixed_yellow('Caught', 'FileNotFoundError', 'while parsing test configuration.', e=True)
                tricot.Logger.print_with_indent_blue(str(e), e=True)
                sys.exit(tricot.constants.FILE_NOT_FOUND)

            except docker.errors.APIError as e:
                tricot.Logger.print_mixed_yellow('Caught', 'docker APIError', 'while parsing test configuration.', e=True)
                tricot.Logger.print('This usually indicates an error when pulling docker images.', e=True)
                tricot.Logger.print_mixed_blue('Make sure that the specified container exists and that you are', 'authenticated',
                        'to the corresponding registry.', e=True)

                tricot.Logger.print_yellow('Original Error:', e=True)
                tricot.Logger.increase_indent()
                tricot.Logger.print_with_indent_blue(str(e), e=True)
                sys.exit(tricot.constants.DOCKER_API)

            except tricot.DuplicateIDError as e:
                tricot.Logger.print_mixed_yellow('Caught', 'DuplicateIDError', 'while parsing test configuration.', e=True)
                tricot.Logger.print_with_indent_blue(str(e), e=True)
                sys.exit(tricot.constants.DUPLICATE_ID_ERROR)

            except tricot.TricotRuntimeError as e:
                tricot.Logger.print_mixed_blue('Caught', 'unexpected Exception', 'while running the test command.', e=True)
                tricot.Logger.print_yellow('Original Error:', e=True)
                tricot.Logger.increase_indent()
                tricot.Logger.print_with_indent_blue(str(e.original), e=True)
                sys.exit(tricot.constants.RUNTIME_ERROR)

            except tricot.ExceptionWrapper as wrapper:

                try:
                    raise wrapper.original

                except (yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
                    tricot.Logger.print_mixed_yellow('Caught', type(e).__name__, 'while parsing the test configuration.', e=True)
                    tricot.Logger.print_mixed_blue('Affected file:', wrapper.path, e=True)
                    tricot.Logger.print_yellow('Original Error:', e=True)
                    tricot.Logger.increase_indent()
                    tricot.Logger.print_with_indent_blue(str(e), e=True)
                    sys.exit(tricot.constants.PARSER_ERROR)

                except tricot.TricotRequiredFile as e:
                    tricot.Logger.print_mixed_yellow('Error: Test configuration requires missing file:', str(e), e=True)
                    tricot.Logger.print_mixed_blue('Affected configuration:', wrapper.path, e=True)
                    sys.exit(tricot.constants.MISSING_RESOURCE)

                except tricot.TricotRequiredCommand as e:
                    tricot.Logger.print_mixed_yellow('Error: Test configuration requires missing command:', str(e), e=True)
                    tricot.Logger.print_mixed_blue('Affected configuration:', wrapper.path, e=True)
                    sys.exit(tricot.constants.MISSING_RESOURCE)

                except tricot.TricotVersionMismatch as e:
                    tricot.Logger.print_mixed_yellow('Error: Test configuration requires different tricot version:', str(e), e=True)
                    tricot.Logger.print_mixed_blue('Affected configuration:', wrapper.path, e=True)
                    sys.exit(tricot.constants.VERSION_MISMATCH)

                except Exception as e:
                    tricot.Logger.print_mixed_yellow('Caught', 'unexpected Exception', 'while running tricot.', e=True)
                    tricot.Logger.increase_indent()
                    tricot.Logger.print_with_indent_blue(str(e), e=True)
                    sys.exit(tricot.constants.UNKNOWN)

            except yaml.scanner.ScannerError as e:
                tricot.Logger.print_mixed_yellow('Caught', 'yaml.scanner.ScannerError', 'while parsing test configuration.', e=True)
                tricot.Logger.print('Seems that there is a syntax error within your test configuration.', e=True)
                tricot.Logger.increase_indent()
                tricot.Logger.print_with_indent_blue(str(e), e=True)
                sys.exit(tricot.constants.YAML_SYNTAX_ERROR)

            except Exception as e:
                tricot.Logger.print_mixed_yellow('Caught', 'unexpected Exception', 'while running tricot.', e=True)
                tricot.Logger.increase_indent()
                tricot.Logger.print_with_indent_blue(str(e), e=True)
                sys.exit(tricot.constants.UNKNOWN)

        finally:
            tricot.Logger.reset_indent()


if __name__ == '__main__':
    main()
    sys.exit(tricot.constants.LAST_ERROR)
