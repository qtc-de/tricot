from __future__ import annotations

from pathlib import Path


class ConditionFormatException(Exception):
    '''
    Raised if the condition format in the .yml file was not correct.
    '''
    def __init__(self, message: str, path: Path) -> None:
        '''
        Custom exception class that stores the original exception within a variable.
        '''
        self.path = path
        super().__init__(message)


class Condition:
    '''
    Conditions can be configured within of testers and can be enabled
    or disabled within of tests. Tests can be configured to only run
    if certain conditions are matched.
    '''

    def __init__(self, name: str, state: bool = False) -> None:
        '''
        Initializes the Condition object with a name and an initial
        state.

        Parameters:
            name            Name of the condition
            state           Initial state of the condition

        Returns:
            None
        '''
        self.name = name
        self.state = state

    def enable(self) -> None:
        '''
        Sets the current condition state to True.

        Parameters:
            None

        Returns:
            None
        '''
        self.state = True

    def disable(self) -> None:
        '''
        Sets the current condition state to False.

        Parameters:
            None

        Returns:
            None
        '''
        self.state = False

    def is_enabled(self) -> bool:
        '''
        Returns the current state of the Condition.

        Parameters:
            None

        Returns:
            None
        '''
        return self.state

    def __eq__(self, other) -> bool:
        '''
        Two Conditions are equal, if they have the same name.

        Parameters:
            other       Condition object to compare with

        Returns:
            bool
        '''
        if type(other) is not Condition:
            return False

        return self.name == other.name

    def __hash__(self) -> int:
        '''
        According to __eq__, hashes are also computed on the condition name.

        Parameters:
            None

        Returns:
            hash
        '''
        return hash(self.name)

    def contains_str(condition: str, conditionals: set[Condition]) -> bool:
        '''
        Checks whether {condition} name is contained within the specified
        set of conditions.

        Parameters:
            condition       Condition name to look for
            conditionals    Set of conditions to look in

        Returns:
            result          True if condition was found in conditionals
        '''
        for cond in conditionals:

            if cond.name == condition:
                return True

        return False

    def update_by_str(condition: str, conditionals: set[Condition], value: bool) -> None:
        '''
        Checks the conditionals set for the specified condition string and updates
        the state of the corresponding condition to the specified value.

        Parameters:
            condition       Condition name to look for
            conditionals    Set of conditions to look in
            value           New state value

        Returns:
            None
        '''
        for cond in conditionals:

            if cond.name == condition:
                cond.state = value
                return

    def from_dict(path: Path, input_dict: dict) -> set[Condition]:
        '''
        Creates a set of Conditions from an input dictionary.

        Parameters:
            path            Path to the current .yml file
            input_dict      Input dictionary read from the .yml file

        Returns:
            set             Set of specified Conditions
        '''
        if type(input_dict) is not dict:
            raise ConditionFormatException('Conditions need to be specified as string -> bool pairs', path)

        conditions = set()

        for key, value in input_dict.items():

            if type(key) != str or type(value) != bool:
                raise ConditionFormatException('Conditions need to be specified as string -> bool pairs', path)

            cond = Condition(key, value)
            conditions.add(cond)

        return conditions

    def check_format(path: Path, conditions: dict, conditionals: set[Condition]) -> None:
        '''
        Check that condition section has the correct format within a .yml file. If the format
        is malformed, an exception is raised.

        Parameters:
            path            Path to the .yml file
            conditions      Condition section specified as dictionary
            conditionals    Set of conditions specified by upper testers

        Returns:
            None
        '''
        if conditions is None:
            return True

        cond_all = conditions.get('all', [])
        cond_one_of = conditions.get('one_of', [])
        cond_none_of = conditions.get('none_of', [])

        cond_error = conditions.get('on_error', {})
        cond_success = conditions.get('on_success', {})

        if not all(isinstance(x, list) for x in [cond_all, cond_one_of, cond_none_of]):
            raise ConditionFormatException("The keys 'all', 'one_of' and 'none_of' need to be lists", path)

        if not all(isinstance(x, dict) for x in [cond_error, cond_success]):
            raise ConditionFormatException("The keys 'on_error' and 'on_success' need to be dicts", path)

        for item in set(cond_all + cond_one_of + cond_none_of):

            if not Condition.contains_str(item, conditionals):
                raise ConditionFormatException(f"Condition '{item}' was used but never declared within a tester.", path)

        for current_dict in [cond_error, cond_success]:

            for key, value in current_dict.items():

                if not Condition.contains_str(key, conditionals):
                    raise ConditionFormatException(f"Condition '{key}' was used but never declared within a tester.", path)

                elif type(value) is not bool:
                    raise ConditionFormatException(f"Condition '{key}' is set to a non boolean value.", path)

    def check_conditions(conditions: dict, conditionals: set[Condition]) -> bool:
        '''
        Checks whether the specified conditions allow a run.

        Parameters:
            conditions      Condition section specified as dictionary
            conditionals    Set of conditions specified by upper testers

        Returns:
            None
        '''
        cond_all = conditions.get('all', [])
        cond_one_of = conditions.get('one_of', [])
        cond_none_of = conditions.get('none_of', [])

        conds = set(filter(lambda x: x.is_enabled(), conditionals))

        if cond_one_of:
            c_set = set(map(lambda x: x.name, conds))
            if bool(set(cond_one_of).isdisjoint(c_set)):
                return False

        for cond in cond_all:
            if not Condition.contains_str(cond, conds):
                return False

        for cond in cond_none_of:
            if Condition.contains_str(cond, conds):
                return False

        return True

    def update_conditions(conditions: dict, conditionals: set[Condition], failure: bool) -> None:
        '''
        Updates the specified conditionals according to the specified conditions.

        Parameters:
            conditions      Condition section specified as dictionary
            conditionals    Set of conditions specified by upper testers
            failure         Indicates whether the corresponding test failed or succeeded

        Returns:
            None
        '''
        cond_error = conditions.get('on_error', {})
        cond_success = conditions.get('on_success', {})

        if failure:
            current_dict = cond_error
        else:
            current_dict = cond_success

        for key, value in current_dict.items():
            Condition.update_by_str(key, conditionals, value)
