"""Use the repository venv for CLI invocations, without changing library imports."""
import os
from pathlib import Path
import sys


def bootstrap(module):
    venv = Path(__file__).resolve().parent.parent / '.venv'
    interpreter = venv / 'bin' / 'python'
    if interpreter.exists() and Path(sys.prefix).resolve() != venv.resolve():
        os.execv(str(interpreter), [str(interpreter), '-m', module, *sys.argv[1:]])
