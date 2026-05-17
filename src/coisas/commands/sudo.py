from typing import override

from attrs import Factory, define
from rich.text import Text

from coisas.commands.shell import (
  ShellArgsType,
  ShellCommand,
  ShellCommandProgram,
)
from coisas.commands.wrappers.base import BaseCommandWrapper


@define(kw_only=True)
class SudoCommand(ShellCommand):
  program: ShellCommandProgram = Factory(
    lambda: ShellCommandProgram(
      shell_args=["sudo"],
      render_style="bold red",
    )
  )
  inner_command: ShellCommand

  @override
  def render(self) -> Text:
    return (
      Text()
      .append(self._render_env())
      .append(self.program.render_str, style=self.program.render_style)
      .append(
        (" " + " ".join(self.args)) if self.args else "",
        style="dim",
      )
      .append(" ", style="dim")
      .append(self.inner_command.render())
    )

  @override
  def build(self) -> ShellArgsType:
    return [
      *super().build(),
      *self.inner_command.build(),
    ]


class SudoCommandWrapper(BaseCommandWrapper):
  @override
  def wrap(self, cmd: ShellCommand) -> SudoCommand:
    """Wrap a command within a SudoCommand."""
    return SudoCommand(inner_command=cmd)
