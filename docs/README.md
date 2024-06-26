### tricot Documentation

----

This folder contains some supplementary documentation that would be to long for the
main [README.md](/README.md) of this project. Don't expect it to be complete or helpful
on it's own.

- [Extractor, Validator and Plugin List](#extractor-validator-and-plugin-list)
- [Writing Custom Plugins](#writing-custom-plugins)
- [Writing Custom Validators](#writing-custom-validators)
- [Writing Custom Extractors](#writing-custom-extractors)
- [Accessing Command Information from an Validator](#accessing-command-information-from-an-validator)
- [Selective Testing](#selective-testing)
  * [Test / Tester IDs](#test--tester-ids)
  * [Test Groups](#test-groups)
- [Environment Variables](#environment-variables)
- [Runtime Variables](#runtime-variables)
- [Nesting Variables](#nesting-variables)
- [Conditionals](#conditionals)
- [Reusing Output](#reusing-output)
- [Logging](#logging)
- [External Requirements](#external-requirements)
- [Custom Strings](#custom-strings)
- [Inline Includes](#inline-includes)
- [Worth Knowing](#worth-knowing)


### Extractor, Validator and Plugin List

----

Currently, the best way to get reliable information on available extractors, plugins and validators
is to read the corresponding parts of *tricot's* source code ([extractor](/tricot/extractor.py),
[plugin](/tricot/plugin.py), [validation](/tricot/validation.py)). However, the following locations
provide a rough overview that may be extended in future:

* [extractors](./extractors)
* [plugins](./plugins)
* [validators](./validators)

The following sections demonstrate how custom *tricot* plugins, validators and extractors can be created.
In case you require more detailed information on how to achieve certain things, please refer
to the source code of *tricot* and read the corresponding class definitions for the ``Extractor``, ``Validator``
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
[qtc@kali ~]$ tricot example.yml --load my_plugin.py
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

  - title: Test Greeting
    description: |-
      Test that 'Hello World :)' is in the command output.

    command:
      - echo
      - Hello World :)
    validators:
      - hello_world:
```

Running this test creates the following output:

```console
[qtc@kali ~]$ tricot example.yml --load my_validator.py
[+] Starting test: Just an example test
[+]     
[+]         1. Test passwd File... success.
```

On the other hand, when changing the command in the above test definition to return ``Ciao World :)`` instead,
the validator will raise a ``ValidationException``:

```console
[qtc@kali ~]$ tricot  -v example.yml --load my_validator.py
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


### Writing Custom Extractors

----

Custom extractors can be created in the same way as custom validators. To create a new extractor,
you should start of with the following command:

```console
$ tricot --template extractor my_extractor.py
```

The template file that is written by this command contains the basic python code required
to create a new extractor. With a few modifications, you can easily arrive at the ``FirstLastCharExtractor``
that is listed below:

```python
import tricot

class FirstLastCharExtractor(tricot.Extractor):
    '''
    Extracts the first and last char of the command output.

    Example:

        extractors:
            - first_last_char:
                variable: example
    '''
    param_type = dict
    inner_types = {
            'variable': {'required': True, 'type': str},
    }

    def extract(self, hotplug: dict) -> None:
        '''
        Extract the first and last character of the command output.
        '''
        cmd_output = self.get_output().strip()
        variable = self.param.get('variable')

        if not cmd_output:
            raise tricot.ExtractException('No command output!', self)

        first_key = f'{variable}-first'
        last_key = f'{variable}-last'

        hotplug[first_key] = cmd_output[0]
        hotplug[last_key] = cmd_output[-1]


tricot.register_extractor('first_last_char', FirstLastCharExtractor)
```

An example for a test with extraction can be found in the following test definition:

```yaml
tester:
  name: ExampleTester
  title: Just an example test

tests:

  - title: Init
    description: |-
      Print a string where we can extract on.

    command:
      - echo
      - 'Hello World :)'
    extractors:
      - first_last_char:
          variable: variable
    validators:
      - contains:
          values:
            - 'Hello World :)'

  - title: Extractor
    description: |-
      Test that the extractor worked like expected

    command:
      - echo
      - ${variable-first}
      - ${variable-last}
    validators:
      - contains:
          values:
            - 'H )'
```

Running this test creates the following output:

```console
[qtc@kali ~]$ tricot -v example.yml --load my_extractor.py
[+] Starting test: Just an example test
[+]
[+]     1. Init... success
[+]     2. Extract... success
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

* ``param_type`` can be used to specify the python type that is expected for the top level argument of a
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


### Selective Testing

----

A common testing scenario is that you just changed a portion of a program and only want to run tests for the affected
component. *tricot* supports this *selective testing* approach by using *IDs* and *test groups*.


#### Test / Tester IDs

*IDs* are exactly what the name suggests, a unique identifier for each test / tester. You can assign them by using the
`id` key within of test definitions. *IDs* are ordinary strings and can contain any characters. If a test / tester
is defined without an *ID*, it's *title* attribute is used as an *ID*. However, in this case
*tricot* does not check for duplicate *IDs* and you may end up with multiple tests / testers having the same *ID*.

```yaml
tester:
  id: '001'
  title: Basic Usage
  description: |-
    Demonstrate the basic usage of IDs and groups

tests:

  - id: '001-01'
    title: Test passwd File
    description: |-
      ...
```

Assigning separate *IDs* for tests is a tedious work and *tricot* supports *ID patterns* to make it a little bit easier.
Each *tester* can use the ``id_pattern`` attribute to define a pattern that is used to assign *test IDs* automatically.
The format is analog to *Python's format strings*:

```yaml
tester:
  id: '001'
  id_pattern: '001-{:02d}'
  title: Basic Usage
  description: |-
    Demonstrate the basic usage of the id_pattern attribute

tests:

  - title: Test passwd File
    description: |-
      ...
```

In the example above, the first *test* within the ``tests`` attribute gets assigned the *ID* ``001-00``, the second
``001-01`` and so on.

To launch tests based on an *ID* you can use the command line switches ``--ids`` and ``--exclude-ids``. When using
``--ids``, *tricot* only runs the tests / testers that match the specified *IDs*. If the *ID* belongs to a tester,
all nested testers and tests are run, independent of their *ID*. The ``--exclude-ids`` can be used to exclude certain
test / tester *IDs* from a test. Notice that ``--exclude-ids`` triggers before ``--ids``, so if you specify the same
*ID* for both command line options, it is not run. On the other hand, this allows you to exclude nested test / tester
*IDs* that are contained within a tester specified with the ``--ids`` option.

*tricot* also supports the options ``--skip-until`` and ``--continue-from``. These option do exactly the same and start
your test from the specified *test / tester ID*. This is useful when a test failed and you want to continue your test
from this point.


#### Test Groups

*Test groups* can be used to group tests / testers together. Each test / tester definition can contain a ``groups`` key,
which is a list within the *YAML* configuration. The contained items are the groups for the corresponding test / tester.
*Test groups* are inherited from parent testers, but stacked instead of being merged together. E.g. when a parent tester
is in the group `io` and the child tester in the group `logging`, the resulting group for the child tester is `io,logging`.

```yaml
# [io.yml]
tester:
  group:
    - io
  name: Test IO Modules
  description: |-
    Test IO Modules for the Software

testers:
  - ./nested.yml


# [nested.yml]
tester:
  group:
    - logging
  name: Test IO Modules - logging
  description: |-
    Test IO Modules for the Software - logging

tests:

  title: Test Error Log
  description: |-
    ...
```

As for *IDs*, you can use the ``--groups`` and ``--exclude-groups`` command line options to run selective tests on *test
groups*. However, group specifications on the command line support some special syntax. The easiest case is that you just
want to run a single test group. E.g. taking the example above, to run the `io,logging` test you could use:

```console
tricot -v example.yml --groups io,logging
```

This is straight forwards, but it can get annoying if you defined `logging` groups in other parent testers than `io`.
To make runs of a single test group, that is contained within different parent test groups easier, it is possible
to specify wildcards.

* `*` can be used to match an arbitrary group
* `**` can be used to match an arbitrary number of arbitrary groups

Running all tests from the `logging` group, independent of the parent test groups can be done like this:

```console
tricot -v example.yml --groups **,logging
```

In addition to wildcards, *tricot* also support *brace expressions*. These can be used to constructed *or-like* test
groups. E.g. to run the `logging` module from the `io` and `networking` parent test groups, you could use:

```console
tricot -v example.yml --groups {io,networking},logging
```

Wildcards and *brace expressions* can also be used together within a group specifications. Whereas *brace expressions* can
be placed at any location of a group specification, wildcards are not allowed within the last comma separated value. Also
for group matching, the `--exclude-groups` option triggers before the `--groups` option.

Both, *IDs* and *test groups* are case sensitive.


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


### External Requirements

----

*tricot* allows you to use arbitrary resources on your system for testing. This can make tests incompatible
across different platforms. To prevent errors at runtime, you can specify some of the external requirements
within your test configuration. *tricot* checks these requirements first before running the tests. Currently,
you can require certain files to exist, certain commands to exist and a specific version of tricot to run the
test. All this needs to be configured within the tester configuration. By using the `url` key, resources can
even be downloaded dynamically during runtime.

```yaml
tester:
  title: Basic Usage
  description: |-
    Demonstrate the basic usage of tricot

  requires:
    files:
      - /etc/passwd
      - path: ~/.local/bin/tool
        url: https://where-to-download-tool-from.com/tool.jar
        hash:
          sha256: e81fb3d921d12bc4ef9d2292d1f2082386e48ffe8b1269c0d846ce17f56e9da8
        mode: 0o755
    commands:
      - cat
      - tool
    tricot:
      eq: 1.9.0
      le: 1.9.0
      lt: 1.9.0
      ge: 1.9.0
      gt: 1.9.0
```

File based requirements support different checksum types:

```yaml
tester:
  title: Basic Usage
  description: |-
    Demonstrate the basic usage of tricot

  requires:
    files:
      - path: /etc/passwd
        md5: c6beb132462d61bdd851de604acec9c7
        sha1: 6de989b32cb10f2361ddaa46ea917a674429b4c6
        sha256: f5aa7815387c6f8bad54554b5632a775f9c95cedcf4400b3f78395d4e2f59c0f
        sha512: c26f20ee2d251198d189b53d4f3437769b4381dcf8d53c7e445740de333b2e671a2133932fb2089e2d90ec7eef78af3fefbe28d0d6b6d5dbdaf5a121705ed347
```


### Custom Strings

----

*Testers*, *tests* and *validators* accept an additional *yml attribute* ``output``. This attribute
is expected to be structured like this:

```yml
output:
  success_string: worked :)
  success_color: cyan
  failure_string: nope :(
  failure_color: magenta
```

Output specifications in *tests* overwrite settings in *testers* and output specifications in *validators*
overwrite settings in *tests*. *Validators* are only allowed to set the ``failure_string`` and ``failure_color``
settings. Furthermore, support for *validators* is currently limited by their parameter type. The ``output`` attribute
can only be specified for *validators* that have an dictionary parameter type.


### Inline Includes

----

As already demonstrated by the [example section](https://github.com/qtc-de/tricot#examples), *tricot* testers can be
nested to split test configurations into individual files. A tester including other testers starts them automatically
and passes context information like variables to them. Visually, each nested tester looks like a separate tester run.

In some situations, you want test definitions to be defined within a separate file but not want to create a separate
tester for them. A common example are shared test definitions, that are used by several testers and expected to create
the same output. Such tests definitions can be included using the `include` key, which inlines the test definitions from
the specified files as they were defined in the current test configuration. Here is a quick example:

```yml
tester:
  title: Include Usage
  description: |-
    Demonstrate the usage of the include key

variables:
  passwd: /etc/passwd

tests:

  - title: Test passwd File
    description: |-
      Test that our passwd file contains some expected user names.
      Make sure that david is not contained within our passwd file.

    command:
      - cat
      - ${passwd}
    validators:
      - status: 0
      - contains:
          ignore_case: False
          values:
            - root
            - bin
          invert:
            - david

include:
  - ./shared/example.yml
```

The test configuration displayed above contains one test definition. However, the `include` key is used to include
another configuration file. The specified file is expected to contain additional test definitions within a key named
`tests`. These tests are inlined into the current test definition as they were specified in the currently parsed
configuration file.

A more practical example can be found in the [remote-method-guesser](https://github.com/qtc-de/remote-method-guesser)
repository. For *remote-method-guesser* we use separate testers for different *Java* versions. While there are some
tool behavior differences between the different *Java* versions, most of the tests are expected to create the same
output. We store these test definitions in separate shared files that are included by the testers for the different
*Java* versions. This is easier to maintain, but still looks like the tests were defined for each tester individually.


### Worth Knowing

----

The following list contains information on some smaller *tricot* features that did not receive their own section:

* You can always use the ``--debug`` command line option to show details on each tester that runs, even when successful.
  Furthermore, the switch disables exception handling and shows each exception with full details.
* Each *test* can contain the special attribute ``shell`` with a boolean value. If ``True`` commands are executed in shell
  mode.
