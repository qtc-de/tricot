### tricot

----

*tricot* is a *trivial command tester* that allows to test scripts, executables and commands for
expected behavior. Tests are configured within of *YAML* files and simply contain the command definitions
to execute along with a set of desired validators. This approach makes *tricot* a simple solution
for end to end testing of command line applications.


![](https://github.com/qtc-de/tricot/workflows/main%20Python%20CI/badge.svg?branch=main)
![](https://github.com/qtc-de/tricot/workflows/develop%20Python%20CI/badge.svg?branch=develop)
![example-usage](https://tneitzel.eu/73201a92878c0aba7c3419b7403ab604/tricot-example.gif)


### Installation

----

*tricot* can be build and installed as a *pip package*. The following command installs *tricot*
for your current user profile:

```console
$ pip3 install tricot
```

You can also build *tricot* from source by running the following commands:

```console
$ git clone https://github.com/qtc-de/tricot
$ cd tricot
$ python3 setup.py sdist
$ pip3 install dist/*
```

*tricot* also supports autocompletion for *bash*. To take advantage of autocompletion, you need to have the
[completion-helpers](https://github.com/qtc-de/completion-helpers) project installed. If setup correctly, just
copying the [completion script](./resources/bash_completion.d/tricot) to your ``~/.bash_completion.d`` folder enables
autocompletion.

```console
$ cp resources/bash_completion.d/tricot ~/bash_completion.d/
```


### Usage

----

*tricot* tests are defined within of *YAML* files that can contain the following components:

* **Testers**: Each *tricot YAML* file is required to define exactly one *Tester*. The *Tester*
  basically describes the context of the current *YAML* file and sets attributes like it's *name*
  or *error_mode*. Furthermore, *tricot YAML* files can contain references to other *Testers*,
  which allows nesting *Testers*.

* **Tests**: *tricot YAML* files can contain an arbitrary number of *Tests*. Each *Test* contains
  the command you want to test and a set of validators that should be used to validate the commands
  output.

* **Validators**: As mentioned above, *Validators* are used within *Tests* to validate the result
  of a test command. *Validators* usually apply to the command output, but they can validate side
  effects as well. E.g. you can also use *Validators* to check whether a command created a specific
  file on the file system.

* **Plugins**: Plugins are mainly used to setup requirements for tests or to perform cleanup actions.
  They run before the actual *Tests* start and perform cleanup actions after the *Tests* finished.
  Plugins can e.g. be used to create files and directories required for the test, to run an operating
  system command before the test or to spawn a *HTTP listener* that is available during the test.

* **Containers**: When testing commands that interact with other systems, you probably want to run
  your tests against a docker container. *Container* definitions within of *tricot YAML* files can
  be used to start containers before your tests run. A container defined in a *YAML* file runs as
  long as the *Tests* from the corresponding *YAML* file are executed. After all tests have finished,
  the container is stopped.

* **Variables**: *tricot YAML* files can contain variable definitions. These can be used to prevent
  repetitions within of *Test* definitions. *Variables* are inherited when nesting *Testers*, which
  allows the definition of global variables within the toplevel *Tester*, that can be used by all
  sub *Testers*.

Sounds too complicated? Let's look at some examples!


### Examples

----

In this section we list some examples on how to use *tricot*. The tests performed in these examples
do not really make sense and are only used for demonstration purposes. If you are interested in some
real word examples, you should check the [Projects that use tricot](#projects-that-use-tricot) section.

**Example 1**:

* Test definition:
  ```yaml
  tester:
    name: ExampleTester
    title: Just an example test

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
              - www-data
            invert:
              - david
  ```
* Output:
  ```console
  [qtc@kali Example]$ tricot -v example1.yml
  [+] Starting test: Just an example test
  [+]
  [+]         1. Test passwd File... success.
  ```

**Example 2**:

* Test definition:
  ```yaml
  tester:
    name: ExampleTester
    title: Just an example test

  containers:
    - name: 'nginx'
      image: 'nginx:latest'
      aliases:
        DOCKER-nginx-IP: DOCKER-IP

  tests:
    - title: Test curl
      description: |-
        Test that our curl installation is working

      command:
        - curl
        - ${DOCKER-IP}
      validators:
        - status: 0
        - contains:
            ignore_case: False
            values:
              - Welcome to nginx
              - Thank you for using nginx

    - title: Test wget
      description: |-
        Test that our wget installation is working

      command:
        - wget
        - ${DOCKER-IP}
      validators:
        - status: 0
        - file_contains:
            - file: ./index.html
              contains:
                - Welcome to nginx
                - Thank you for using nginx
        - file_exists:
            cleanup: True
            files:
              - './index.html'
  ```
* Output:
  ```console
  [qtc@kali Example]$ tricot -v example2.yml
  [+] Starting test: Just an example test
  [+]
  [+]     Starting container: nginx
  [+]         Image: nginx:latest
  [+]         Volumes: {}
  [+]         Environment: {}
  [+]
  [+]         1. Test curl... success.
  [+]         2. Test wget... success.
  [+]
  [+]     Stopping container: nginx
  ```


**Example 3**:

* Test definition:
  * ``example3.yml``:
    ```yaml
    tester:
      name: ExampleTester
      title: Just an example test
      error_mode: break

    plugins:
      - mkdir:
          cleanup: True
          force: True
          dirs:
            - ./www
      - copy:
          from:
            - /etc/passwd
          to:
            - ./www
      - http_listener:
          port: 8000
          dir: ./www

    testers:
      - ./example3/curl.yml
      - ./example3/wget.yml
    ```
  * ``curl.yml``
    ```yaml
    tester:
      name: CurlTester
      title: Curl Commands

    tests:

      - title: Test passwd File
        description: |-
          Test whether the passwd file can be obtained from the
          http_listener plugin.

        command:
          - curl
          - http://127.0.0.1:8000/passwd
        validators:
          - status: 0
          - contains:
              values:
                - root
                - bin
                - www-data
    ```
  * ``wget.yml``:
    ```yaml
    tester:
      name: WgetTester
      title: Wget Commands

    plugins:
      - cleanup:
          items:
            - ./passwd
    tests:

      - title: Test passwd File
        description: |-
          Test whether the passwd file can be obtained from the
          http_listener plugin.

        command:
          - wget
          - http://127.0.0.1:8000/passwd
        validators:
          - status: 0
          - file_exists:
              files:
                - './passwd'
          - file_contains:
              - file: ./passwd
                contains:
                  - root
                  - bin
                  - nope
      ```

* Output:
  ```console
  [qtc@kali Example]$ tricot -v example3.yml
  [+] Starting test: Just an example test
  [+]
  [+]     Starting test: Curl Commands
  [+]
  [+]             1. Test passwd File... success.
  [+]
  [+]     Starting test: Wget Commands
  [+]
  [+]             1. Test passwd File... failed.
  [-]                 - Caught ValidationException raised by the file_contains validator.
  [-]                   Validator run failed because of the following reason:
  [-]                   String 'nope' not found in passwd.
  [-]
  [-]                   Command: ['wget', 'http://127.0.0.1:8000/passwd']
  [-]                   Status code: 0
  [-]                   Command output:
  [-]                     --2021-04-03 11:32:56--  http://127.0.0.1:8000/passwd
  [-]                     Connecting to 127.0.0.1:8000... connected.
  [-]                     HTTP request sent, awaiting response... 200 OK
  [-]                     Length: 3635 (3.5K) [application/octet-stream]
  [-]                     Saving to: ‘passwd.2’
  [-]
  [-]                          0K ...                                                   100%  652M=0s
  [-]
  [-]                     2021-04-03 11:32:56 (652 MB/s) - ‘passwd.2’ saved [3635/3635]
  [-]
  [-]
  [-]                   Validator parameters:
  [-]                     [
  [-]                         {
  [-]                             "file": "./passwd",
  [-]                             "contains": [
  [-]                                 "root",
  [-]                                 "bin",
  [-]                                 "nope"
  [-]                             ]
  [-]                         }
  [-]                     ]
  [-]
  [-]         Caught ValidationException while error mode is set to break.
  [-]         Stopping test.
  ```

### Projects that use tricot

----

In this section we list some projects that are using *tricot* for testing. Not because we are proud of,
but only to provide you some more examples on how to use *tricot* for effective testing.

* [remote-method-guesser](https://github.com/qtc-de/remote-method-guesser)
* [ctfcred](https://github.com/qtc-de/ctfcred)
* [tricot](https://github.com/qtc-de/tricot)
