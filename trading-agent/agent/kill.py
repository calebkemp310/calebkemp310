"""Kill switch: flatten every paper position and disarm.

    python -m agent.kill --state-dir ../paper-state

Same as the workflow's "kill" button. Re-arming needs `--action rearm` on the
runner, and is refused while the KILL file exists.
"""
import sys

from .runner import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] + ["--action", "kill"]))
