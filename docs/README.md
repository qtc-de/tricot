### tricot Documentation

----

This folder contains some supplementary documentation that would be to long for the
main [README.md](/README.md) of this project. Don't expect it to be complete or helpful
on it's own.


### Validator and Plugin List

----

Currently, the best way to get reliable information on available plugins and validators
is to read the corresponding parts of *tricot's* source code ([plugin](/tricot/plugin.py),
[validation](/tricot/validation.py)). However, the following locations provide a rough
overview that may be extended in future:

* [plugins](./plugins)
* [validators](./validators)

The following sections demonstrate how custom *tricot* plugins and validators can be created.
In case you require more detailed information on how to achieve certain things, please refer
to the source code of *tricot* and read the corresponding class definitions for the ``Validator``
and ``Plugin`` class.


### Writing Custom Plugins

----

*tricot* can be easily extended with custom plugins that execute user controlled actions
during startup and shutdown of a test. The recommended way to create a new plugin is by
running the following command:

```console
$ tricot --template plugin my_plugin.py
[+] Writing template file my_plugin.py
```

The template file that is written by this command contains the basic python code required
to create a new plugin. With a few modifications, you can easily arrive at the ``HelloWorldPlugin``
that is listed below:

```python
import tricot

class HelloWorldPlugin(tricot.Plugin):
    '''
    Prints "Hello World" during startup and "Ciao World" during shutdown.
    Also expects a user specified string that is appended.

    Example:

        plugins:
            - hello_world: :)
    '''
    param_type = str

    def run(self) -> None:
        '''
        Executed on startup.
        '''
        tricot.Logger.print(f"Hello World {self.param}")

    def stop(self) -> None:
        '''
        Executed when stopping.
        '''
        tricot.Logger.print(f"Ciao World {self.param}")


tricot.register_plugin('hello_world', HelloWorldPlugin)
```

To see the plugin in action, we can use the following sample test definition:

```yaml
tester:
  name: ExampleTester
  title: Just an example test

plugins:
  - hello_world: :)

tests:

  - title: Test passwd File
    description: |-
      Test that the passwd file can be read.

    command:
      - cat
      - /etc/passwd
    validators:
      - status: 0
```

When running this test while including our custom plugin definition, we get the following output:

```console
[qtc@kali ~]$ tricot example.yml --plugin my_plugin.py 
[+] Starting test: Just an example test
[+]     Hello World :)
[+]     
[+]         1. Test passwd File... success.
[+]     Ciao World :)
```


### Writing Custom Validators

----

Custom validators can be created in the same way as custom plugins. To create a new validator,
you should start of with the following command:

```console
$ tricot --template validator my_validator.py
```

The template file that is written by this command contains the basic python code required
to create a new validator. With a few modifications, you can easily arrive at the ``HelloWorldValidator``
that is listed below:

```python
import tricot

class HelloWorldValidator(tricot.Validator):
    '''
    Verifies that the command output contains the string "Hello World".

    Example:

        validators:
            - hello_world:
    '''
    def run(self) -> None:
        '''
        Run during validation.
        '''
        if "Hello World" not in self.get_output():
            raise tricot.ValidationException("String 'Hello World' was not found in command output.")


tricot.register_validator('hello_world', HelloWorldValidator)
```

An example for a successful validation can be found in the following test definition:

```yaml
tester:
  name: ExampleTester
  title: Just an example test

tests:

  - title: Test passwd File
    description: |-
      Test that the passwd file can be read.

    command:
      - echo
      - Hello World :)
    validators:
      - hello_world:
```

Running this test creates the following output:

```console
[qtc@kali ~]$ tricot example.yml --validator my_validator.py 
[+] Starting test: Just an example test
[+]     
[+]         1. Test passwd File... success.
```

On the other hand, when changing the command in the above test definition to return ``Ciao World :)`` instead,
the validator will raise a ``ValidationException``:

```console
[qtc@kali ~]$ tricot  -v example.yml --validator my_validator.py 
[+] Starting test: Just an example test
[+]     
[+]         1. Test passwd File... failed.
[-]             - Caught ValidationException raised by the hello_world validator.
[-]               Validator run failed because of the following reason:
[-]               String 'Hello World' was not found in command output.
[-]             
[-]               Command: ['echo', 'Ciao World :)']
[-]               Status code: 0
[-]               Command stdout:
[-]                 Ciao World :)
[-]                 
[-]               Command stderr:  
[-]               Validator parameters:
[-]                 null
[-]  
```


### Accessing Command Information from an Validator

----

Validators get access to the command output and some meta information using their ``self.command`` attribute.
This attribute contains the [Command object](/tricot/command.py) that is associated with the current validation.
The command object contains the default outputs (``stdout`` and ``stderr``) as well as some meta information
like the status code or the overall runtime.

Each dicitionary based validator (see next section for more details) should add support for the implicit ``stream``
key. ``stream`` is expected to be one of ``stdout``, ``stderr`` or ``both`` and is parsed an validated automatically
by tricot. Dictionary based validators should use the ``self.get_output()`` function to obtain command output, as this
function returns the command output associated with the user specified stream.

### Parameter Types and their Validation

----

Plugins and validators may use the ``param_type`` and ``inner_types`` class variables to define more detailed
information on their required parameters types. Both variables are used when parsing the test configuration
and perform some basic type validations. To describe this in more detail, we use the following test configuration:

```yaml
tester:
  name: ExampleTester
  title: Just an example test

plugins:
  example_one: Hello World :)
  example_two:
    - arg1
    - 22
  example_three:
    key1: arg1
    key2: 22
```

* ``param_type`` can be used to specify the python type that is expected for the toplevel argument of a
  plugin or validator. In the example test configuration above, the ``param_type`` values should be set
  like this:
  * ``example_one``: ``param_type = str``
  * ``example_two``: ``param_type = list``
  * ``example_three``: ``param_type = dict``

* ``inner_types`` can be used to specify further requirements on inner parameters that are expected within
  of list or dictionary argument types. In the example test configuration above, the ``inner_types`` values
  should be set like this:
  * ``example_one``: Not set
  * ``example_two``: ``inner_types = [str, int]``
  * ``example_three``: ``inner_types = {'key1': {'required': True, 'type': str}, 'key2': {'required': False, 'type': int}``

The parameter validation described above is very basic and has obviously limitations. In future, we probably
want a parameter validation that is easier to use and has an arbitrary recursion depth.
