### tricot Documentation

----

This folder contains some supplementary documentation that would be to long for the
main [README.md](/README.md) of this project. Don't expect it to be complete or helpful
on it's own.

- [Validator and Plugin List](#validator-and-plugin-list)
- [Writing Custom Plugins](#writing-custom-plugins)
- [Writing Custom Validators](#writing-custom-validators)
- [Accessing Command Information from an Validator](#accessing-command-information-from-an-validator)
- [Writing Custom Validators](#writing-custom-validators)
- [Environment Variables](#environment-variables)
- [Runtime Variables](#runtime-variables)
- [Nesting Variables](#nesting-variables)
- [Conditionals](#conditionals)
- [Reusing Output](#reusing-output)
- [Logging](#logging)
- [Additional Command Line Switches](#additional-command-line-switches)


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

Each dictionary based validator (see next section for more details) should add support for the implicit ``stream``
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


### Environment Variables

----

Environment variables can be specified on the tester level and are added to the current users environment
when executing commands. E.g. when using the following tester definition:

```yml
tester:
  name: env
  title: EnvironmentVariables Tests
  description: |-
    'Checks whether environment variables are set correctly'
  env:
    test: test123
    test2: Hello World :D
```

The environment variables ``test=test123`` and ``test2="Hello World :D"`` are added to the current user environment
while running commands.

Environment variables for docker containers can be specified in the corresponding container section. The following
example shows an example for the ``nginx`` container:

```yml
containers:
  - name: 'nginx'
    image: 'nginx:alpine'
    volumes:
      - './${volume}:/usr/share/nginx/html:ro'
      - './Docker/templates:/etc/nginx/templates:ro'
    aliases:
      DOCKER-nginx-IP: DOCKER-IP
    env:
      NGINX_PORT: '8000'
```

To use evaluated environment variables within your test definitions, you have to declare them as variables first.
The following example shows, how the ``$HOME`` environment variable can be used within a test specification.

```yml
tester:
  name: environment_example
  title: Environment Example
  description: |-
    'Demonstrate how to use environment variables'

variables:
  HOME: $env

tests:
  - title: env_test
    description: |-
      'Check whether environment variable is set.'

    command:
      - echo
      - ${HOME}

    validators:
      - contains:
          values:
            - '/home/user'
```


### Runtime Variables

----

Whereas ordinary variables are specified as key value pairs within of test definitions, *runtime variables* are
expected to be passed to *tricot* on the command line or via it's library interface. Nonetheless, it is required
to declare them in the variable sections of a test in order to use them. The following tests shows an example:

```yml
tester:
  name: example
  title: example
  description: |-
    example

variables:
  1: $runtime
  var: $runtime

tests:
  - title: Positional Test
    description: |-
      Positional Test

    command:
      - echo
      - ${1}
      - ${var}

    validators:
      - contains:
          values:
            - Not there
```

Running this tester in verbose mode leads to the following output:

```console
[qtc@host ~]$ tricot -v --variables var=test1 --positionals test2 -- bla.yml
[+] Starting test: mytest
[+]
[+]         1. Positional Test... failed.
[-]             - Caught ValidationException raised by the contains validator.
[-]               Configuration file: /home/qtc/bla.yml
[-]
[-]               Validator run failed because of the following reason:
[-]               String 'Not there' was not found in command output.
[-]
[-]               Command: ['echo', 'test2', 'test1']
[-]               Command exit code: 0
[-]               Command stdout:
[-]                 test2 test1
[-]
[-]               Command stderr:
[-]               Validator parameters:
[-]                 {
[-]                     "values": [
[-]                         "Not there"
[-]                     ]
[-]                 }
```


### Nesting Variables

----

Nesting variables is possible (without recursion). The following tester shows an example:

```yml
tester:
  name: nested_variables
  title: Nested Variables Example
  description: |-
    'Demonstrate how to use nested variables'

variables:
  nested: This is going to be nested
  nest: <NEST>${nested}<NEST>

tests:
  - title: nested_test
    description: |-
      'Check whether nested variable is set.'

    command:
      - echo
      - ${nest}

    validators:
      - contains:
          values:
            - '<NEST>This is going to be nested<NEST>'
```


### Reusing Output

----

Sometimes it is not suitable to put all desired validators within a single test. In these cases, you can use
the ``${prev}`` variable to indicate that you want to reuse the latest command output:

```yml
tests:
  - title: Initial Test
    [...]

  - title: Example Test
    description: |-
      'This example test uses the output of the previous test.'
    command:
      - '${prev}'
```


### Conditionals

----

Sometimes you may want to run a test or tester only if some other test succeed or failed. This is possible by using conditionals.
Conditionals can be defined within *testers* and consist out of a name and an initial boolean value. The following *tester*
shows an example:

```yaml
tester:
  name: cond_launcher
  title: Conditonal Launcher
  description: |-
    'Launcher for conditional tests'

  conditionals:
    Test1: false
    Test2: false
    Test3: true

testers:
  - ./test1.yml
```

Within subsequent *tests* and *testers*, you can use conditionals like this:

```yaml
tester:
  name: cond_test
  title: Conditionals Test
  description: |-
    'Launches some conditional tests and updates some conditions'
  conditions:
    one_of:
      - Test1
      - Test2
      - Test3

tests:
  - title: Example Test
    description: |-
      'Only runs if Test1 and Test2 are False and Test3 is True.
      Updates the conditions after a successful run.'
    conditions:
      none_of:
        - Test1
        - Test2
      all:
        - Test3
      on_success:
        Test1: true
        Test3: false
      on_error:
        Test2: true
        Test3: false
    command:
      - echo
      - "Not relevant"
    validators:
      - status: 0
```

Updating conditions is only allowed within of *tests* and not within *testers*. The ``on_success`` action triggers,
when all validators have run successfully. The ``on_error`` action triggers, if one or more validators failed.


### Logging

----

*tricot* supports logging on *global*, *tester* and *test* level. For global logging, you can use the ``--log <FILE>`` command
line option and all output is mirrored to the specified logfile. Logging single *tests* or *testers* is possible by using the
``logfile`` attribute:

```yaml
tester:
  name: ExampleTester
  title: Just an example test
  logfile: /log/example-tester.log

tests:
  - title: Test curl
    description: |-
      Test that our curl installation is working

    command:
      - curl
      - http://example.org
    logfile: /log/curl-tester.log

    validators:
      - status: 0

  - title: Test wget
    description: |-
      Test that our wget installation is working

    command:
      - wget
      - http://example.org
    logfile: /log/wget-tester.log

    validators:
      - status: 0
```

Log files are always written in verbose mode and contain the full details for each *test* or *tester*.
This is also true, even if the corresponding *test* or *tester* run was successful.


### Additional Command Line Switches

----

Here is some more detailed explanation on some of *tricots* command line switches:

* ``--logfile`` - Mirrors all tricot output into a logfile. Logfiles are always written with verbose output.
* ``--debug`` - Show details on each tester that runs, even when successful. Furthermore, disable
  exception handling and show each exception with full details.
