import sys
from typing import TYPE_CHECKING, TextIO

from attrs import Factory, define
from rich.console import Console

from coisas.args import parse_output_mode
from coisas.cli.cli import CLIPanelFactory

if TYPE_CHECKING:
  from coisas.output import OutputMode


@define(kw_only=True)
class GlobalState:
  argv: tuple[str, ...] = Factory(lambda: tuple(sys.argv[1:]))
  """Command-line arguments owned by this state."""

  output_mode: OutputMode.Type = Factory(
    lambda self: parse_output_mode(self.argv),
    takes_self=True,
  )
  """How command output should be rendered."""
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
      info_stream=self.info_stream,
      error_stream=self.error_stream,
      default_panel_height=15,
    ),
    takes_self=True,
  )
  """Handles creation and display of commands."""
