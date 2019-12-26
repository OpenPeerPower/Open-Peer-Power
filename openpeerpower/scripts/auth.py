"""Script to manage users for the Open Peer Power auth provider."""
import argparse
import asyncio
import logging
import os

from openpeerpower.auth import auth_manager_from_config
from openpeerpower.auth.providers import openpeerpower as opp_auth
from openpeerpower.config import get_default_config_dir
from openpeerpower.core import OpenPeerPower

# mypy: allow-untyped-calls, allow-untyped-defs


def run(args):
    """Handle Open Peer Power auth provider script."""
    parser = argparse.ArgumentParser(description="Manage Open Peer Power users")
    parser.add_argument("--script", choices=["auth"])
    parser.add_argument(
        "-c",
        "--config",
        default=get_default_config_dir(),
        help="Directory that contains the Open Peer Power configuration",
    )

    subparsers = parser.add_subparsers(dest="func")
    subparsers.required = True
    parser_list = subparsers.add_parser("list")
    parser_list.set_defaults(func=list_users)

    parser_add = subparsers.add_parser("add")
    parser_add.add_argument("username", type=str)
    parser_add.add_argument("password", type=str)
    parser_add.set_defaults(func=add_user)

    parser_validate_login = subparsers.add_parser("validate")
    parser_validate_login.add_argument("username", type=str)
    parser_validate_login.add_argument("password", type=str)
    parser_validate_login.set_defaults(func=validate_login)

    parser_change_pw = subparsers.add_parser("change_password")
    parser_change_pw.add_argument("username", type=str)
    parser_change_pw.add_argument("new_password", type=str)
    parser_change_pw.set_defaults(func=change_password)

    args = parser.parse_args(args)
    loop = asyncio.get_event_loop()
    opp = OpenPeerPower(loop=loop)
    loop.run_until_complete(run_command(opp, args))

    # Triggers save on used storage helpers with delay (core auth)
    logging.getLogger("openpeerpower.core").setLevel(logging.WARNING)
    loop.run_until_complete(opp.async_stop())


async def run_command(opp, args):
    """Run the command."""
    opp.config.config_dir = os.path.join(os.getcwd(), args.config)
    opp.auth = await auth_manager_from_config(opp, [{"type": "openpeerpower"}], [])
    provider = opp.auth.auth_providers[0]
    await provider.async_initialize()
    await args.func(opp, provider, args)


async def list_users(opp, provider, args):
    """List the users."""
    count = 0
    for user in provider.data.users:
        count += 1
        print(user["username"])

    print()
    print("Total users:", count)


async def add_user(opp, provider, args):
    """Create a user."""
    try:
        provider.data.add_auth(args.username, args.password)
    except opp_auth.InvalidUser:
        print("Username already exists!")
        return

    # Save username/password
    await provider.data.async_save()
    print("Auth created")


async def validate_login(opp, provider, args):
    """Validate a login."""
    try:
        provider.data.validate_login(args.username, args.password)
        print("Auth valid")
    except opp_auth.InvalidAuth:
        print("Auth invalid")


async def change_password(opp, provider, args):
    """Change password."""
    try:
        provider.data.change_password(args.username, args.new_password)
        await provider.data.async_save()
        print("Password changed")
    except opp_auth.InvalidUser:
        print("User not found")
