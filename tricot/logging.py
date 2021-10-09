from __future__ import annotations

import sys
import json
import typing
from termcolor import cprint

from tricot.command import Command
from tricot.validation import Validator, ValidationException, ValidatorError
from tricot.extractor import Extractor, ExtractException


class Logger:
    '''
    A very primitive Logger class to unify indentation, colors and prefixes.
    In future, this class could also implement additional logging strategies
    like e.g. printing to a file and so on. For now, we keep it simple :)

    The class has two static class variables. The 'indent' variable contains
    the current indentation level of print statements that are executed by
    the Logger. The 'verbosity' variable determines how verbose failed
    Validators should behave.

        Value: 0 -> Just print 'failed' without details
        Value: 1 -> Print 'failed' and show the Validator message
        Value: 2 -> Print 'failed', the validator message + cmd_output
    '''
    tee = None
    indent = 0
    verbosity = 1

    def cprint(string: str, **kwargs) -> None:
        '''
        Just a wrapper around termcolors cprint.
        '''
        cprint(string, **kwargs)

    def print(string: str, *args, e: bool = False, end: str = None) -> None:
        '''
        Print with prefix and indentation.
        '''
        print(Logger.get_prefix(e), string, *args, end=end)

    def print_plain(string: str, *args, end: str = None) -> None:
        '''
        Print with prefix.
        '''
        print(string, *args, end=end)

    def print_plain_green(string: str, end: str = None) -> None:
        '''
        Print without indent or prefix, text in green.
        '''
        cprint(string, color='green', end=end)

    def print_plain_red(string: str, end: str = None) -> None:
        '''
        Print without indent or prefix, text in red.
        '''
        cprint(string, color='red', end=end)

    def print_plain_blue(string: str, end: str = None) -> None:
        '''
        Print without indent or prefix, text in blue.
        '''
        cprint(string, color='blue', end=end)

    def print_yellow(string: str, e: bool = False, end: str = None) -> None:
        '''
        Print with prefix and indent, text in yellow.
        '''
        print(Logger.get_prefix(e), end=' ')
        cprint(string, color='yellow', end=end)

    def print_yellow_plain(string: str, e: bool = False, end: str = None) -> None:
        '''
        Print in yellow.
        '''
        cprint(string, color='yellow', end=end)

    def print_blue(string: str, e: bool = False, end: str = None, **kwargs) -> None:
        '''
        Print with prefix and indent, text in blue.
        '''
        print(Logger.get_prefix(e), end=' ', **kwargs)
        cprint(string, color='blue', end=end, **kwargs)

    def print_mixed_yellow(str1: str, str2: str, *args, e: bool = False,  end: str = None) -> None:
        '''
        Print with prefix and indent, first arg in normal text color, second arg
        in yellow and the rest of the args in normal text color again.
        '''
        print(Logger.get_prefix(e), str1, end=' ')

        if(args):
            cprint(str2, color='yellow', end=' ')
            print(*args, end=end)

        else:
            cprint(str2, color='yellow', end=end)

    def print_mixed_red(str1: str, str2: str, *args, e: bool = False,  end: str = None) -> None:
        '''
        Print with prefix and indent, first arg in normal text color, second arg
        in red and the rest of the args in normal text color again.
        '''
        print(Logger.get_prefix(e), str1, end=' ')

        if(args):
            cprint(str2, color='red', end=' ')
            print(*args, end=end)

        else:
            cprint(str2, color='red', end=end)

    def print_mixed_blue(str1: str, str2: str, *args, e: bool = False, end: str = None) -> None:
        '''
        Print with prefix and indent, first arg in normal text color, second arg
        in blue and the rest of the args in normal text color again.
        '''
        print(Logger.get_prefix(e), str1, end=' ')

        if(args):
            cprint(str2, color='blue', end=' ')
            print(*args, end=end)

        else:
            cprint(str2, color='blue', end=end)

    def print_mixed_blue_yellow(str1: str, str2: str, *args, e: bool = False, end: str = None) -> None:
        '''
        Print with prefix and indent, first arg in blue text color, second arg
        in yellow and the rest of the args in normal text color again.
        '''
        Logger.print_blue(str1, end=' ')

        if(args):
            cprint(str2, color='yellow', end=' ')
            print(*args, end=end)

        else:
            cprint(str2, color='yellow', end=end)

    def print_mixed_blue_plain(str1: str, str2: str, *args, e: bool = False, end: str = None) -> None:
        '''
        Print first arg in normal text color, second arg
        in blue and the rest of the args in normal text color again.
        '''
        print(str1, end=' ')

        if(args):
            cprint(str2, color='blue', end=' ')
            print(*args, end=end)

        else:
            cprint(str2, color='blue', end=end)

    def print_mixed_red_plain(str1: str, str2: str, *args, e: bool = False, end: str = None) -> None:
        '''
        Print first arg in normal text color, second arg
        in red and the rest of the args in normal text color again.
        '''
        print(str1, end=' ')

        if(args):
            cprint(str2, color='red', end=' ')
            print(*args, end=end)

        else:
            cprint(str2, color='red', end=end)

    def increase_indent() -> None:
        '''
        Increases the indentation level by one.
        '''
        Logger.indent += 1

    def decrease_indent() -> None:
        '''
        Decreases the indentation level by one.
        '''
        Logger.indent -= 1

        if Logger.indent < 0:
            Logger.indent = 0

    def reset_indent() -> None:
        '''
        Resets the indent level to 0.
        '''
        Logger.indent = 0

    def set_verbosity(level: int) -> None:
        '''
        Sets the verbosity level to the specified value
        '''
        Logger.verbosity = level

    def get_prefix(is_error: bool) -> None:
        '''
        Returns the globally used prefix. '[+]' on success and '[-]' on error.
        '''
        if is_error:
            return '[-]' + Logger.indent * 4 * ' '

        return '[+]' + Logger.indent * 4 * ' '

    def print_with_indent(string: str, e: bool = False) -> None:
        '''
        Takes a string, spilts it on newlines and prints each single line
        with the current prefix and indent.
        '''
        content = string.replace('\x0d', '\n')
        lines = content.split('\n')
        for line in lines:
            Logger.print(line, e=e)

    def print_with_indent_blue(string: str, e: bool = False) -> None:
        '''
        Takes a string, spilts it on newlines and prints each single line
        with the current prefix and indent in blue.
        '''
        content = string.replace('\x0d', '\n')
        lines = content.split('\n')
        for line in lines:
            Logger.print_blue(line, e=e)

    def add_logfile(file: typing.TextIO) -> None:
        '''
        Mirrors all output of tricot to the specified logfile.

        Parameters:
            file        Logfile to mirror to

        Returns:
            None
        '''
        if file is None:
            return

        if Logger.tee is None:
            Logger.tee = Tee(file)

        else:
            Logger.tee.add(file)

    def remove_logfile(file: typing.TextIO) -> None:
        '''
        Stop mirroring to the specified logfile.

        Parameters:
            file        Logfilt to stop mirroring to

        Returns:
            None
        '''
        if file is None or Logger.tee is None:
            return

        else:
            Logger.tee.close(file)

    def enable_stdout() -> None:
        '''
        Enables stdout on the loggers tee object.

        Parameters:
            None

        Returns:
            None
        '''
        if Logger.tee is None:
            return

        Logger.tee.enable_stdout()

    def disable_stdout() -> None:
        '''
        Disables stdout on the loggers tee object.

        Parameters:
            None

        Returns:
            None
        '''
        if Logger.tee is None:
            return

        Logger.tee.disable_stdout()

    def extract_warning(e: Exception, ext: Extractor) -> None:
        '''
        Print a warning message that the specified extractor did not
        worked as expected.

        Parameters:
            None

        Returns:
            None
        '''
        Logger.increase_indent()
        Logger.print_plain('')

        if type(e) is ExtractException:
            Logger.print_yellow('Warning:', end=' ')
            Logger.print_mixed_blue_plain('Extractor', ext.name, 'did not extract any values.')

        else:
            Logger.print_yellow('Warning:', end=' ')
            Logger.print_mixed_blue_plain('Extractor', ext.name, 'caused an unexpected exception:')
            Logger.print_yellow(str(e))

        Logger.print('', end='  --> ')
        Logger.decrease_indent()

    def handle_error(e: Exception, val: Validator) -> None:
        '''
        This function is called when a Validator failed to handle the error
        logging. It is basically a wrapper around '_handle_error', which
        performs the real error handling.
        '''
        Logger.increase_indent()
        Logger._handle_error(e, val)
        Logger.decrease_indent()

        if Logger.verbosity != 0:
            Logger.print('', e=True)

    def _handle_error(e: Exception, val: Validator) -> None:
        '''
        This functions handles Exceptions that are raised by validators.
        Depending on the current 'verbosity' level, a different amount of information
        is printed.
        '''
        if Logger.verbosity == 0:
            Logger.disable_stdout()

        if type(e) is ExtractException:
            Logger.print_mixed_yellow('- Caught', 'ExtractException', 'raised by the', end='', e=True)
            Logger.print_mixed_red_plain('', e.extractor.name, 'extractor.')
            Logger.print_mixed_blue('  Configuration file:', e.extractor.path.absolute(), e=True)

            if Logger.verbosity > 1:
                Logger.print('', e=True)

            Logger.print('  Extractor failed because of the following reason:', e=True)
            Logger.print_with_indent_blue('  ' + str(e), e=True)

        elif type(e) is ValidatorError:
            Logger.print_mixed_red('- Caught', 'ValidatorError', 'during validator instantiation.', e=True)
            Logger.print('  Validator instantiation failed because of the following reason:', e=True)
            Logger.print_blue('  ' + str(e), e=True)
            Logger.enable_stdout()
            return

        elif type(e) is ValidationException:
            Logger.print_mixed_yellow('- Caught', 'ValidationException', 'raised by the', end='', e=True)
            Logger.print_mixed_red_plain('', val.name, 'validator.')
            Logger.print_mixed_blue('  Configuration file:', val.path.absolute(), e=True)

            if Logger.verbosity > 1:
                Logger.print('', e=True)

            Logger.print('  Validator run failed because of the following reason:', e=True)
            Logger.print_with_indent_blue('  ' + str(e), e=True)

        else:
            Logger.print_mixed_yellow('- Caught unexpected', type(e).__name__, 'during validation process.', e=True)
            Logger.print_mixed_red('  The', val.name, 'validator raises probably an uncaught exception.', e=True)
            Logger.print_mixed_blue('  Message:', str(e), e=True)

        if Logger.verbosity <= 1:
            Logger.disable_stdout()

        Logger.print('', e=True)
        Logger.print_yellow('  Command:', e=True, end=' ')
        Logger.print_plain(val.command.command)
        Logger.print_yellow('  Command exit code:', end=' ', e=True)
        cprint(val.command.status, color='blue')

        Logger.print_yellow('  Command stdout:', e=True)
        if val.command.stdout:
            Logger.increase_indent()
            Logger.print_with_indent(val.command.stdout, e=True)
            Logger.decrease_indent()

        Logger.print_yellow('  Command stderr:', e=True)
        if val.command.stderr:
            Logger.increase_indent()
            Logger.print_with_indent(val.command.stderr, e=True)
            Logger.decrease_indent()

        if type(e) is ExtractException:
            Logger.print_yellow('  Extractor parameters:', e=True)
            Logger.increase_indent()
            Logger.print_with_indent(json.dumps(e.extractor.param, indent=4).replace(r'\n', '\n').replace(r'\t', '\t'), e=True)

        else:
            Logger.print_yellow('  Validator parameters:', e=True)
            Logger.increase_indent()
            Logger.print_with_indent(json.dumps(val.param, indent=4).replace(r'\n', '\n').replace(r'\t', '\t'), e=True)

        Logger.decrease_indent()
        Logger.enable_stdout()

    def handle_success(cmd: Command, val: list[Validator]) -> None:
        '''
        This function is called when all Validators have been passed.
        It is basically a wrapper around '_handle_success'.
        '''
        if Logger.tee is None:
            return

        if Logger.verbosity != 3:
            Logger.disable_stdout()

        Logger.increase_indent()
        Logger._handle_success(cmd, val)
        Logger.decrease_indent()
        Logger.print('')
        Logger.enable_stdout()

    def _handle_success(cmd: Command, val: list[Validator]) -> None:
        '''
        This functions handles Exceptions that are raised by validators.
        Depending on the current 'verbosity' level, a different amount of information
        is printed.
        '''
        Logger.print_mixed_yellow('-', 'Debug output:')
        Logger.increase_indent()
        Logger.print_yellow('Command:', end=' ')
        Logger.print_plain(cmd.command)
        Logger.print_yellow('Command exit code:', end=' ')
        cprint(cmd.status, color='blue')

        Logger.print_yellow('Command stdout:')
        if cmd.stdout:
            Logger.increase_indent()
            Logger.print_with_indent(cmd.stdout)
            Logger.decrease_indent()

        Logger.print_yellow('Command stderr:')
        if cmd.stderr:
            Logger.increase_indent()
            Logger.print_with_indent(cmd.stderr)
            Logger.decrease_indent()

        Logger.print_yellow('Validators:')
        Logger.increase_indent()
        for validator in val:
            Logger.print_yellow('Validator name:', end=' ')
            cprint(validator.name, color='blue')
            Logger.print_yellow('Validator parameters:')
            Logger.increase_indent()
            Logger.print_with_indent(json.dumps(validator.param, indent=4).replace(r'\n', '\n').replace(r'\t', '\t'))
            Logger.decrease_indent()

        Logger.decrease_indent()
        Logger.decrease_indent()


class Tee(object):
    '''
    Helper class to log stdout to a file. Copied from:
    https://stackoverflow.com/questions/616645/how-to-duplicate-sys-stdout-to-a-log-file
    '''

    def __init__(self, file: typing.TextIO) -> None:
        '''
        Create a new Tee object that is used to duplicate output to log files.

        Parameters:
            file        Logfile to mirror output to

        Returns:
            None
        '''
        self.file_names = [file.name]
        self.files = [file]
        self.stdout = sys.stdout
        self.use_stdout = True
        sys.stdout = self

    def __del__(self) -> None:
        '''
        Set sys.stdout back to it's default value and close all logfiles.

        Parameters:
            None

        Returns:
            None
        '''
        sys.stdout = self.stdout
        for file in self.files:
            file.close()

    def write(self, data) -> None:
        '''
        Write output to stdout if 'use_stdout' is True. Furthermore, write
        output to all open logfiles.

        Parameters:
            data        Data to write

        Returns:
            None
        '''
        if self.use_stdout:
            self.stdout.write(data)
        for file in self.files:
            file.write(data)

    def flush(self) -> None:
        '''
        Flusth pending output on all files.

        Parameters:
            None

        Returns:
            None
        '''
        for file in self.files:
            file.flush()

    def add(self, file: typing.TextIO) -> None:
        '''
        Add a new logfile where output is mirrored to.

        Parameters:
            file        File to mirror output to

        Returns:
            None
        '''
        if file.name not in self.file_names:
            self.file_names.append(file.name)
            self.files.append(file)

    def close(self, file: typing.TextIO) -> None:
        '''
        Close a logfile and stop mirroring data to it.

        Parameters:
            None

        Returns:
            None
        '''
        if file.name not in self.file_names:
            return

        self.file_names.remove(file.name)
        c_file = next(filter(lambda x: x.name == file.name, self.files))
        c_file.close()
        self.files.remove(c_file)

    def enable_stdout(self) -> None:
        '''
        Enable writing to stdout. In certain verbosity levels, you only
        want ouput to go into the logfiles. For these cases, you can disable
        stdout, print the desired output and enable it afterwards again.

        Parameters:
            None

        Returns:
            None
        '''
        self.use_stdout = True

    def disable_stdout(self) -> None:
        '''
        Disable writing to stdout. In certain verbosity levels, you only
        want ouput to go into the logfiles. For these cases, you can disable
        stdout, print the desired output and enable it afterwards again.

        Parameters:
            None

        Returns:
            None
        '''
        self.use_stdout = False
