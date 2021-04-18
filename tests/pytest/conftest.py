import sys
import tricot

from pathlib import Path


def resolve(base: str, filename: str) -> Path:
    '''
    Resolve the specified filename to the directory specified in base.

    Parameters:
        base        base directory to resolve to
        filename    filename inside base

    Returns:
        path        Path object of the resolved file
    '''
    return Path(base).parent.joinpath(filename)


sys.modules['tricot'].resolve = resolve
