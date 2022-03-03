from __future__ import annotations

import time
import docker
import atexit
from typing import Any
from pathlib import Path

import tricot


class TricotContainer:
    '''
    The TricotContainer class represents a docker container that was started by tricot.
    '''

    def __init__(self, name: str, image: str, env: dict[str, str] = None, volumes: dict[str, str] = None,
                 aliases: dict[str, str] = {}, network_mode: str = None, init: int = 2) -> None:
        '''
        Initializes the container and registers an atexit event, but does not start the container.

        Parameters:
            name            Name of the running container
            image           Name of the image to run
            env             Environment variables to assign to the container
            volumes         Volumes to assign to the container
            aliases         Aliases for docker variables
            network_mode    Networking mode to start the container in
            init            Time to wait for container initialization

        Returns:
            None
        '''
        self.name = name
        self.image = image

        self.env = env
        self.volumes = volumes
        self.aliases = aliases
        self.network_mode = network_mode
        self.init = init

        self.client = docker.from_env()
        self.container = None

        atexit.register(self.stop_container)

    def start_container(self) -> None:
        '''
        Starts the container and print somes general information about it. The start
        procedure currently includes a shot timeout of one second. When skipping this,
        it can be the case that the container is not already full up and running when
        other functions are called. As a result, docker variables like the IP address
        might be empty.

        Parameters:
            None

        Returns:
            None
        '''
        tricot.Logger.print('')
        tricot.Logger.print_mixed_yellow('Starting container:', self.name)
        tricot.Logger.increase_indent()

        network_mode = self.network_mode or 'default'

        tricot.Logger.print_mixed_blue_yellow('Image:', self.image)
        tricot.Logger.print_mixed_blue_yellow('Network Mode:', network_mode)
        self.print_volumes()
        self.print_env()

        tricot.Logger.decrease_indent()

        self.client.containers.run(self.image, name=self.name, volumes=self.volumes,
                                   environment=self.env, detach=True, auto_remove=True,
                                   network_mode=self.network_mode)

        self.container = self.client.containers.get(self.name)
        time.sleep(self.init)

    def stop_container(self) -> None:
        '''
        Stops the container. This function does not need to be called manually, as it
        is registered as an exit event during the object initialization.

        Parameters:
            None

        Returns:
            None
        '''
        if self.container:

            tricot.Logger.print('')
            tricot.Logger.print_mixed_yellow('Stopping container:', self.name)

            self.container.stop()
            self.container = None

    def print_env(self) -> None:
        '''
        Prints the containers environment variables in a formatted way.

        Parameters:
            None

        Returns:
            None
        '''
        if not self.env:
            return

        tricot.Logger.print_blue('Environment:')
        tricot.Logger.increase_indent()

        max_length = 0
        for key in self.env.keys():
            if len(key) > max_length:
                max_length = len(key)

        for key, value in self.env.items():
            tricot.Logger.print_yellow(f'{key.ljust(max_length)} = {value}'),

        tricot.Logger.decrease_indent()

    def print_volumes(self) -> None:
        '''
        Prints the containers volumes in a formatted way.

        Parameters:
            None

        Returns:
            None
        '''
        if not self.volumes:
            return

        tricot.Logger.print_blue('Volumes:')
        tricot.Logger.increase_indent()

        max_length = 0
        for key in self.volumes.keys():
            if len(key) > max_length:
                max_length = len(key)

        for key, value in self.volumes.items():
            tricot.Logger.print_yellow(f'{key.ljust(max_length)} = {value}'),

        tricot.Logger.decrease_indent()

    def get_container_variables(self) -> dict[str, str]:
        '''
        Returns a dictionary of container variables. Currently, only the IP address and
        the mounted volumes are included. Additional data may be added in future.

        Parameters:
            None

        Returns:
            dict        Container variables
        '''
        variables = {f'DOCKER-{self.name}-IP': self.container.attrs['NetworkSettings']['IPAddress']}
        variables[f'DOCKER-{self.name}-GATEWAY'] = self.container.attrs['NetworkSettings']['Gateway']

        ctr = 0
        for key, value in self.volumes.items():
            variables[f'DOCKER-{self.name}-VOLUME{ctr}'] = value['bind']
            variables[f'DOCKER-{self.name}-VOLUME{ctr}-HOST'] = key

        for key, value in self.aliases.items():

            try:
                variables[value] = variables[key]

            except KeyError:
                pass

        return variables

    def from_list(input_list: list, path: Path, variables: dict[str, Any]) -> list[TricotContainer]:
        '''
        Returns a list of TricotContainer that were created according to the input list.
        The input list is expected to be the result read in from the containers section
        of a .yml file.

        Parameters:
            input_list      Input list containing container specifications
            path            Path object to the yaml file where the container was defined in
            variables       Variables to apply.

        Returns:
            list            List of corresponding TricotContainer objects
        '''
        containers = list()

        try:

            for item in input_list:

                volume_dict = dict()
                volumes = item.get('volumes', [])
                volumes = tricot.utils.apply_variables(volumes, variables)

                for volume in volumes:
                    split = volume.split(':')

                    if '/' in split[0]:
                        p = Path(split[0])

                        if not p.is_absolute():
                            p = path.parent.joinpath(p).absolute()

                    if len(split) < 3:
                        split.append('rw')

                    volume_dict[str(p)] = {'bind': split[1], 'mode': split[2]}

                name = tricot.utils.apply_variables(item['name'], variables)
                image = tricot.utils.apply_variables(item['image'], variables)
                aliases = tricot.utils.apply_variables(item.get('aliases', {}), variables)
                environment = tricot.utils.apply_variables(item.get('env', {}), variables)
                network_mode = tricot.utils.apply_variables(item.get('network_mode'), variables)
                init = tricot.utils.apply_variables(item.get('init', 2), variables)

                container = TricotContainer(name, image, environment, volume_dict, aliases, network_mode, init)
                containers.append(container)

            return containers

        except KeyError as e:
            raise tricot.TesterKeyError(str(e), section='containers')
