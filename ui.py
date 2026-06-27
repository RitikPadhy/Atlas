"""Tiny terminal UI helpers: colors, banners, and menus."""
import sys

_USE_COLOR = sys.stdout.isatty()


def _c(code: str) -> str:
    return code if _USE_COLOR else ""


RESET = _c("\033[0m")
BOLD = _c("\033[1m")
DIM = _c("\033[2m")
RED = _c("\033[31m")
GREEN = _c("\033[32m")
YELLOW = _c("\033[33m")
BLUE = _c("\033[34m")
MAGENTA = _c("\033[35m")
CYAN = _c("\033[36m")


def banner(text: str) -> None:
    line = "═" * (len(text) + 2)
    print(f"{CYAN}╔{line}╗{RESET}")
    print(f"{CYAN}║ {BOLD}{text}{RESET}{CYAN} ║{RESET}")
    print(f"{CYAN}╚{line}╝{RESET}")


def info(text: str) -> None:
    print(f"{BLUE}ℹ{RESET}  {text}")


def ok(text: str) -> None:
    print(f"{GREEN}✓{RESET}  {text}")


def warn(text: str) -> None:
    print(f"{YELLOW}⚠{RESET}  {text}")


def error(text: str) -> None:
    print(f"{RED}✗{RESET}  {text}", file=sys.stderr)


def prompt(text: str) -> str:
    return input(f"{MAGENTA}{text}{RESET}")
