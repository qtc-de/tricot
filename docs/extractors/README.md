### Default Extractors

----

This document contains a list of extractors that are available per default when using *tricot*.

- [RegexExtractor](#regexextractor)


### RegexExtractor

----

The ``RegexExtractor`` can be used to extract command output into variables by using an regular
expression. Users can specify a pattern which they want to be extracted and a variable name to
extract the pattern matches to. The ``RegexExtractor`` supports multiple matches and match groups.

Consider you specified the variable name to be ``example`` and a pattern that contains two match groups
and is expected to match multiple times. The following variables could be used to obtain the extracted
values:

* ``${extract}`` - Contains the first whole match (like ``match.group(0)`` in python on the *first* match)
* ``${extract-0}`` - Same as ``${extract}``
* ``${extract-1}`` - Contains the second whole match (like ``match.group(0)`` in python on the *second* match)
* ``${extract-0-1}`` - Contains the *first* matchgroup of the *first* match (like ``match.group(1)`` on the *first* match)
* ``${extract-1-0}`` - Same as ``${extract-1}``
* ``...``

**Type Validation**:

```python
param_type = dict
inner_types = {
        'ascii': {'required': False, 'type': bool},
        'default': {'required': False, 'type': dict},
        'dotall': {'required': False, 'type': bool},
        'ignore_case': {'required': False, 'type': bool},
        'multiline': {'required': False, 'type': bool},
        'pattern': {'required': True, 'type': str},
        'variable': {'required': True, 'type': str},
}
```

**Example:**

```yaml
    command:
      - cat
      - /etc/passwd
    extractors:
      - regex:
          pattern: '1000:1000:[^:]+:([^:]+):(.+)$'
          variable: 'home-shell'
          on_miss: 'break'
          multiline: true
    validators:
      - contains:
          values:
            - 1000:1000
```
