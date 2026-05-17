import shlex
from typing import TYPE_CHECKING, override

from attrs import Factory, define
from rich.text import Text

from coisas.commands.shell import (
  ShellArgsType,
  ShellCommand,
  ShellCommandProgram,
)

if TYPE_CHECKING:
  from coisas.commands.ssh import SSHConfig


@define(kw_only=True)
class RsyncCommand(ShellCommand):
  program: ShellCommandProgram = Factory(
    lambda: ShellCommandProgram(
      shell_args=["rsync"],
    )
  )
  src: str
  dest: str
  ssh_config: SSHConfig | None = None
  extra_args: ShellArgsType = Factory(lambda _: [], takes_self=True)
  remote_dest: bool = True

  @override
  def render(self) -> Text:
    display_args = [*self.args, *self.extra_args]
    text = Text().append(self._render_env())
    if self.ssh_config:
      text = text.append(
        f"[ssh {self.ssh_config.host}] ", style="bold orange"
      )
    return (
      text.append("$ ", style="dim")
      .append(self.program.render_str, style=self.program.render_style)
      .append(
        (" " + " ".join(display_args)) if display_args else "",
        style="dim",
      )
      .append(f" {self.src} -> {self.dest}", style="dim")
    )

  @override
  def build(self) -> ShellArgsType:
    cmd = [
      *self._env_prefix(),
      *self.program.shell_args,
      "-avz",
      *self.args,
      *self.extra_args,
    ]
    if self.ssh_config:
      identity = shlex.quote(str(self.ssh_config.identity_file))
      ssh_cmd = f"ssh -i {identity} -p {self.ssh_config.port}"
      cmd += ["-e", ssh_cmd]

    src = self.src
    dest = self.dest
    if self.ssh_config:
      host = self.ssh_config.host
      if self.remote_dest:
        dest = f"{host}:{dest}"
      else:
        src = f"{host}:{src}"
    return [*cmd, src, dest]
