"""`artgen` console entry point. Subcommands land here across milestones."""
from __future__ import annotations

import sys


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("artgen <command>\n  pixelize   normalize external art to the game palette/size\n"
              "  (procgen commands arrive in M2+)")
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "pixelize":
        from .pixelize import main as pixelize_main
        return pixelize_main(rest)
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
