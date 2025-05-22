import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import git
import typer
from rich import print
from rich.panel import Panel
from rich.table import Table

FILENAME = "sdt.json"


app = typer.Typer()


def custom_dump(data, fp):
    json.dump(data, fp, indent=4, sort_keys=True, default=str)


class SDT_Panel(Panel):
    def __init__(self, renderable, **kwargs):
        super().__init__(renderable, **kwargs)
        self.title_align = "left"
        self.expand = False
        self.subtitle = "Sudoscientific Doc Tool"
        self.subtitle_align = "right"
        self.border_style = kwargs.get("border_style", "blue")


def sdt_error(text):
    print(SDT_Panel(text, title="Error", border_style="red"))
    raise typer.Exit(code=1)


def check_is_repo():
    if not os.path.isdir(".git"):
        sdt_error("Parent directory is not a git repository")


def check_for_file():
    if not os.path.exists(FILENAME):
        sdt_error(
            f"{FILENAME} file not found, please generate one using [code]sdt init[/code]"
        )


@app.command()
def init():
    if os.path.exists(FILENAME):
        sdt_error(f"{FILENAME} already exists")

    check_is_repo()
    with open(FILENAME, "w") as f:
        custom_dump({}, f)
    print(SDT_Panel(f"{FILENAME} generated", title=":party_popper:"))


@app.command()
def add(
    doc: Annotated[str, typer.Argument(help="Name of the piece of documentation")],
    path: Annotated[
        Path,
        typer.Argument(
            help="Path to the file or directory you want to associate with the documentation",
            exists=True,
        ),
    ],
):
    """
    Add an entry
    """
    check_for_file()
    with open(f"{FILENAME}", "r") as f:
        path_str = path.as_posix()
        entries: dict = json.load(f)
        id = doc.lower().replace(" ", "")
    if id in entries.keys():
        for other_path in map(Path, entries[id]["paths"]):
            if path.resolve() == other_path.resolve():
                sdt_error("Entry already made")
            elif path.is_relative_to(other_path) or other_path.is_relative_to(path):
                sdt_error("Path overlaps with an existing path for this document")
        entries[id]["paths"].append(path_str)
        panel = SDT_Panel(f"{path_str} added to {id}", title="Path added to entry")
    else:
        entries[id] = {
            "document_name": doc.strip(),
            "paths": [path_str],
            "updated": datetime.now(),
        }
        table = Table()
        table.add_column("ID")
        table.add_column("Document", style="green")
        table.add_column(
            "Paths",
            style="cyan",
        )
        table.add_column("Updated Date")
        table.add_row(
            id,
            doc.strip(),
            path_str,
            f"{entries[id]['updated']}",
        )
        panel = SDT_Panel(table, title="Entry made")

    with open(f"{FILENAME}", "w") as f:
        custom_dump(entries, f)

    print(panel)


@app.command()
def ls():
    """
    List entries
    """
    check_for_file()
    with open(f"{FILENAME}", "r") as f:
        entries: dict = json.load(f)
    if not entries:
        sdt_error("No entries found, add some with [code]sdt add[/code]")

    table = Table()
    table.add_column("ID")
    table.add_column("Document", style="green")
    table.add_column(
        "Paths",
        style="cyan",
    )
    table.add_column("Updated Date")
    for key, values in entries.items():
        table.add_row(
            key,
            values["document_name"],
            "\n".join(f"{path}" for path in values["paths"]),
            values["updated"],
        )
    table.show_lines = True
    print(SDT_Panel(table, title="Entries"))


@app.command()
def rm(
    id: Annotated[str, typer.Argument(help="id for entry")],
    path: Annotated[
        Optional[Path],
        typer.Option(
            help="Path to the file or directory you want to associate with the documentation",
            exists=True,
        ),
    ] = None,
):
    """
    Remove an entry
    """
    check_for_file()
    with open(f"{FILENAME}", "r") as f:
        entries: dict = json.load(f)
    try:
        entry = entries[id]
    except KeyError:
        sdt_error(f"Entry {id} not present in {FILENAME}")
        return
    if path:
        path_str = path.as_posix()
        try:
            entry["paths"].remove(path_str)
            print(SDT_Panel(f"{path} deleted from {id}", title="Path deleted"))
        except ValueError:
            if len(entry["paths"]) == 0:
                sdt_error(f"No paths for {id}, please run rm without the --path flag")
            else:
                sdt_error(
                    f"Path not in entry, the following paths are:\n\n{'\n'.join(f'{path}' for path in entry['paths'])}"
                )
    elif len(entry["paths"]) > 0:
        sdt_error(
            f"Cannot remove a document with paths. The following paths are present in this entry:\n\n{'\n'.join(f'{path}' for path in entry['paths'])}\n\nPlease run rm with the --path flag."
        )
    else:
        try:
            entries.pop(id)
            print(SDT_Panel(f"{id} deleted", title="Entry deleted"))
        except KeyError:
            sdt_error("ID not found")

    with open(f"{FILENAME}", "w") as f:
        custom_dump(entries, f)


@app.command()
def check():
    """
    Check your entries against your repos git log
    """
    check_for_file()
    repo = git.Repo(".git")
    with open(f"{FILENAME}", "r") as f:
        entries: dict = json.load(f)
    if not entries:
        sdt_error("No entries found, add some with [code]sdt add[/code]")
    table = Table()
    table.add_column("ID")
    table.add_column("Document", style="green")
    table.add_column(
        "Paths",
        style="cyan",
    )
    table.add_column("Updated Date")
    table.add_column("Commits since last updated")
    table.show_lines = True
    for key, values in entries.items():
        if len(values["paths"]) == 0:
            sdt_error("No entries found, add some with [code]sdt add[/code]")
        print()
        commits = len(
            list(
                repo.iter_commits(
                    paths=[values["paths"]],
                    since=values["updated"],
                    max_count=10,
                )
            )
        )
        if commits == 10:
            cell_style = "on magenta"
        elif commits >= 5:
            cell_style = "on gold1 black"
        else:
            cell_style = "on green4"

        table.add_row(
            key,
            values["document_name"],
            "\n".join(f"{path}" for path in values["paths"]),
            values["updated"],
            f"[{cell_style}]{commits}[/{cell_style}]",
        )
    print(SDT_Panel(table, title="Entries"))


@app.command()
def update(id: Annotated[str, typer.Argument(help="id for entry")]):
    """
    Set the updated date for an entry to today
    """
    check_for_file()
    with open(f"{FILENAME}", "r") as f:
        entries: dict = json.load(f)
    if not entries:
        sdt_error("No entries found, add some with [code]sdt add[/code]")
    try:
        entry = entries[id]
        entry["updated"] = datetime.now()
    except KeyError:
        sdt_error(f"Entry {id} not present in {FILENAME}")
        return

    with open(f"{FILENAME}", "w") as f:
        custom_dump(entries, f)

    print(SDT_Panel(f"{id} updated", title="Entries"))
