import json
from termcolor import cprint

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
    indent = 0
    verbosity = 1

    def print(string: str, *args, e: bool = False, end: str = None) -> None:
        '''
        Print with prefix and indentation.
        '''
        print(Logger.get_prefix(e), string, *args, end=end)

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
        in yellow and the rest of the args in normal text color again..
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
        in red and the rest of the args in normal text color again..
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
        in blue and the rest of the args in normal text color again..
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
        in blue and the rest of the args in normal text color again..
        '''
        print(str1, end=' ')

        if(args):
            cprint(str2, color='blue', end=' ')
            print(*args, end=end)

        else:
            cprint(str2, color='blue', end=end)

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
        lines = string.split('\n')
        for line in lines:
            Logger.print(line, e=e)

    def print_with_indent_blue(string: str, e: bool = False) -> None:
        '''
        Takes a string, spilts it on newlines and prints each single line
        with the current prefix and indent in blue.
        '''
        lines = string.split('\n')
        for line in lines:
            Logger.print_blue(line, e=e)

    def handle_error(e: Exception, val: Validator, command: list) -> None:
        '''
        This function is called when a Validator failed to handle the error
        logging. It is basically a wrapper around '_handle_error', which
        performs the real error handling.
        '''
        Logger.increase_indent()
        Logger._handle_error(e, val, command)
        Logger.decrease_indent()

        if Logger.verbosity != 0:
            Logger.print('', e=True)

    def _handle_error(e: Exception, val: Validator, command: list) -> None:
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
            Logger.print_mixed_yellow('- Caught', 'ValidationException', 'raised by the', end=' ', e=True)
            cprint(val.name, color='red', end='')
            print(' validator.')
            Logger.print('  Validator run failed because of the following reason:', e=True)
            Logger.print_with_indent_blue('  ' + str(e), e=True)

        else:
            Logger.print_mixed_yellow('- Caught unexpected', type(e).__name__, 'during validation process.', e=True)
            Logger.print_mixed_red('  The', val.name, 'validator raises probably an uncaught exception.', e=True)
            Logger.print_mixed_blue('  Message:', str(e), e=True)

        if Logger.verbosity > 1:
            Logger.print('', e=True)
            Logger.print_yellow('  Command:', e=True, end=' ')
            print(command)
            Logger.print_yellow('  Status code:', e=True, end=' ')
            cprint(val.command_output[0], color='blue')

            Logger.print_yellow('  Command output:', e=True)
            Logger.increase_indent()
            Logger.print_with_indent(val.command_output[1], e=True)
            Logger.decrease_indent()

            Logger.print_yellow('  Validator parameters:', e=True)
            Logger.increase_indent()
            Logger.print_with_indent(json.dumps(val.param, indent=4).replace(r'\n', '\n').replace(r'\t', '\t'), e=True)
            Logger.decrease_indent()
