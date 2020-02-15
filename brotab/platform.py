import os
import platform


def get_editor() -> str:
    mapping = {
        'Windows': 'notepad'
    }
    system = platform.system()
    editor = mapping.get(system, 'nvim')
    return os.environ.get('EDITOR', editor)
