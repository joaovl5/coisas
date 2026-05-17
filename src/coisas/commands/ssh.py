import shlex
from typing import TYPE_CHECKING, override

from attrs import Factory, define
from rich.text import Text

from coisas.commands.shell import (
  ShellArgsType,
  ShellCommand,
  ShellCommandProgram,
)
from coisas.commands.wrappers.base import BaseCommandWrapper

if TYPE_CHECKING:
  from pathlib import Path


def _quote_for_ssh(parts: ShellArgsType) -> str:
  """Join command parts into remote shell string.

  Will quote args with shlex, but leave globs/operators unquoted so they expand
  on the remote host.
  """
  res: list[str] = []
  for part in parts:
    if part == "" or any(ch.isspace() for ch in part):
      res.append(shlex.quote(part))
    else:
      res.append(part)
  return " ".join(res)


@define(kw_only=True)
class SSHConfig:
  host: str
  port: int
  identity_file: Path


@define(kw_only=True)
class SSHCommand(ShellCommand):
  program: ShellCommandProgram = Factory(
    lambda: ShellCommandProgram(
      shell_args=["ssh"],
      render_style="bold orange",
    )
  )
  inner_command: ShellCommand
  config: SSHConfig

  @override
  def render(self) -> Text:
    return (
      Text()
      .append(self._render_env())
      .append(f"[ssh {self.config.host}]", style=self.program.render_style)
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
      *self._env_prefix(),
      *self.program.shell_args,
      "-i",
      str(self.config.identity_file),
      "-p",
      str(self.config.port),
      *self.args,
      self.config.host,
      "--",
      _quote_for_ssh(self.inner_command.build()),
    ]


@define(kw_only=True)
class SSHCommandWrapper(BaseCommandWrapper):
  config: SSHConfig

  @override
  def wrap(self, cmd: ShellCommand) -> SSHCommand:
    """Wrap a command within a SSHCommand."""
    return SSHCommand(
      inner_command=cmd,
      config=self.config,
    )
