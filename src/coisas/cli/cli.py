import subprocess
import sys
from typing import TYPE_CHECKING, TextIO

from attrs import Factory, define
from rich.panel import Panel
from rich.text import Text

from coisas.output import OutputMode, plain_text, strip_ansi
from coisas.panels.main import PanelFactory, make_some_panel
from coisas.panels.types import PanelStatus

if TYPE_CHECKING:
  from coisas.commands.shell import ShellArgsType, ShellCommand
  from coisas.panels.protocols import PanelWriter


@define
class CLIPanelFactory(PanelFactory):
  info_stream: TextIO = Factory(lambda: sys.stdout)
  error_stream: TextIO = Factory(lambda: sys.stderr)

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

  def _command_label(self, command_line: str | Text) -> str:
    plain = plain_text(command_line).strip()
    return plain.removeprefix("$ ").strip()

  def _write_plain(self, line: str, *, error: bool = False) -> None:
    stream = self.error_stream if error else self.info_stream
    print(strip_ansi(line), file=stream)

  def _write_condense_start(
    self, command_label: str, plain_command: str
  ) -> None:
    self._write_plain(f"[RUN] {command_label}")
    self._write_plain(plain_command)

  def _collect_process_output(
    self,
    process: subprocess.Popen[str],
    output_mode: OutputMode.Type,
  ) -> list[str]:
    output_lines: list[str] = []
    if process.stdout is None:
      return output_lines

    for line in process.stdout:
      formatted = self._format_process_line(line)
      output_lines.append(formatted)
      if isinstance(output_mode, OutputMode.Condense):
        self._write_plain(formatted)
    return output_lines

  def _write_condense_finish(
    self,
    *,
    command_label: str,
    command_executable: ShellArgsType | None,
    return_code: int,
    return_failed: bool,
  ) -> None:
    status = "FAILED" if return_failed else "DONE"
    self._write_plain(f"[{status}] {command_label} exit={return_code}")
    if return_failed and command_executable:
      self._write_plain(f"Full command: {command_executable}")

  def _write_quiet_failure(
    self,
    *,
    command_label: str,
    plain_command: str,
    command_executable: ShellArgsType | None,
    output_lines: list[str],
    return_code: int,
  ) -> None:
    self._write_plain(
      f"[FAILED] {command_label} exit={return_code}",
      error=True,
    )
    self._write_plain(plain_command, error=True)
    if output_lines:
      for line in output_lines:
        self._write_plain(line, error=True)
    else:
      self._write_plain("(no output captured)", error=True)
    if command_executable:
      self._write_plain(f"Full command: {command_executable}", error=True)

  def _run_command_plain(
    self,
    *,
    process: subprocess.Popen[str],
    command_line: str | Text,
    command_executable: ShellArgsType | None = None,
    output_mode: OutputMode.Type,
    ok_codes: tuple[int, ...],
  ) -> int:
    command_label = self._command_label(command_line)
    plain_command = plain_text(command_line)
    if isinstance(output_mode, OutputMode.Condense):
      self._write_condense_start(command_label, plain_command)

    output_lines = self._collect_process_output(process, output_mode)
    return_code = process.wait()
    return_failed = return_code not in ok_codes

    match output_mode:
      case OutputMode.Condense():
        self._write_condense_finish(
          command_label=command_label,
          command_executable=command_executable,
          return_code=return_code,
          return_failed=return_failed,
        )
      case OutputMode.Quiet():
        if return_failed:
          self._write_quiet_failure(
            command_label=command_label,
            plain_command=plain_command,
            command_executable=command_executable,
            output_lines=output_lines,
            return_code=return_code,
          )
      case OutputMode.Panel():
        raise RuntimeError

    return return_code

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

  def info(
    self, msg: str, output_mode: OutputMode.Type | None = None
  ) -> None:
    """Print an info message."""
    output_mode = output_mode or OutputMode.Panel()
    match output_mode:
      case OutputMode.Panel():
        self.console.print(
          make_some_panel(
            msg,
            "INFO",
            "blue",
          )
        )
      case OutputMode.Condense():
        print(f"INFO: {msg}")  # noqa: T201
      case _:
        return

  def run_command(  # noqa: PLR0913
    self,
    command: ShellCommand,
    description: str,
    writer: PanelWriter | None = None,
    error_cls: type[Exception] | None = None,
    ok_codes: tuple[int, ...] = (0,),
    output_mode: OutputMode.Type | None = None,
  ) -> int:
    """Run a command and stream results.

    Args:
        command: Command-like object to run.
        description: Human-facing command description.
        writer: PanelWriter instance, if any.
        error_cls: Error class to raise, defaults to RuntimeError.
        ok_codes: Which codes are 'acceptable' and won't get treated as errors.
        output_mode: How command output should be rendered.

    Returns:
      Return code of command.

    """
    error_cls = error_cls or RuntimeError
    mode = output_mode or OutputMode.Panel()
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
      match mode:
        case OutputMode.Panel():
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
        case OutputMode.Condense() | OutputMode.Quiet():
          print(msg, file=self.error_stream)
      raise error_cls() from exc

    match mode:
      case OutputMode.Panel():
        return_code: int = self._stream_command(
          title=panel_title,
          command_line=command_line,
          command_executable=command_executable,
          process=process,
          writer=writer,
        )
      case OutputMode.Condense() | OutputMode.Quiet():
        return_code = self._run_command_plain(
          command_line=command_line,
          command_executable=command_executable,
          process=process,
          output_mode=mode,
          ok_codes=ok_codes,
        )

    if return_code not in ok_codes:
      raise error_cls()
    return return_code
