import subprocess
from typing import TYPE_CHECKING

from attrs import define
from rich.panel import Panel
from rich.text import Text

from coisas.panels.main import PanelFactory
from coisas.panels.types import PanelStatus

if TYPE_CHECKING:
  from coisas.commands.shell import ShellArgsType, ShellCommand
  from coisas.panels.protocols import PanelWriter


@define
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
    command: ShellCommand,
    description: str,
    writer: PanelWriter | None = None,
    error_cls: type[Exception] | None = None,
    ok_codes: tuple[int, ...] = (0,),
  ) -> int:
    """Run a command and stream results.

    Args:
        command: Command-like object to run.
        description: Human-facing command description.
        writer: PanelWriter instance, if any.
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
      raise error_cls() from exc
    return_code: int = self._stream_command(
      title=panel_title,
      command_line=command_line,
      command_executable=command_executable,
      process=process,
      writer=writer,
    )

    if return_code not in ok_codes:
      raise error_cls()
    return return_code
