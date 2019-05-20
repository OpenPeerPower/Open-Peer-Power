"""Start Open Peer Power."""
from __future__ import print_function

import argparse
import os
import sys
import platform
import asyncio
import json
import subprocess
import sys
import threading
from typing import (  # noqa pylint: disable=unused-import
    List, Dict, Any, TYPE_CHECKING
)

from openpeerpower.const import (
    __version__,
    EVENT_OPENPEERPOWER_START,
    REQUIRED_PYTHON_VER,
    RESTART_EXIT_CODE,
)

if TYPE_CHECKING:
    from openpeerpower import core


def set_loop() -> None:
    """Attempt to use uvloop."""
    import asyncio
    from asyncio.events import BaseDefaultEventLoopPolicy

    policy = None

    if sys.platform == 'win32':
        if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
            # pylint: disable=no-member
            policy = asyncio.WindowsProactorEventLoopPolicy()
        else:
            class ProactorPolicy(BaseDefaultEventLoopPolicy):
                """Event loop policy to create proactor loops."""

                _loop_factory = asyncio.ProactorEventLoop

            policy = ProactorPolicy()
    else:
        try:
            import uvloop
        except ImportError:
            pass
        else:
            policy = uvloop.EventLoopPolicy()

    if policy is not None:
        asyncio.set_event_loop_policy(policy)


def validate_python() -> None:
    """Validate that the right Python version is running."""
    if sys.version_info[:3] < REQUIRED_PYTHON_VER:
        print("Open Peer Power requires at least Python {}.{}.{}".format(
            *REQUIRED_PYTHON_VER))
        sys.exit(1)


def ensure_config_path(config_dir: str) -> None:
    """Validate the configuration directory."""
    import openpeerpower.config as config_util
    lib_dir = os.path.join(config_dir, 'deps')

    # Test if configuration directory exists
    if not os.path.isdir(config_dir):
        if config_dir != config_util.get_default_config_dir():
            print(('Fatal Error: Specified configuration directory does '
                   'not exist {} ').format(config_dir))
            sys.exit(1)

        try:
            os.mkdir(config_dir)
        except OSError:
            print(('Fatal Error: Unable to create default configuration '
                   'directory {} ').format(config_dir))
            sys.exit(1)

    # Test if library directory exists
    if not os.path.isdir(lib_dir):
        try:
            os.mkdir(lib_dir)
        except OSError:
            print(('Fatal Error: Unable to create library '
                   'directory {} ').format(lib_dir))
            sys.exit(1)


async def ensure_config_file(opp: 'core.OpenPeerPower', config_dir: str) \
        -> str:
    """Ensure configuration file exists."""
    import openpeerpower.config as config_util
    config_path = await config_util.async_ensure_config_exists(
        opp, config_dir)

    if config_path is None:
        print('Error getting configuration path')
        sys.exit(1)

    return config_path

def get_arguments() -> argparse.Namespace:
    """Get parsed passed in arguments."""
    import openpeerpower.config as config_util
    parser = argparse.ArgumentParser(
        description="Open Peer Power: Observe, Control, Automate.")
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        '-c', '--config',
        metavar='path_to_config_dir',
        default=config_util.get_default_config_dir(),
        help="Directory that contains the Open Peer Power configuration")
    parser.add_argument(
        '--demo-mode',
        action='store_true',
        help='Start Open Peer Power in demo mode')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Start Open Peer Power in debug mode')
    parser.add_argument(
        '--open-ui',
        action='store_true',
        help='Open the webinterface in a browser')
    parser.add_argument(
        '--skip-pip',
        action='store_true',
        help='Skips pip install of required packages on startup')
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose logging to file.")
    parser.add_argument(
        '--pid-file',
        metavar='path_to_pid_file',
        default=None,
        help='Path to PID file useful for running as daemon')
    parser.add_argument(
        '--log-rotate-days',
        type=int,
        default=None,
        help='Enables daily log rotation and keeps up to the specified days')
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Log file to write to.  If not set, CONFIG/open-peer-power.log '
             'is used')
    parser.add_argument(
        '--log-no-color',
        action='store_true',
        help="Disable color logs")
    parser.add_argument(
        '--runner',
        action='store_true',
        help='On restart exit with code {}'.format(RESTART_EXIT_CODE))
    parser.add_argument(
        '--script',
        nargs=argparse.REMAINDER,
        help='Run one of the embedded scripts')
    if os.name == "posix":
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run Open Peer Power as daemon')

    arguments = parser.parse_args()
    if os.name != "posix" or arguments.debug or arguments.runner:
        setattr(arguments, 'daemon', False)

    return arguments


def daemonize() -> None:
    """Move current process to daemon process."""
    # Create first fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    # Decouple fork
    os.setsid()

    # Create second fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    # redirect standard file descriptors to devnull
    infd = open(os.devnull, 'r')
    outfd = open(os.devnull, 'a+')
    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(infd.fileno(), sys.stdin.fileno())
    os.dup2(outfd.fileno(), sys.stdout.fileno())
    os.dup2(outfd.fileno(), sys.stderr.fileno())


def check_pid(pid_file: str) -> None:
    """Check that Open Peer Power is not already running."""
    # Check pid file
    try:
        with open(pid_file, 'r') as file:
            pid = int(file.readline())
    except IOError:
        # PID File does not exist
        return

    # If we just restarted, we just found our own pidfile.
    if pid == os.getpid():
        return

    try:
        os.kill(pid, 0)
    except OSError:
        # PID does not exist
        return
    print('Fatal Error: OpenPeerPower is already running.')
    sys.exit(1)


def write_pid(pid_file: str) -> None:
    """Create a PID File."""
    pid = os.getpid()
    try:
        with open(pid_file, 'w') as file:
            file.write(str(pid))
    except IOError:
        print('Fatal Error: Unable to write pid file {}'.format(pid_file))
        sys.exit(1)


def closefds_osx(min_fd: int, max_fd: int) -> None:
    """Make sure file descriptors get closed when we restart.

    We cannot call close on guarded fds, and we cannot easily test which fds
    are guarded. But we can set the close-on-exec flag on everything we want to
    get rid of.
    """
    from fcntl import fcntl, F_GETFD, F_SETFD, FD_CLOEXEC

    for _fd in range(min_fd, max_fd):
        try:
            val = fcntl(_fd, F_GETFD)
            if not val & FD_CLOEXEC:
                fcntl(_fd, F_SETFD, val | FD_CLOEXEC)
        except IOError:
            pass


def cmdline() -> List[str]:
    """Collect path and arguments to re-execute the current opp instance."""
    if os.path.basename(sys.argv[0]) == '__main__.py':
        modulepath = os.path.dirname(sys.argv[0])
        os.environ['PYTHONPATH'] = os.path.dirname(modulepath)
        return [sys.executable] + [arg for arg in sys.argv if
                                   arg != '--daemon']

    return [arg for arg in sys.argv if arg != '--daemon']

def appliance_string():
    print(appliance_list)
    return json.dumps(appliance_list)

async def notify_appliances():
    if USERS:       # asyncio.wait doesn't accept an empty list
        message = appliance_string()
        await asyncio.wait([user.send(message) for user in USERS])

async def register(websocket):
    USERS.add(websocket)
#    await notify_users()

async def unregister(websocket):
    USERS.remove(websocket)
#    await notify_users()

async def appliances_ws(websocket, path):
    # register(websocket) sends appliance list to websocket
    await register(websocket)
    try:
        await websocket.send(appliance_string())
        global appliance_list
        async for message in websocket:
            appliance_list = json.loads(message)
            await notify_appliances()
    finally:
        await unregister(websocket)

async def setup_and_run_opp(config_dir: str,
                             args: argparse.Namespace) -> int:
    """Set up OPP and run."""
    # pylint: disable=redefined-outer-name
    from openpeerpower import bootstrap, core

    opp = core.OpenPeerPower()

    if args.demo_mode:
        config = {
            'frontend': {},
            'demo': {}
        }  # type: Dict[str, Any]
        bootstrap.async_from_config_dict(
            config, opp, config_dir=config_dir, verbose=args.verbose,
            skip_pip=args.skip_pip, log_rotate_days=args.log_rotate_days,
            log_file=args.log_file, log_no_color=args.log_no_color)
    else:
        config_file = await ensure_config_file(opp, config_dir)
        print('Config directory:', config_dir)
        await bootstrap.async_from_config_file(
            config_file, opp, verbose=args.verbose, skip_pip=args.skip_pip,
            log_rotate_days=args.log_rotate_days, log_file=args.log_file,
            log_no_color=args.log_no_color)

    if args.open_ui:
        # Imported here to avoid importing asyncio before monkey patch
        from openpeerpower.util.async_ import run_callback_threadsafe

        def open_browser(_: Any) -> None:
            """Open the web interface in a browser."""
            if opp.config.api is not None:
                import webbrowser
                webbrowser.open(opp.config.api.base_url)

        run_callback_threadsafe(
            opp.loop,
            opp.bus.async_listen_once,
            EVENT_OPENPEERPOWER_START, open_browser
        )

        asyncio.get_event_loop().run_until_complete(
            websockets.serve(appliances_ws, 'localhost', 6789))
        asyncio.get_event_loop().run_forever()

    return await opp.async_run()


def try_to_restart() -> None:
    """Attempt to clean up state and start a new Open Peer Power instance."""
    # Things should be mostly shut down already at this point, now just try
    # to clean up things that may have been left behind.
    sys.stderr.write('Open Peer Power attempting to restart.\n')

    # Count remaining threads, ideally there should only be one non-daemonized
    # thread left (which is us). Nothing we really do with it, but it might be
    # useful when debugging shutdown/restart issues.
    try:
        nthreads = sum(thread.is_alive() and not thread.daemon
                       for thread in threading.enumerate())
        if nthreads > 1:
            sys.stderr.write(
                "Found {} non-daemonic threads.\n".format(nthreads))

    # Somehow we sometimes seem to trigger an assertion in the python threading
    # module. It seems we find threads that have no associated OS level thread
    # which are not marked as stopped at the python level.
    except AssertionError:
        sys.stderr.write("Failed to count non-daemonic threads.\n")

    # Try to not leave behind open filedescriptors with the emphasis on try.
    try:
        max_fd = os.sysconf("SC_OPEN_MAX")
    except ValueError:
        max_fd = 256

    if platform.system() == 'Darwin':
        closefds_osx(3, max_fd)
    else:
        os.closerange(3, max_fd)

    # Now launch into a new instance of Open Peer Power. If this fails we
    # fall through and exit with error 100 (RESTART_EXIT_CODE) in which case
    # systemd will restart us when RestartForceExitStatus=100 is set in the
    # systemd.service file.
    sys.stderr.write("Restarting Open Peer Power\n")
    args = cmdline()
    os.execv(args[0], args)


def main() -> int:
    """Start Open Peer Power."""
    validate_python()

    set_loop()

    # Run a simple daemon runner process on Windows to handle restarts
    if os.name == 'xt' and '--runner' not in sys.argv:
        nt_args = cmdline() + ['--runner']
        while True:
            try:
                subprocess.check_call(nt_args)
                sys.exit(0)
            except KeyboardInterrupt:
                sys.exit(0)
            except subprocess.CalledProcessError as exc:
                if exc.returncode != RESTART_EXIT_CODE:
                    sys.exit(exc.returncode)

    args = get_arguments()

    if args.script is not None:
        from openpeerpower import scripts
        return scripts.run(args.script)

    config_dir = os.path.join(os.getcwd(), args.config)
    ensure_config_path(config_dir)

    # Daemon functions
    if args.pid_file:
        check_pid(args.pid_file)
    if args.daemon:
        daemonize()
    if args.pid_file:
        write_pid(args.pid_file)

    from openpeerpower.util.async_ import asyncio_run
    exit_code = asyncio_run(setup_and_run_opp(config_dir, args))
    if exit_code == RESTART_EXIT_CODE and not args.runner:
        try_to_restart()

    return exit_code  # type: ignore


if __name__ == "__main__":
    sys.exit(main())
