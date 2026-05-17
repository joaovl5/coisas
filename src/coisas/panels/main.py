from contextlib import contextmanager
from typing import TYPE_CHECKING, Self

from attrs import define
from rich.box import (
  ASCII,
  HEAVY_HEAD,
  HORIZONTALS,
  MARKDOWN,
  MINIMAL,
  MINIMAL_HEAVY_HEAD,
  ROUNDED,
  SIMPLE_HEAVY,
  Box,
)
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from coisas.panels.protocols import PanelWriter
from coisas.panels.types import PanelStatus

if TYPE_CHECKING:
  from collections.abc import Generator

  from rich.console import Console


# fmt: off
THE_BOX: Box = Box(
    "══╤═\n"
    "    \n"
    "    \n"
    "    \n"
    " ── \n"
    " ── \n"
    "    \n"
    "▔▔▔▔\n"
)
THE_BOX_PENDING: Box = Box(
    "+--+\n"
    "    \n"
    "    \n"
    "    \n"
    "|-+|\n"
    "|-+|\n"
    "    \n"
    "+--+\n"
)
# fmt: on


@define
class PanelFactory:
  console: Console
  default_panel_height: int = 30
  default_panel_box: Box = ASCII

  @contextmanager
  def get_panel(
    self,
    *,
    title: str,
    prelude: list[str],
    max_lines: int | None = None,
    panel_height_override: int | None = None,
    panel_box_override: Box | None = None,
  ) -> Generator[PanelWriter]:
    """Yield a 'PanelWriter' object."""
    lines: list[Text] = [Text(line, style="dim") for line in prelude]
    if max_lines is None:
      max_lines = panel_height_override or min(
        self.console.size.height // 2,
        self.default_panel_height,
      )

    with PanelObject(
      lines=lines,
      title=title,
      status=PanelStatus.Pending(message=None, code=None),
      max_lines=max_lines,
      border_style="dim",
      box_style=panel_box_override or self.default_panel_box,
      console=self.console,
      show_all=False,
    ) as cli_panel:
      yield PanelWriter(
        append_line=cli_panel.append,
        update_line=cli_panel.update_line,
        set_status=cli_panel.set_status,
      )
      cli_panel.update()


@define(kw_only=True)
class PanelObject:
  lines: list[Text]
  title: str
  status: PanelStatus.Type
  max_lines: int
  border_style: str
  box_style: Box
  live: Live | None = None
  console: Console
  show_all: bool = False

  def __enter__(self) -> Self:
    """Handle auto-creating internal 'live' object."""
    self._ensure_live()
    if self.live is None:
      raise RuntimeError
    self.live = self.live.__enter__()
    return self

  def __exit__(self, /, *args: object) -> None:
    """Exit context manager and cleanup of 'live'."""
    if self.live is None:
      raise RuntimeError
    self.live.__exit__(*args)  # pyright: ignore[reportArgumentType]

  def _make_panel(self, text: Text) -> Panel:
    return Panel(
      renderable=text,
      title=f"{self.title}",
      title_align="left",
      border_style=self.border_style,
      box=self.box_style,
      padding=(0, 0),
    )

  def _ensure_live(self) -> None:
    if self.live is None:
      text = Text()
      for line in self.lines:
        _ = text.append(line)
        _ = text.append("\n")
      panel = self._make_panel(text)
      self.live = Live(
        renderable=panel,
        console=self.console,
      )

  def _update_status(self) -> None:
    """Update panel's status-related styles."""
    box_done = THE_BOX
    box_pending = THE_BOX_PENDING
    match self.status:
      case PanelStatus.Done():
        self.box_style = box_done
        self.border_style = "bold " + (
          "green" if self.status.warning is None else "yellow"
        )
        self.show_all = False
      case PanelStatus.Pending():
        self.box_style = box_pending
        self.border_style = "dim"
        self.show_all = False
      case PanelStatus.Failed():
        self.box_style = box_done
        self.border_style = "bold red"
        self.show_all = True

  def set_status(self, status: PanelStatus.Type) -> None:
    """Set status and trigger an update."""
    self.status = status
    self.update()

  def update(self) -> None:
    """Trigger update on panel."""
    self._update_status()
    text = Text()
    visible: list[Text]
    if not self.show_all and len(self.lines) > self.max_lines:
      hidden = len(self.lines) - self.max_lines
      _ = text.append(
        f"... ({hidden} more lines above)\n", style="dim italic"
      )
      visible = self.lines[-self.max_lines :]
    else:
      visible = self.lines
    for line in visible:
      _ = text.append(line)
      _ = text.append("\n")
    if self.live is None:
      raise RuntimeError
    self.live.update(self._make_panel(text))

  def append(self, line: str | Text, style: str | None = None) -> int:
    """Append a line to panel."""
    match line:
      case Text():
        self.lines.append(line)
        if style is not None:
          raise RuntimeError
      case str():
        self.lines.append(Text(line, style=style or ""))
    self.update()
    return len(self.lines) - 1

  def update_line(
    self,
    index: int,
    line: str | Text,
    style: str | None = None,
  ) -> None:
    """Update a specific line in panel."""
    if 0 <= index < len(self.lines):
      match line:
        case Text():
          self.lines[index] = line
          if style is not None:
            raise RuntimeError
        case str():
          self.lines[index] = Text(line, style=style or "")
    self.update()
