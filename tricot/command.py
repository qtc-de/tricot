from __future__ import annotations

import os
import signal
import timeit
import subprocess
from typing import Any
from pathlib import Path

import tricot


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


class Command:
    '''
    The command class represents a test command and is responsible for running
    the command and storing the corresponding outputs along with some meta
    information.
    '''
    def __init__(self, command: list, shell: bool = False) -> None:
        '''
        Crates a new Command object.

        Parameters:
            command     Command that is executed during a test.

        Returns:
            None
        '''
        self.path = None
        self.stdout = None
        self.stderr = None
        self.status = None
        self.runtime = None

        self.stdout_raw = None
        self.stderr_raw = None

        self.shell = shell
        self.command = command

    def run(self, path: Path, timeout: int, hotplug_variables: dict[str, Any] = None, env: dict = {}):
        '''
        Just a wrapper around the actual command execution function. It is basically used
        to reduce the complexity of the run function and to handle the special case of
        the ${prev} variable within the command specification. It returns nothing, as
        outputs and meta information is stored within class variables.

        Parameters:
            path                File system path where the command is run in
            timeout             Timeout to use during command execution
            hotplug_variables   Variables that are applied at runtime.
            env                 Environment variables

        Returns:
            None
        '''
        if self.command[0] != '${prev}':
            self.command = tricot.Test.apply_variables(self.command, hotplug_variables)

            try:
                self.path = path
                timer = timeit.Timer(lambda: self._run(path, timeout, env))
                self.runtime = timer.timeit(number=1)

            except Exception as e:
                tricot.Logger.print_plain_red("error.")
                raise TricotRuntimeError(e)

            except KeyboardInterrupt as e:
                tricot.Logger.print_plain_red("canceled.")
                raise KeyboardInterrupt(e)

        else:
            prev = hotplug_variables.get('$prev')

            if prev is not None and prev.validate_run():
                self.copy(prev)

            else:
                tricot.Logger.print_plain_red("error.")
                raise tricot.TricotException("Special '${prev}' variable was used, but no previous output exists.")

    def _run(self, path: Path, timeout: int, env: dict = {}) -> None:
        '''
        Performs the actual command execution via subprocess.Popen. All relevant outputs and
        status codes are saved within of object attributes.

        Parameters:
            path                File system path where the command is run in
            timeout             Timeout to use during command execution
            env                 Environment variables

        Returns:
            cmd_output      Command output in the form [status_code, stdout & stderr]
        '''
        envi = tricot.utils.merge_default_environment(env)

        if self.shell:
            self.command = ' '.join(self.command)

        try:
            process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       cwd=path, env=envi, shell=self.shell, preexec_fn=os.setsid)

            self.stdout_raw, self.stderr_raw = process.communicate(timeout=timeout)
            self.status = process.returncode

        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            self.stdout_raw, self.stderr_raw = process.communicate()
            self.status = 99

        except subprocess.CalledProcessError as e:
            self.stdout_raw = e.output
            self.stderr_raw = e.stderr
            self.status = e.returncode

        self.stdout = self.stdout_raw.decode('utf-8')
        self.stderr = self.stderr_raw.decode('utf-8')

    def copy(self, other: Command) -> None:
        '''
        Copies all attribute values from the specified Command into the current object.

        Parameters:
            other       Command object to copy the values from

        Returns:
            None
        '''
        attrs = list(filter(lambda x: not x.startswith('__'), self.__dict__))
        for attr in attrs:
            setattr(self, attr, getattr(other, attr))

    def validate_run(self) -> bool:
        '''
        Validates that the command object was run. This is done by checking attributes that
        are set during command execution like self.stdout, self.stderr or self.status.

        Parameters:
            None

        Returns:
            boolean     True if command was run and contains all required attributes.
        '''
        attrs = list(filter(lambda x: not x.startswith('__'), self.__dict__))
        for attr in attrs:

            value = getattr(self, attr)
            if value is None:
                return False

        return True

    def get_output(self) -> str:
        '''
        Returns the merged stdout and stderr outputs. Outputs are separated with a single
        newline.

        Parameters:
            None

        Returns:
            output      Returns merged stdout and stderr output
        '''
        output = ''

        if self.stdout:
            output += self.stdout

        if self.stderr:
            output += '\n'
            output += self.stderr

        return output

    def get_raw_output(self) -> bytes:
        '''
        Returns the merged stdout_raw and stderr_raw outputs.

        Parameters:
            None

        Returns:
            output      Returns merged stdout_raw and stderr_raw output
        '''
        output = b''

        if self.stdout:
            output += self.stdout

        if self.stderr:
            output += self.stderr

        return output
