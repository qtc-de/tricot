from __future__ import annotations

import sys
import json
from termcolor import cprint

from tricot.command import Command
from tricot.validation import Validator, ValidationException, ValidatorError


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

    def set_logfile(path: str) -> None:
        '''
        Mirrors all output of tricot to the specified logfile.

        Parameters:
            path        File system path of the logfile

        Returns:
            None
        '''
        Logger.tee = Tee(path)

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
            return

        if type(e) is ValidatorError:
            Logger.print_mixed_red('- Caught', 'ValidatorError', 'during validator instantiation.', e=True)
            Logger.print('  Validator instantiation failed because of the following reason:', e=True)
            Logger.print_blue('  ' + str(e), e=True)
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

        if Logger.verbosity > 1:
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

            Logger.print_yellow('  Validator parameters:', e=True)
            Logger.increase_indent()
            Logger.print_with_indent(json.dumps(val.param, indent=4).replace(r'\n', '\n').replace(r'\t', '\t'), e=True)
            Logger.decrease_indent()

    def handle_success(cmd: Command, val: list[Validator]) -> None:
        '''
        This function is called when all Validators have been passed.
        It is basically a wrapper around '_handle_success'.
        '''
        if Logger.verbosity != 3:
            return

        Logger.increase_indent()
        Logger._handle_success(cmd, val)
        Logger.decrease_indent()
        Logger.print('')

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
    def __init__(self, name):
        self.file = open(name, 'w')
        self.stdout = sys.stdout
        sys.stdout = self

    def __del__(self):
        sys.stdout = self.stdout
        self.file.close()

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()
