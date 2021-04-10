### Default Plugins

----

This document contains a list of plugins that are available per default when using *tricot*.

- [CleanupPlugin](#cleanupplugin)
- [HttpListenerPlugin](#httplistenerplugin)
- [MkdirPlugin](#mkdirplugin)
- [OsCommandPlugin](#oscommandplugin)


### CleanupPlugin

----

The ``CleanupPlugin`` can be used to remove files and directories that have been created during
tests. Relative paths are resolved to the directory the plugin is defined in. Non empty
directories are only cleaned up when the ``force`` key was set to ``True``.


**Type Validation**:

```python
param_type = dict
inner_types = {
                'force': {'required': False, 'type': bool},
                'items': {'required': True, 'type': list}
              }
```

**Example:**

```yaml
plugins:
    - cleanup:
        force: false
        items:
            - /tmp/test
            - /tmp/test2
```


### HttpListenerPlugin

----

The ``HttpListenerPlugin`` starts a HTTP server in the background and servers files
from the user specified directory. Relative paths are resolved to the directory
where the plugin is defined in.


**Type Validation**:

```python
param_type = dict
inner_types = {
                'port': {'required': True, 'type': int},
                'dir': {'required': True, 'type': str}
              }
```

**Example:**

```yaml
plugins:
    - http_listener:
        port: 8000
        dir: ./www
```


### MkdirPlugin

----

The ``MkdirPlugin`` simply creates the user specified directories.
Relative paths are interpreted to the directory the plugin was configured in.
Created directories can be cleaned up after the test by using the ``cleanup``
key. By default, this only removes empty directories. If you want to remove
directories with content, you have to set the ``force`` key to ``True``.


**Type Validation**:

```python
param_type = dict
inner_types = {
                'cleanup': {'required': False, 'type': bool},
                'force': {'required': False, 'type': bool},
                'dirs': {'required': True, 'type': list}
              }
```

**Example:**

```yaml
plugins:
    - mkdir:
        cleanup: true
        force: false
        dirs:
            - /tmp/test
            - /tmp/test2
```


### OsCommandPlugin

----

The ``OsCommandPlugin`` simply executes the specified operating system command.
Commands are executed from the directory where the plugin was configured in.
The plugin allows some additional configuration by using different plugin keys:

* ``background``: Execute the command in the background.
* ``ignore_error``: decides whether a failed command execution leads to a plugin
  error. Default is ``False``.
* ``init``: Sleep the specified amount of seconds before going on with the test.
  Command is executed in the background.
  This gives the command some initialization time.
* ``timeout``: Timeout the command after the specified amount of seconds. A timed
  out plugin will cause an error. Use ``init`` if you need a timeout without error.


**Type Validation**:

```python
param_type = dict
inner_types = {
                'ignore_error': {'required': False, 'type': bool},
                'init': {'required': False, 'type': int},
                'background': {'required': False, 'type': bool},
                'timeout': {'required': False, 'type': int},
                'cmd': {'required': True, 'type': list}
              }
```

**Example:**

```yaml
plugins:
    - os_command:
        init: 1
        cmd:
            - nc
            - -vlp
            - 4444
```
