"""
Display beanstalkd stats as a big table with sections

Non-interactive.
"""

import argparse
import time

import greenstalk
from rich.panel import Panel
from rich.table import Table
from rich.console import Console, RenderGroup
from rich.live import Live
from rich.layout import Layout
from rich.rule import Rule
from rich import box

parser = argparse.ArgumentParser()
parser.add_argument("--server", default="127.0.0.1")
parser.add_argument("--port", default=11300, type=int)

args = parser.parse_args()

client = greenstalk.Client((args.server, args.port))
console = Console()


def generate_live_panel(stats: greenstalk.Stats) -> Panel:
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="bold green")
    table.add_column("Value")

    rows = [
        ("# tubes", "current-tubes"),
        ("# connections", "current-connections"),
        ("# producers", "current-producers"),
        ("# workers", "current-workers"),
        ("# waiting", "current-waiting"),
    ]

    for name, key in rows:
        table.add_row(name, str(stats[key]))

    return Panel(table, title="Current stats", title_align="right")


def generate_cmd_table(stats: greenstalk.Stats) -> Table:
    table = Table(
        title="Command",
        title_style="",
        title_justify="left",
        show_header=False,
        box=None,
    )
    table.add_column("Key", style="bold green")
    table.add_column("Value")

    rows = [
        ("# put", "cmd-put"),
        ("# reserve", "cmd-reserve"),
        ("# delete", "cmd-delete"),
        ("# bury", "cmd-bury"),
        ("# release", "cmd-release"),
        ("# kick", "cmd-kick"),
    ]

    for name, key in rows:
        table.add_row(name, str(stats[key]))

    return table


def generate_misc_table(stats: greenstalk.Stats) -> Table:
    table = Table(
        title="Misc", title_style="", title_justify="left", show_header=False, box=None
    )
    table.add_column("Key", style="bold green")
    table.add_column("Value")

    rows = [
        ("# jobs", "total-jobs"),
        ("# connections", "total-connections"),
    ]

    for name, key in rows:
        table.add_row(name, str(stats[key]))

    return table


def generate_lifetime_panel(stats: greenstalk.Stats) -> Panel:
    table1 = generate_cmd_table(stats)
    table2 = generate_misc_table(stats)

    return Panel(
        RenderGroup(table1, Rule("", style=""), table2),
        title="Lifetime counts",
        title_align="right",
    )


def generate_job_panel(stats: greenstalk.Stats):
    table = Table(
        "Key", "Value", show_header=False, show_edge=False, box=box.HORIZONTALS
    )

    rows = [
        ("[red]Urgent", "current-jobs-urgent"),
        ("[green]Ready", "current-jobs-ready"),
        ("[yellow]Reserved", "current-jobs-reserved"),
        ("[magenta]Delayed", "current-jobs-delayed"),
        ("[blue]Buried", "current-jobs-buried"),
    ]

    for name, key in rows:
        table.add_row(name, str(stats[key]))

    panel = Panel(table, title="Current job counts", title_align="right")
    return panel


def generate_beanstalkd_info(stats: greenstalk.Stats):
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="bold green")
    table.add_column("Value")

    rows = [
        ("[b]Version", "version"),
        ("PID", "pid"),
        ("Uptime", "uptime"),
    ]

    for name, key in rows:
        table.add_row(name, str(stats[key]))

    return Panel(table, title="beanstalkd info", title_align="right")


def generate_tube_table(client: greenstalk.Client):
    """Get info about all tubes

    Note: This makes n+1 requests to beanstalkd, where n is the number of tubes,
    so probably not a good idea if there are many tubes active.

    Parameters
    ----------
    client : greenstalk.Client
        Client to talk to beanstalkd
    """

    tubes = client.tubes()

    headers = [
        ("Name", "name"),
        ("[red]#U", "current-jobs-urgent"),
        ("[green]#Y", "current-jobs-ready"),
        ("[yellow]#R", "current-jobs-reserved"),
        ("[magenta]#D", "current-jobs-delayed"),
        ("[blue]#B", "current-jobs-buried"),
        ("# using", "current-using"),
        ("# waiting", "current-waiting"),
        ("# watching", "current-watching"),
        ("pause", "pause"),
        ("Total jobs seen", "total-jobs"),
        ("# del", "cmd-delete"),
    ]

    tube_table = Table(
        *[h[0] for h in headers],
        show_edge=False,
        box=box.HORIZONTALS,
    )

    for tube_name in tubes:
        tube_stats = client.stats_tube(tube_name)

        tube_table.add_row(*[str(tube_stats[h[1]]) for h in headers])

    return Panel(tube_table, title="Tube info", title_align="right")


def generate_screen(client: greenstalk.Client) -> Layout:
    stats = client.stats()

    live_panel = generate_live_panel(stats)
    lifetime_panel = generate_lifetime_panel(stats)
    job_panel = generate_job_panel(stats)
    beanstalkd_panel = generate_beanstalkd_info(stats)

    tube_table = generate_tube_table(client)

    layout = Layout()
    layout.split_row(
        Layout(name="overall-stats"),
        Layout(tube_table, name="tube-info", ratio=2),
    )
    layout["overall-stats"].split_column(
        Layout(job_panel, minimum_size=7),
        Layout(live_panel, minimum_size=7),
        Layout(lifetime_panel, minimum_size=12),
        Layout(beanstalkd_panel, size=5),
    )

    return layout


with Live(console=console, screen=True, auto_refresh=False) as live:
    while True:
        live.update(generate_screen(client), refresh=True)
        time.sleep(1)
