"""Bootstrap: add `src/` to sys.path so `core`, `agents`, … import cleanly."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> None:
    from web_app.gradio_app import launch

    launch()


if __name__ == "__main__":
    main()
