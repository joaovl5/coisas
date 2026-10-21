import shlex
from string.templatelib import Template
from typing import TYPE_CHECKING

from pydantic import BaseModel
from rich import print as rprint

from coisas.args import parse_extra_args as _parse_extra_args
from coisas.commands.shell import ShellCommand, ShellCommandProgram
from coisas.output import OutputMode
from coisas.state import GlobalState
from coisas.templates import get_shell_template_params, process_shell_template

if TYPE_CHECKING:
  from collections.abc import Sequence

  from coisas.commands.shell import ShellArgsType


state: GlobalState = GlobalState()


def parse_extra_args[TArgs: BaseModel](
  model: type[TArgs],
  argv: Sequence[str] | None = None,
) -> TArgs:
  """Parse common output flags plus script-specific Pydantic args."""
  return _parse_extra_args(state, model, argv)


def p(txt: str, *, output_mode: OutputMode.Type | None = None) -> None:
  """Print `txt` into current stream."""
  mode = output_mode or state.output_mode
  match mode:
    case OutputMode.Quiet():
      return
    case OutputMode.Condense():
      print(txt, file=state.info_stream)
    case OutputMode.Panel():
      rprint(
        txt,
        file=state.info_stream,
      )


def run(
  cmd: str | ShellArgsType | Template,
  *,
  description: str | None = None,
  render_style: str = "bold",
  output_mode: OutputMode.Type | None = None,
) -> None:
  """Run a shell command.

  Args:
      cmd: Command to be ran.
      description: Description about command. If empty, will be auto-generated.
      render_style: `rich` style for the main part of the command.
      output_mode: Output mode override for this command.

  """
  mode = output_mode or state.output_mode

  split_cmd: ShellArgsType
  match cmd:
    case str():
      split_cmd = shlex.split(cmd)
    case Template():
      split_cmd = process_shell_template(cmd)
    case _:
      split_cmd = cmd

  if not split_cmd:
    p("(empty command was ignored)", output_mode=mode)
    return

  program = ShellCommandProgram(
    shell_args=[split_cmd[0]],
    render_style=render_style,
  )
  command = ShellCommand(
    program=program,
    args=split_cmd[1:],
  )
  _ = state.cli_factory.run_command(
    command=command,
    description=description or f"Running {program.render_str}",
    output_mode=mode,
  )


def _print_skip(cmd_name: str, mode: OutputMode.Type) -> None:
  match mode:
    case OutputMode.Panel():
      p(
        f"[yellow dim]Skipping [bold]{cmd_name}[/bold] due to zero matching files",
        output_mode=mode,
      )
    case OutputMode.Condense():
      p(f"[SKIP] {cmd_name}: zero matching files", output_mode=mode)
    case OutputMode.Quiet():
      return


def run_pat(
  *cmds: Template,
  output_mode: OutputMode.Type | None = None,
) -> None:
  """Run commands, skipping those if `gils` param has no matches.

  Will expect commands to have either zero or one params of type
  `GitLsFilesShellParam`.
  """
  mode = output_mode or state.output_mode
  for cmd in cmds:
    cmd_params = get_shell_template_params(cmd)
    # this will at most expect one param of type to be `gils` in `cmd`
    if cmd_params:
      cmd_param = cmd_params.pop()
      cmd_name = cmd.strings[0].split(" ")[0].strip()
      if len(cmd_param.expand()) == 0:
        _print_skip(cmd_name, mode)
        continue
    run(cmd, output_mode=mode)
