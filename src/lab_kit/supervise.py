"""The detached half of `lab run`. Started by it, never by hand."""
import sys

from . import runs

if __name__ == "__main__":
    runs.supervise(sys.argv[1])
