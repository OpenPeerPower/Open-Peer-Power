"""Script to ensure a configuration file exists."""
import argparse
import os

import openpeerpower.config as config_util
from openpeerpower.core import OpenPeerPower

# mypy: allow-untyped-calls, allow-untyped-defs


def run(args):
    """Handle ensure config commandline script."""
    parser = argparse.ArgumentParser(
        description=("Ensure a Open Peer Power config exists, creates one if necessary.")
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="path_to_config_dir",
        default=config_util.get_default_config_dir(),
        help="Directory that contains the Open Peer Power configuration",
    )
    parser.add_argument("--script", choices=["ensure_config"])

    args = parser.parse_args()

    config_dir = os.path.join(os.getcwd(), args.config)

    # Test if configuration directory exists
    if not os.path.isdir(config_dir):
        print("Creating directory", config_dir)
        os.makedirs(config_dir)

    opp = OpenPeerPower()
    opp.config.config_dir = config_dir
    config_path = opp.loop.run_until_complete(async_run(opp))
    print("Configuration file:", config_path)
    return 0


async def async_run(opp):
    """Make sure config exists."""
    path = await config_util.async_ensure_config_exists(opp)
    await opp.async_stop(force=True)
    return path
