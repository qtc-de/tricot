### Default Validators

----

This document contains a list of validators that are available per default when using *tricot*.

- [ContainsValidator](#containsvalidator)
- [CountValidator](#countvalidator)
- [DirectoryExistsValidator](#directoryexistsvalidator)
- [ErrorValidator](#errorvalidator)
- [FileContainsValidator](#filecontainsvalidator)
- [FileExistsValidator](#fileexistsvalidator)
- [LineCountValidator](#linecountvalidator)
- [MatchValidator](#matchvalidator)
- [RegexValidator](#regexvalidator)
- [RuntimeValidator](#runtimevalidator)
- [StatusCodeValidator](#statuscodevalidator)
- [TarContainsValidator](#tarcontainsvalidator)
- [ZipContainsValidator](#zipcontainsvalidator)


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


### CountValidator

----

Takes several strings as argument and an expected count on how often the string should be
encountered within the command output. Theoretically, we could use the syntax ``match: count``
to specify that ``match`` should be appear ``count`` times, as the YAML spec is not that strict
when it comes to allowed characters within of keys. However, to prevent problems with the python
parser, two separate lists are used.

**Type Validation**:

```python
param_type = dict
inner_types = {
        'counts': {'required': True, 'type': list},
        'ignore_case': {'required': False, 'type': bool},
        'values': {'required': True, 'type': list}
}
```

**Example:**

```yaml
validators:
    - count:
        ignore_case: True
        values:
            - match one
            - match two
        counts:
            - 3
            - 4
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
          invert:
            - unexpected
        - file: /etc/hosts
          ignore_case: True
          contains:
            - localhost
            - 127.0.0.1
        - file: /tmp/tmp_file
          contains:
            - 'cleanup deletes the file after validation'
          cleanup: True
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


### LineCountValidator

----

Takes a number of expected lines and checks whether the command output has a matching number of lines.
Empty lines can be ignored by using the ``ignore_empty`` option. Empty lines on the start and end of
the command output are ignored by default. To prevent this behavior, you can use the ``keep_trailing``
and ``keep_leading`` options.

**Type Validation**:

```python
param_type = dict
inner_types = {
        'count': {'required': True, 'type': int},
        'ignore_empty': {'required': False, 'type': bool},
        'keep_trailing': {'required': False, 'type': bool},
        'keep_leading': {'required': False, 'type': bool},
}
```

**Example:**

```yaml
validators:
    - line_count:
        ignore_empty: True
        count: 5
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

The ``RegexValidator`` checks whether the command output matches the specified regex. Several
flags can be specified for matching, with corresponding meanings as in python's ``re`` module.
It is also possible to invert the match, which makes the validator fail if the specified regex
was found.

**Type Validation**:

```python
param_type = dict
inner_types = {
        'ascii': {'required': False, 'type': bool},
        'dotall': {'required': False, 'type': bool},
        'ignore_case': {'required': False, 'type': bool},
        'multiline': {'required': False, 'type': bool},
        'match': {'required': True, 'type': list, 'alternatives': ['invert']},
        'invert': {'required': True, 'type': list, 'alternatives': ['values']}
}
```

**Example:**

```yaml
validators:
    - regex:
        match:
            - ^match this$
            - ^and this.+
        invert:
            - but not this.*
            - ^or this.*
        multiline: true
        ignore_case: true
```


### RuntimeValidator

----

The ``RuntimeValidator`` checks whether the overall runtime of the command was lower or greater
than the user specified value. It also supports equal, but this should be useless :D

**Type Validation**:

```python
param_type = dict
inner_types = {
        'lt': {'required': True, 'type': int, 'alternatives': ['gt', 'eq']},
        'gt': {'required': True, 'type': int, 'alternatives': ['lt', 'eq']},
        'eq': {'required': True, 'type': int, 'alternatives': ['lt', 'gt']},
}
```

**Example:**

```yaml
validators:
    - runtime:
        lt: 10
        gt: 5
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


### TarContainsValidator

----

The `TarContainsValidator` checks whether a *tar* archive contains the specified items. It is also
possible to validate the item type and other attributes of an tar item.

**Type Validation**:

```python
param_type = dict
inner_types = {
        'archive': {'required': True, 'type': str},
        'files': {'required': True, 'type': list, 'alternatives': ['invert']},
        'invert': {'required': True, 'type': list, 'alternatives': ['files']},
        'compression': {'required': False, 'type': str},
}
```

**Example:**

Whereas the `invert` key is expected to be a list of plain strings, the `files` key can also
contain more validation options for a tar item:

```yaml
validators:
    - tar_contains:
      archive: "/tmp/test.tar"
      files:
        - filename: link
          type: LNKTYPE
          target: /etc/passwd
        - example1
        - filename: example2
          size: 5
```


### ZipContainsValidator

----

The `ZipContainsValidator` checks whether a *zip* archive contains the specified items. It is also
possible to validate the item type and other attributes of an zip item.

**Type Validation**:

```python
param_type = dict
inner_types = {
        'archive': {'required': True, 'type': str},
        'files': {'required': True, 'type': list, 'alternatives': ['invert']},
        'invert': {'required': True, 'type': list, 'alternatives': ['files']},
}
```

**Example:**

Whereas the `invert` key is expected to be a list of plain strings, the `files` key can also
contain more validation options for a zip item:

```yaml
validators:
  - zip_contains:
      archive: "/tmp/test.zip"
      files:
        - test1
        - filename: test2
          size: 20
          csize: 5
          type: FILE
          crc: 906850967
        - test3
```
