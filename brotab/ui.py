import os
import sys

from rich.console import Console


stdout_console = Console(highlight=True, soft_wrap=True)
stderr_console = Console(stderr=True, highlight=True, soft_wrap=True)


def _is_rich_enabled(console: Console) -> bool:
    if os.environ.get('NO_COLOR'):
        return False
    return bool(console.is_terminal)


def stdout_supports_rich() -> bool:
    return _is_rich_enabled(stdout_console)


def stderr_supports_rich() -> bool:
    return _is_rich_enabled(stderr_console)


def print_info(message: str) -> None:
    if stdout_supports_rich():
        stdout_console.print(message, style='green')
        return
    print(message)


def print_warning(message: str) -> None:
    if stderr_supports_rich():
        stderr_console.print(message, style='yellow')
        return
    print(message, file=sys.stderr)


def print_error(message: str) -> None:
    if stderr_supports_rich():
        stderr_console.print(message, style='bold red')
        return
    print(message, file=sys.stderr)
