from __future__ import annotations

import os
import sys
import time
import shutil
import signal
import atexit
import socket
import functools
import threading
import subprocess
import http.server
from typing import Any
from pathlib import Path

import tricot.utils


this = sys.modules[__name__]
this.plugins = {}


def register_plugin(plugin_name: str, plugin_class: type) -> None:
    '''
    Registers a plugin class under the specified name. This function needs to
    be called to make plugins available within of .yml files. Some default
    plugin classes are registerd at the end of this file. Others can be manually
    added by users that use tricot as a library.

    Parameters:
        plugin_name         Name of the plugin to use in .yml files
        plugin_class        Reference to the corresponding plugin class

    Returns:
        None
    '''
    this.plugins[plugin_name] = plugin_class


def get_plugin(path: Path, plugin_name: str, param: Any, variables: dict[str:str]) -> Plugin:
    '''
    Searches for the specified plugin name within the registred plugins and
    uses the corresponding class to create an instance for the plugin. This instance
    is returned by the function. If the specified plugin name is not found, the
    function raises a PluginError.

    Parameters:
        path                Path object to the .yml file containing the plugin
        plugin_name         Name of the requested plugin
        param               Params to initialize the plugin with
        variables           Variables to initialize the plugin with
    '''
    plug_class = this.plugins.get(plugin_name)

    if plug_class is None:
        raise PluginError(path, f"Unable to find specified plugin '{plugin_name}'.")

    return plug_class(path, plugin_name, param, variables)


def get_plugin_list() -> list[str]:
    '''
    Returns a list of currently registered plugin names.

    Parameters:
        None

    Returns:
        plugin_list       List of registred plugins
    '''
    keys = this.plugins.keys()
    return list(keys)


class PluginException(Exception):
    '''
    PluginExceptions are raised by plugins when they throw any other kind of exception.
    They contain the original exception as parameter.
    '''
    def __init__(self, exception: Exception, name: str, path: Path) -> None:
        '''
        Custom exception class that stores the original exception within a variable.
        '''
        self.original = exception
        self.name = name
        self.path = path

        super().__init__('PluginException')


class PluginError(Exception):
    '''
    PluginErrors are raised when there are problems with initializing a plugin.
    '''
    def __init__(self, path: Path, message: str) -> None:
        '''
        Adds the additional path attribute (location of the corresponding configuration file)
        '''
        self.path = str(path.resolve())
        super().__init__(message)


class Plugin:
    '''
    The Plugin class is basically an abstract class with the only purpose of
    being extended by other classes. All possible plugins implemented in
    tricot are based on this superclass that contains some shared methods and
    some that need to be overwritten by the child classes.

    Within test.yaml files, Plugins can be defined in different ways:

        * example-plugin: This is a value
        * example-plugin2:
            param1: value1
            param2: value2
            ...
        * example-plugin3:
            - value1
            - value2
            ...

    Which form to choose depends on the corresponding Plugin requirements. When
    choosing the first version, the 'param' attribute of the Plugin just contains
    the value specified in the yaml file. When choosing the second or third form, the
    'param' attribute contains a dictionary or list with the specified parameters.

    Plugins can use the 'param_type' class variable to indicate which type of parameters
    they expect. For collection types like dict or list, it is also possible to specify
    the 'inner_types' attribute to specify requirements on the containing types.
    To understand this feature you probably want to look at the HttpListenerPlugin in
    this file, which uses the 'inner_types' variable.

    Custom Plugins should at least overwrite the 'run' method to perform their
    operation. Other methods can be overwritten or added on demand. The run
    should perform its operation without returning anything. PluginExceptions do not
    need to be raised manually. Invalid configuration within the .yml file should cause
    a PluginError, but it is recommended to only raise this error during initialization
    and not within the 'run' method.
    '''
    param_type = None
    inner_types = None

    def __init__(self, path: Path, name: str, param: Any, variables: dict[str, Any]) -> None:
        '''
        Initializes the Plugin.

        Parameters:
            path        Path object to the .yml file containing the plugin
            name        Name of the Plugin (as specified in the .yml file)
            param       Parameters of the Plugin (can be str, dict, int, bool, ...)
            variables   Variables contained in this dict are replaced in all str parameters
        '''
        self.path = path
        self.name = name
        self.param = param
        self.variables = variables
        self.stopped = True
        self.check_param_type()

    def check_param_type(self) -> None:
        '''
        Checks whether the specified parameter type matches the expected one. If this is not
        the case, a PluginError is raised. As parameter types may changed after variable
        substituation, this function also applies variables before checking.

        Parameters:
            None

        Returns:
            None
        '''
        self.param = tricot.utils.apply_variables(self.param, self.variables)

        if self.param_type is None:
            return

        if type(self.param) is not self.param_type:
            raise PluginError(self.path, f"Plugin '{self.name}' requires a parameter type of {str(self.param_type)}")

        self.check_inner_types()

    def check_inner_types(self) -> None:
        '''
        Plugins that require a dictionary or list can specify the static class variable 'inner_types'
        to specify which inner types are expecetd within the collection types. When a list is used,
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
                if value['required'] and not param:
                    message = f"Plugin '{self.name}' requires key with name '{key}' and type {value['type']}."
                    raise PluginError(self.path, message)

                if param is not None and type(param) is not value['type']:
                    message = f"Plugin '{self.name}' expects type {value['type']} for the '{key}' key."
                    raise PluginError(self.path, message)

        elif type(self.param) is list and type(self.inner_types) is list:

            for param in self.param:
                if type(param) not in self.inner_types:
                    message = f"Plugin '{self.name}' requires a parameter type of list[{str(self.inner_types)}."
                    raise PluginError(self.path, message)

    def from_list(path: Path, input_list: list[dict], variables: dict[str, Any] = {}) -> list[Plugin]:
        '''
        Constructs a new list of Plugins from a python list. The list content is usually
        the specified plugin configuration within a .yml file.

        Parameters:
            path        Path object to the .yml file containing the plugin
            input_list  Python list as read in from a .yml file
            variables   Global variables that should be inherited by the plugin

        Returns:
            Plugin   Newly constructed Plugin objects
        '''
        if input_list is None:
            return []

        if type(input_list) is dict:
            raise PluginError(path, "Plugins need to be specified as a list.")

        plugins = list()

        for item in input_list:
            for key, value in item.items():
                val = get_plugin(path, key, value, variables)
                plugins.append(val)

        return plugins

    def _run(self, hotplug_variables: dict[str, Any] = None) -> None:
        '''
        This method is called internally to perform the Plugin action. It is basically
        a wrapper to the user defined 'run' method that catches possible exceptions and repalces
        them with the PluginException class.

        Parameters:
            hotplug_variables   Variables to apply at runtime

        Returns:
            None
        '''
        self.stopped = False
        atexit.register(self._stop)
        self.param = tricot.utils.apply_variables(self.param, hotplug_variables)

        try:
            self.run()

        except Exception as e:
            raise PluginException(e, self.name, self.path)

    def run(self) -> None:
        '''
        Dummy run method. This one needs to be overwritten by the actual Plugin implementations.
        '''
        return None

    def _stop(self) -> None:
        '''
        This method is called internally to perform Plugin cleanup actions. It is run
        after all Tests and Testers from the .yml file where the Plugin was defined in
        have finished. It is basically a wrapper around the user defined 'stop' method
        that performs the actual Plugin cleanup.

        Whether or not a plugin requires a cleanup depends on the plugins functionality.
        Therefore, this method does not need to be implemented.

        Parameters:
            None

        Returns:
            None
        '''
        if self.stopped:
            return

        try:
            self.stop()
            self.stopped = True

        except Exception as e:
            atexit.unregister(self._stop)
            raise PluginException(e, self.name, self.path)

    def stop(self) -> None:
        '''
        Dummy stop method. If a Plugin requires cleanup, this method should be overwritten.
        '''
        return None

    def resolve_path(self, path: str) -> str:
        '''
        Resolves the specified path relative to the current plugin definition (file location of
        the plugins .yml file). If the input path is already absolute, it is just returned.

        Parameters:
            path        File system path to resolve

        Returns:
            resolved    Resolved file system path
        '''
        if os.path.isabs(path):
            return Path(path)

        return self.path.parent.joinpath(path)


class OsCommandPlugin(Plugin):
    '''
    The OsCommandPlugin simply executes the specified operating system command.
    Commands are executed from the directory where the plugin was configured in.

    Example:

        plugins:
            - os_command:
                init: 1
                cmd:
                    - nc
                    - -vlp
                    - 4444
    '''
    param_type = dict
    inner_types = {
                    'shell': {'required': False, 'type': bool},
                    'ignore_error': {'required': False, 'type': bool},
                    'init': {'required': False, 'type': int},
                    'background': {'required': False, 'type': bool},
                    'timeout': {'required': False, 'type': int},
                    'cmd': {'required': True, 'type': list}
                  }

    def on_exit(self, command) -> None:
        '''
        Just a helper function that is called when a process exited.
        '''
        ignore_error = self.param.get('ignore_error', False)
        poll = self.process.poll()

        if poll and poll != 0 and not ignore_error:

            if type(command) is list:
                command = ' '.join(command)

            stdout, stderr = self.process.communicate()

            raise OSError(f"Command '{command}' exited with a non zero status code." +
                          f"\n\nstdout: {stdout}\n\nstderr: {stderr}")

    def run(self) -> None:
        '''
        Run the specified operating system command.
        '''
        init = self.param.get('init', 0)

        command = self.param['cmd']
        shell = self.param.get('shell', False)
        timeout = self.param.get('timeout', 0)
        background = self.param.get('background', False)

        for ctr in range(len(command)):
            command[ctr] = str(command[ctr])

        if shell:
            command = ' '.join(command)

        self.process = subprocess.Popen(command, cwd=self.path.parent, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, shell=shell, preexec_fn=os.setsid)

        if timeout > 0:
            self.process.communicate(timeout=timeout)

        elif not background:
            self.process.wait()

        if init > 0:
            time.sleep(init)

        self.on_exit(command)

    def stop(self) -> None:
        '''
        Stop the process if still existing.
        '''
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

        except ProcessLookupError:
            pass

        except AttributeError:
            pass


class MkdirPlugin(Plugin):
    '''
    The MkdirPlugin simply creates the specified directories.
    Relative paths are interpreted to the directory the plugin was configured in.

    Example:

        plugins:
            - mkdir:
                cleanup: true
                force: false
                dirs:
                    - /tmp/test
                    - /tmp/test2
    '''
    param_type = dict
    inner_types = {
                    'cleanup': {'required': False, 'type': bool},
                    'force': {'required': False, 'type': bool},
                    'dirs': {'required': True, 'type': list}
                  }

    blacklist = ['/', '/home', '/opt', '/var']
    directories = list()

    def run(self) -> None:
        '''
        Create the specified directories if not already existing.
        '''
        for directory in self.param['dirs']:

            directory = self.resolve_path(directory)
            os.makedirs(directory, exist_ok=True)

            if directory not in MkdirPlugin.directories:
                MkdirPlugin.directories.append(directory)

                if self.directories is None:
                    self.directories = []

                self.directories.append(directory)

    def stop(self) -> None:
        '''
        Remove all directories created by the plugin (only if cleanup is set to true).
        '''
        if not self.param.get('cleanup', False) or not hasattr(self, 'directories'):
            return

        for directory in self.directories:
            if directory not in MkdirPlugin.blacklist:

                try:
                    os.rmdir(directory)

                except OSError as e:

                    if 'not empty' in str(e) and self.param.get('force', False):
                        shutil.rmtree(directory)

                MkdirPlugin.directories.remove(directory)
                self.directories.remove(directory)


class HttpListenerPlugin(Plugin):
    '''
    The HttpListenerPlugin starts a HTTP server in the background and servers files
    from the specified directory and port.

    Example:

        plugins:
            - http_listener:
                port: 8000
                dir: ./www
    '''
    param_type = dict
    inner_types = {
                    'port': {'required': True, 'type': int},
                    'dir': {'required': True, 'type': str}
                  }
    instances = []

    def __init__(self, *args, **kwargs) -> None:
        '''
        Make sure that the specified port is valid before running the server.
        '''
        super().__init__(*args, **kwargs)

        if self.param['port'] <= 0 or self.param['port'] > 65535:
            raise PluginError(self.path, f"Specified port '{self.param['port']}' is invalid. Needs to be between 0-65535.")

    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        '''
        Custom HTTPRequestHandler that uses the base functioanlity of SimpleHTTPRequestHandler
        and only overwrites its log_message method to prevent any otuputs.
        '''

        def log_message(self, format, *args):
            '''
            Overwrite log_message to prevent log messages from being printed.
            '''
            return

    def run(self) -> None:
        '''
        Checks whether a server on this port is already running and starts it otherwise.
        '''
        port = self.param['port']
        directory = self.param['dir']

        if port in HttpListenerPlugin.instances:
            return

        directory = self.resolve_path(directory)
        if not directory.is_dir():
            raise FileNotFoundError(f"Specified directory '{directory.absolute()}' does not exist.")

        self.thread = threading.Thread(name=f'http-{port}', target=self.start_server, args=(port, directory))
        self.thread.setDaemon(True)
        self.thread.start()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while sock.connect_ex(('127.0.0.1', port)) != 0:
            time.sleep(0.1)
        sock.close()

        HttpListenerPlugin.instances.append(port)

    def start_server(self, port: int, directory: str) -> None:
        '''
        Starts the HTTPListener. Should be run in a separate thread.
        '''
        handler = functools.partial(HttpListenerPlugin.CustomHandler, directory=directory)
        self.server = http.server.HTTPServer(('', port), handler)
        self.server.serve_forever()

    def stop(self) -> None:
        '''
        Stops the HTTPListener and the corresponding thread.
        '''
        if hasattr(self, 'server') and self.server:
            self.server.server_close()
            self.server.shutdown()

        if hasattr(self, 'thread') and self.thread:
            self.thread.join()

        if self.param['port'] in HttpListenerPlugin.instances:
            HttpListenerPlugin.instances.remove(self.param['port'])


class CleanupPlugin(Plugin):
    '''
    The CleanupPlugin is used to remove files and directories that have been created during
    tests. Relative paths are resolved to the directory the plugin is defined in.

    Example:

        plugins:
            - cleanup:
                force: false
                items:
                    - /tmp/test
                    - /tmp/test2
    '''
    param_type = dict
    inner_types = {
                    'force': {'required': False, 'type': bool},
                    'items': {'required': True, 'type': list}
                  }

    blacklist = ['/', '/home', '/opt', '/var']

    def stop(self) -> None:
        '''
        Remove all items specified in the plugin definition.
        '''
        for item in self.param.get('items', []):

            item = self.resolve_path(item)
            try:

                if item in CleanupPlugin.blacklist:
                    continue

                elif os.path.isdir(item):

                    try:
                        os.rmdir(item)

                    except OSError as e:
                        if 'not empty' in str(e) and self.param.get('force', False):
                            shutil.rmtree(item)

                else:
                    os.remove(item)

            except FileNotFoundError:
                continue


class CleanupCommandPlugin(Plugin):
    '''
    Basically a copy of the OsCommandPlugin, but runs on the end of the corresponding tester.

    Example:

        plugins:
            - cleanup_command:
                ignore_error: True
                cmd:
                    - rm
                    - -r
                    - /tmp/testdir
    '''
    param_type = dict
    inner_types = {
                    'shell': {'required': False, 'type': bool},
                    'ignore_error': {'required': False, 'type': bool},
                    'timeout': {'required': False, 'type': int},
                    'cmd': {'required': True, 'type': list}
                  }

    def on_exit(self, command) -> None:
        '''
        Just a helper function that is called when a process exited.
        '''
        ignore_error = self.param.get('ignore_error', False)
        poll = self.process.poll()

        if poll and poll != 0 and not ignore_error:

            if type(command) is list:
                command = ' '.join(command)

            stdout, stderr = self.process.communicate()

            raise OSError(f"Command '{command}' exited with a non zero status code." +
                          f"\n\nstdout: {stdout}\n\nstderr: {stderr}")

    def stop(self) -> None:
        '''
        Run the specified command on stop.
        '''
        command = self.param['cmd']
        shell = self.param.get('shell', False)
        timeout = self.param.get('timeout', 0)

        for ctr in range(len(command)):
            command[ctr] = str(command[ctr])

        if shell:
            command = ' '.join(command)

        self.process = subprocess.Popen(command, cwd=self.path.parent, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, shell=shell)

        if timeout > 0:
            self.process.communicate(timeout=timeout)

        else:
            self.process.wait()

        self.on_exit(command)


class CopyPlugin(Plugin):
    '''
    The CopyPlugin can be used to copy files before a test runs. It also offers a cleanup
    action to remove copied files after the test.

    Example:

        plugins:
            - copy:
                cleanup: True
                recursive: False
                from:
                    - /tmp/from-here
                to:
                    - /opt/to-there
    '''
    param_type = dict
    inner_types = {
                    'cleanup': {'required': False, 'type': bool},
                    'from': {'required': True, 'type': list},
                    'to': {'required': True, 'type': list}
                  }

    blacklist = ['/', '/home', '/opt', '/var']

    def run(self) -> None:
        '''
        Copy the specified files into the target location.
        '''
        self.cleanup = []

        dest = self.param.get('to', [])
        files = self.param.get('from', [])

        if len(dest) != len(files):
            raise ValueError("The 'from' and 'to' parameters need to be equally sized lists.")

        for ctr in range(len(files)):

            src_path = self.resolve_path(files[ctr])
            dest_path = self.resolve_path(dest[ctr])

            if src_path.is_file():
                created = shutil.copy(src_path, dest_path)
                self.cleanup.append(Path(created))

            elif src_path.is_dir():

                if dest_path.is_dir():
                    dest_path = dest_path.joinpath(src_path.name)

                created = shutil.copytree(src_path, dest_path)
                self.cleanup.append(Path(created))

    def stop(self) -> None:
        '''
        Removed copied files if desired.
        '''
        if not self.param.get('cleanup', False):
            return

        for item in self.cleanup:

            if not item.exists():
                continue

            elif item.absolute() in CopyPlugin.blacklist:
                raise ValueError("Plugin attempted to remove the blacklisted ressource '{item}'.")

            elif item.is_file():
                item.unlink()

            elif item.is_dir():
                shutil.rmtree(str(item.absolute()))


class TempFile(Plugin):
    '''
    The TempFile plugin creates a temorary file and optionally fills it with user specified content.
    The temporary file is deleted after the pluin has stopped.

    Example:

        plugins:
            - tempfile:
                path: /tmp/tricot_tempfile
                content: |-
                    This is some content for the tempfile
    '''
    param_type = dict
    inner_types = {
                    'path': {'required': True, 'type': str},
                    'content': {'required': False, 'type': str},
                    'mode': {'required': False, 'type': str}
                  }

    def __init__(self, *args, **kwargs) -> None:
        '''
        Make sure that the specified mode is valid before running the plugin.
        '''
        super().__init__(*args, **kwargs)

        self.path = self.param['path']
        self.mode = self.param.get('mode', 'w')
        self.content = self.param.get('content', '')

        if self.mode not in ['w', 'a']:
            raise PluginError(self.path, f"The select mode '{self.mode}' is invalid! Choices: 'w', 'a'")

    def run(self) -> None:
        '''
        Create the temporary file and optionally fill it with content.
        '''
        with open(self.path, self.mode) as temp_file:
            temp_file.write(self.content)

    def stop(self) -> None:
        '''
        Remove the temporary file.
        '''
        item = Path(self.path)

        if item.is_file():
            item.unlink()


register_plugin("os_command", OsCommandPlugin)
register_plugin("mkdir", MkdirPlugin)
register_plugin("http_listener", HttpListenerPlugin)
register_plugin("cleanup", CleanupPlugin)
register_plugin("cleanup_command", CleanupCommandPlugin)
register_plugin("copy", CopyPlugin)
register_plugin("tempfile", TempFile)
