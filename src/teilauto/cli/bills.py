from __future__ import annotations

from pathlib import Path

import rich_click as click

from teilauto.api.errors import ApiError, NotFoundError
from teilauto.api.models import Bill
from teilauto.cli.options import json_option
from teilauto.output.json_out import print_json
from teilauto.output.render import bills_table, console


def _bill_year(bill: Bill) -> str | None:
    return bill.bill_date[:4] if bill.bill_date and len(bill.bill_date) >= 4 else None


def totals_by_currency(bills: list[Bill]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for bill in bills:
        if bill.gross_amount is None:
            continue
        key = bill.currency or "?"
        totals[key] = round(totals.get(key, 0.0) + bill.gross_amount, 2)
    return totals


@click.group()
def bills() -> None:
    """List your bills and download their PDFs (login required)."""


@bills.command("list")
@click.option("--year", type=int, default=None, metavar="YYYY", help="Only bills from this year.")
@json_option
@click.pass_obj
def list_bills(app, year, as_json) -> None:
    """Show your bills, newest first, with the accumulated total."""
    with app.require_auth_client() as client:
        items = client.list_bills()
    if year is not None:
        items = [b for b in items if _bill_year(b) == str(year)]
    if as_json:
        print_json(items)
        return
    if not items:
        console.print("No bills." if year is None else f"No bills in {year}.")
        return
    console.print(bills_table(items, totals_by_currency(items)))


@bills.command("download")
@click.argument("bill_id")
@click.option(
    "--out",
    "out_path",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Where to write the PDF (default: the bill's own file name).",
)
@click.pass_obj
def download_bill(app, bill_id, out_path) -> None:
    """Download the itemized PDF for BILL_ID."""
    with app.require_auth_client() as client:
        items = client.list_bills(expand_document=True)
        bill = next((b for b in items if b.id == bill_id), None)
        if bill is None:
            raise NotFoundError(f"No bill with id {bill_id}.")
        if bill.document is None:
            raise ApiError(f"Bill {bill_id} has no document attached.")
        content = client.download_bill_document(bill.document)
    if out_path is None:
        name = bill.document.file_name or f"bill-{bill.bill_number or bill.id}.pdf"
        out_path = Path(name)
    out_path.write_bytes(content)
    console.print(f"[green]✓ Saved[/green] {out_path} ({len(content)} bytes)")
