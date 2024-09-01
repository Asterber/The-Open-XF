import platform
from . import schemas

__all__ = ['schemas']

if platform.system() == 'Windows':
    from . import parsing, utils

    __all__ += ['parsing', 'utils']
