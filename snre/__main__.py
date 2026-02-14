# Author: Bradley R. Kinnard
"""
Single entry point: python -m snre
"""

from snre.ports.cli import cli


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
