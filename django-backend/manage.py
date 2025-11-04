#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import signal
import atexit
import platform

# Path setup for PID files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PID_DIR = os.path.join(BASE_DIR, "pids")
PID_FILES = [
    os.path.join(PID_DIR, "main_script.pid"),
    os.path.join(PID_DIR, "train_script.pid"),
]


def kill_subprocess_on_exit():
    """Kill all background script processes if still running."""
    for pid_file in PID_FILES:
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    pid = int(f.read().strip())

                if platform.system() == "Windows":
                    os.kill(pid, signal.SIGTERM)
                else:
                    os.killpg(pid, signal.SIGTERM)

                print(f"Killed subprocess with PID: {pid} from {os.path.basename(pid_file)}")
                os.remove(pid_file)

            except ProcessLookupError:
                print(f"Process in {os.path.basename(pid_file)} already terminated.")
            except Exception as e:
                print(f"Error killing subprocess from {os.path.basename(pid_file)}: {e}")


# Register the cleanup function
atexit.register(kill_subprocess_on_exit)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Nexify.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
