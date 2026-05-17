import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Self

from attrs import define
from rich.box import ASCII, ROUNDED, Box
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from coisas.command import Command, ShellArgsType
from coisas.primitives import PanelStatus, PanelWriter

if TYPE_CHECKING:
  from rich.console import Console


@define
class PanelFactory:
  console: Console
  default_panel_height: int = 30
  default_panel_box: Box = ASCII

  def info(self, msg: str) -> None:
    """Display informative message."""
    self.console.print(f"[blue][bold]🛈 :[/bold][/blue] {msg}")

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

  def _make_panel(self, text: Text) -> Panel:
    return Panel(
      renderable=text,
      title=self.title,
      border_style=self.border_style,
      box=self.box_style,
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

  def _update_status(self) -> None:
    """Update panel's status-related styles."""
    match self.status:
      case PanelStatus.Done():
        self.box_style = ROUNDED
        self.border_style = (
          "green" if self.status.warning is None else "yellow"
        )
        self.show_all = False
      case PanelStatus.Pending():
        self.box_style = ASCII
        self.border_style = "dim"
        self.show_all = False
      case PanelStatus.Failed():
        self.box_style = ROUNDED
        self.border_style = "red"
        self.show_all = True
      case _:
        raise RuntimeError

  def set_status(self, status: PanelStatus.Type) -> None:
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


class CLIPanelFactory(PanelFactory):
  def _format_process_line(self, line: str) -> str:
    return line.rstrip("\n").replace("\t", "    ")

  def _format_status_line(
    self,
    line: str | Text,
    status: PanelStatus.Type,
  ) -> Text:
    text = Text()
    prefix: str
    style: str
    match status:
      case PanelStatus.Done():
        if status.warning:
          prefix = "WARNING"
          style = "yellow"
        else:
          prefix = "DONE"
          style = "green"
      case PanelStatus.Pending():
        prefix = "PENDING"
        style = "blue"
      case PanelStatus.Failed():
        prefix = "FAILED"
        style = "red bold"
      case _:
        raise RuntimeError

    _ = text.append(f"{prefix} ", style=style)

    match line:
      case Text():
        _ = text.append_text(line)
      case str():
        _ = text.append(line, style="dim")

    return text

  def _stream_command(
    self,
    *,
    title: str,
    process: subprocess.Popen[str],
    command_line: str | Text,
    command_executable: ShellArgsType | None = None,
    writer: PanelWriter | None = None,
  ) -> int:
    if writer is None:
      with self.get_panel(
        title=title,
        prelude=[],
      ) as panel_writer:
        return self._stream_command(
          title=title,
          process=process,
          command_line=command_line,
          command_executable=command_executable,
          writer=panel_writer,
        )

    command_line_idx: int = writer.append_line(
      line=command_line,
    )
    if process.stdout is not None:
      for line in process.stdout:
        formatted: str = self._format_process_line(line)
        _ = writer.append_line(formatted)
    return_code: int = process.wait()
    return_failed: bool = return_code != 0
    return_status: PanelStatus.Type = (
      PanelStatus.Done() if not return_failed else PanelStatus.Failed()
    )
    status_line: Text = self._format_status_line(
      line=command_line,
      status=return_status,
    )
    writer.update_line(
      index=command_line_idx,
      line=status_line,
    )
    if return_failed:
      if command_executable:
        _ = writer.append_line(
          f"Full command: {command_executable}",
          style="red dim",
        )
      _ = writer.append_line(
        f"Failed with exit code {return_code}",
        style="red",
      )
    writer.set_status(return_status)
    return return_code

  def run_command(
    self,
    command: Command,
    description: str,
    writer: PanelWriter | None = None,
    error_msg: str | None = None,
    error_cls: type[Exception] | None = None,
    ok_codes: tuple[int, ...] = (0,),
  ) -> int:
    """Run a command and stream results.

    Args:
        command: Command-like object to run.
        description: Human-facing command description.
        writer: PanelWriter instance, if any.
        error_msg: Error message to show, if any.
        error_cls: Error class to raise, defaults to RuntimeError.
        ok_codes: Which codes are 'acceptable' and won't get treated as errors.

    Returns:
      Return code of command.

    """
    error_cls = error_cls or RuntimeError
    command_line = command.render()
    command_executable = command.build()
    panel_title = description
    try:
      process: subprocess.Popen[str] = subprocess.Popen(  # noqa: S603
        command_executable,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
      )
    except Exception as exc:
      msg = f"Failed to run command: {exc}"
      if writer:
        code = "failed_run"
        _ = writer.append_line(msg, style="red")
        writer.set_status(
          PanelStatus.Failed(
            message=msg,
            code=code,
          )
        )
      else:
        self.console.print(
          Panel(
            msg,
            title=panel_title,
            border_style="red",
          )
        )
      if error_msg is not None:
        raise error_cls(error_msg) from exc
      return 1
    return_code: int = self._stream_command(
      title=panel_title,
      command_line=command_line,
      command_executable=command_executable,
      process=process,
      writer=writer,
    )

    if error_msg is not None and return_code not in ok_codes:
      raise error_cls(error_msg)
    return return_code
