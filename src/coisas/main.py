import shlex
from string.templatelib import Template
from typing import TYPE_CHECKING

from rich import print as rprint

from coisas.commands.shell import ShellCommand, ShellCommandProgram
from coisas.state import GlobalState
from coisas.templates import process_shell_template

if TYPE_CHECKING:
  from coisas.commands.shell import ShellArgsType

state: GlobalState = GlobalState()


def p(txt: str) -> None:
  """Print `txt` into current stream."""
  rprint(
    txt,
    file=state.info_stream,
  )


def run(
  cmd: str | ShellArgsType | Template,
  *,
  description: str | None = None,
  render_style: str = "bold",
) -> None:
  """Run a shell command.

  Args:
      cmd: Command to be ran.
      description: Description about command. If empty, will be auto-generated.
      render_style: `rich` style for the main part of the command.

  """
  split_cmd: ShellArgsType
  match cmd:
    case str():
      split_cmd = shlex.split(cmd)
    case Template():
      split_cmd = process_shell_template(cmd)
    case _:
      split_cmd = cmd

  if not split_cmd:
    p("(empty command was ignored)")
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
  )
