import sys
from typing import TextIO

from attrs import Factory, define
from rich.console import Console

from coisas.cli.cli import CLIPanelFactory


@define(kw_only=True)
class GlobalState:
  info_stream: TextIO = Factory(lambda: sys.stdout)
  """Stream for user-facing messages."""

  log_stream: TextIO = Factory(lambda: sys.stdout)
  """Stream for information-heavy messages."""

  error_stream: TextIO = Factory(lambda: sys.stderr)
  """Stream for error messages."""

  rich_console: Console = Factory(Console)
  """Console for handling `rich` calls."""

  cli_factory: CLIPanelFactory = Factory(
    lambda self: CLIPanelFactory(
      console=self.rich_console,
      default_panel_height=15,
    ),
    takes_self=True,
  )
  """Handles creation and display of commands."""
