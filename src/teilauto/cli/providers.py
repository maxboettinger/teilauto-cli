from __future__ import annotations

import rich_click as click

from teilauto.cli.options import json_option
from teilauto.output.json_out import print_json
from teilauto.output.render import console, providers_table


@click.group()
def providers() -> None:
    """Discover which carsharing operators you can log in to."""


@providers.command("list")
@json_option
@click.pass_obj
def list_providers(app, as_json) -> None:
    """Show login-eligible operators (no login required).

    Pick yours and save it with `teilauto config set api.prov_id <ID>`,
    then run `teilauto auth login`.
    """
    with app.client() as client:
        items = client.login_providers()
    if as_json:
        print_json(items)
        return
    if not items:
        console.print("No login-eligible operators for the configured api.key.")
        return
    console.print(providers_table(items, current=app.settings.prov_id))
