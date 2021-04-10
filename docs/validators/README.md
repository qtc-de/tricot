### Default Validators

----

This document contains a list of validators that are available per default when using *tricot*.

- [ContainsValidator](#containsvalidator)
- [DirectoryExistsValidator](#directoryexistsvalidator)
- [ErrorValidator](#errorvalidator)
- [FileContainsValidator](#filecontainsvalidator)
- [FileExistsValidator](#fileexistsvalidator)
- [MatchValidator](#matchvalidator)
- [RegexValidator](#regexvalidator)
- [StatusCodeValidator](#statuscodevalidator)


### ContainsValidator

----

The ``ContainsValidator`` checks whether the command output contains the user specified string values.
The corresponding values are expected to be stored as list within the ``values`` key of the Validator.
Additionally, the Validator accepts the ``ignore_case`` key, to specify whether the case should be ignored
and the ``invert`` key to specify words, that should not be contained within the output.

**Type Validation**:

```python
param_type = dict
inner_types = {
        'ignore_case': {'required': False, 'type': bool},
        'values': {'required': True, 'type': list, 'alternatives': ['invert']},
        'invert': {'required': True, 'type': list, 'alternatives': ['values']}
}
```

**Example:**

```yaml
validators:
    - contains:
        ignore_case: True
        values:
            - match this
            - and this
        invert:
            - not match this
            - and this
```


### DirectoryExistsValidator

----

The ``DirectoryExistsValidator`` takes a list of directory names and checks whether they exist
on the file system. This can be useful, when your testing command is expected to create
directories. It also supports a ``cleanup`` option that can be used to remove files created
during a test. Non empty directories are only cleaned up when the ``force`` key was specified
with a value of ``True``. The ``invert`` key can be used to verify that certain files do not exist.

**Type Validation**:

```python
param_type = dict
inner_types = {
        'cleanup': {'required': False, 'type': bool},
        'force': {'required': False, 'type': bool},
        'dirs': {'required': True, 'type': list, 'alternatives': ['invert']},
        'invert': {'required': True, 'type': list, 'alternatives': ['dirs']}
}
```

**Example:**

```yaml
validators:
    - dir_exists:
        cleanup: True
        force: False
        dirs:
            - /tmp/test1
            - /tmp/test2
            ...
```


### ErrorValidator

----

The ``ErrorValidator`` just checks the status code of the command for an error (``status_code != 0``). If the
Validator was used with ``False`` as argument, it checks the other way around.

**Type Validation**:

```python
param_type = bool
```

**Example:**

```yaml
validators:
    - error: False
```


### FileContainsValidator

----

The ``FileContainsValidator`` takes a list of filenames and strings that represent their
expected content. It when validates whether the files contain the corresponding content.

**Type Validation**:

```python
param_type = list
inner_types = [dict]
```

**Example:**

```yaml
validators:
    - file_contains:
        - file: /etc/passwd
          contains:
            - root
            - bin
        - file: /etc/hosts
          contains:
            - localhost
            - 127.0.0.1
```


### FileExistsValidator

----

The ``FileExistsValidator`` takes a list of filenames and checks whether they exist on the file
system. This can be useful, when your testing command is expected to create files. It also supports
a ``cleanup`` option that can be used to remove files created during a test. The ``invert`` key can
be used to verify that certain files do not exist.

**Type Validation**:

```python
param_type = dict
inner_types = {
        'cleanup': {'required': False, 'type': bool},
        'files': {'required': True, 'type': list, 'alternatives': ['invert']},
        'invert': {'required': True, 'type': list, 'alternatives': ['files']}
}
```

**Example:**

```yaml
validators:
    - file_exists:
        cleanup: True
        files:
            - /tmp/test1
            - /tmp/test2
```



### MatchValidator

----

The ``MatchValidator`` checks whether there is an exact match of the command output and the user
specified value. The value is expected within the ``value`` key. Additionally, the validator
accepts the ``ignore_case`` key, to specify whether case should be ignored.

**Type Validation**:

```python
param_type = dict
inner_types = {
        'ignore_case': {'required': False, 'type': bool},
        'value': {'required': True, 'type': str}
}
```

**Example:**

```yaml
validators:
    - match:
        ignore_case: True
        value: Match this!
```


### RegexValidator

----

The ``RegexValidator`` checks whether the command output matches the specified regex.

**Type Validation**:

```python
param_type = str
```

**Example:**

```yaml
validators:
    - regex: .+(match this| or this).+
```


### StatusCodeValidator

----

The ``StatusCodeValidator`` checks whether the exit code of the command matches the user specified value.

**Type Validation**:

```python
param_type = int
```

**Example:**

```yaml
validators:
    - status: 0
```
