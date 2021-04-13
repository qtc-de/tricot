import tricot


tester_template = """tester:
  name: <NAME>
  title: <TITLE>
  description: |-
    <DESCRIPION>


variables:
  <VAR>: <VALUE>


containers:
  - name: <NAME>
    image: <IMAGE>
    volumes:
      - <LOCAL>:<CONTAINER>
    env:
        <KEY>: <VALUE>
    aliases:
      DOCKER-<NAME>-IP: DOCKER-IP
      DOCKER-<NAME>-GATEWAY: DOCKER-GW


plugins:
  - <PLUGIN>


tests:
  - title: <TITLE>
    description: |-
        <DESCRIPTION>

    command:
      - <CMD>
      - <ARGG1>

    validators:
      - <VALIDATOR>


testers:
  - <TESTER>
"""


plugin_template = """import tricot

class MyPlugin(tricot.Plugin):
    '''
    Plugin description.

    Example:

        plugins:
            - my_plugin:
                key: value
    '''
    param_type = dict
    inner_types = {
                    'key': {'required': True, 'type': str},
                  }

    def run(self) -> None:
        '''
        Executed on startup.
        '''
        pass

    def stop(self) -> None:
        '''
        Executed when stopping.
        '''
        pass


tricot.register_plugin('my_plugin', MyPlugin)
"""


validator_template = """import tricot

class MyValidator(tricot.Validator):
    '''
    Validator description.

    Example:

        validators:
            - my_validator:
                key: value
    '''
    param_type = dict
    inner_types = {
            'key': {'required': True, 'type': str},
    }

    def run(self) -> None:
        '''
        Run during validation.
        '''
        if self.command.status != 0:
            raise tricot.ValidationException(f'Failure Reason')

        if 'key' not in self.get_output():
            raise tricot.ValidationException(f'Failure Reason')


tricot.register_validator('my_validator', MyValidator)
"""


def replace_placeholders(template: str) -> str:
    '''
    Replaces the palceholders within a template. Accepted placeholders
    are currently the plugin and validator names.

    Parameters:
        template    YAML template to replace parameters in

    Returns:
        YAML template with placeholders replaced
    '''
    val_list = tricot.get_validator_list()
    val_replace = '\n      - '.join(val_list)

    replaced = template.replace('<VALIDATOR>', val_replace)

    plug_list = tricot.get_plugin_list()
    plug_replace = '\n  - '.join(plug_list)

    replaced = replaced.replace('<PLUGIN>', plug_replace)
    return replaced


def write_template(filename: str, mode: str) -> None:
    '''
    Write the template YAML to the specified file system path.

    Parameters:
        filename    file system location to write to
        mode        Decdides whether the tester, plugin or validator template is written

    Returns:
        None
    '''
    if mode.lower() == 'tester':
        prepared_template = replace_placeholders(tester_template)

    elif mode.lower() == 'plugin':
        prepared_template = plugin_template

    elif mode.lower() == 'validator':
        prepared_template = validator_template

    with open(filename, 'w') as f:
        f.write(prepared_template)
