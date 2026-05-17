from functools import partial
from typing import override

from attrs import Factory, define
from rich.text import Text

from coisas.commands.shell import (
  ShellArgsType,
  ShellCommand,
  ShellCommandProgram,
)


def _default_nix_program(
  _: NixCommand, *, is_nix_run: bool
) -> ShellCommandProgram:
  return ShellCommandProgram(
    shell_args=["nix", "run"] if is_nix_run else ["nix"],
    render_style="bold magenta",
  )


def _get_nix_flags() -> ShellArgsType:
  return ["--option", "experimental-features", "nix-command flakes"]


@define(kw_only=True)
class NixCommand(ShellCommand):
  program: ShellCommandProgram = Factory(
    partial(_default_nix_program, is_nix_run=False), takes_self=True
  )

  @override
  def build(self) -> ShellArgsType:
    return [
      *self._env_prefix(),
      *self.program.shell_args,
      *_get_nix_flags(),
      *self.args,
    ]


@define(kw_only=True)
class NixRunCommand(NixCommand):
  program: ShellCommandProgram = Factory(
    partial(_default_nix_program, is_nix_run=True), takes_self=True
  )
  package: str

  @override
  def render(self) -> Text:
    return (
      Text()
      .append(self._render_env())
      .append("$ ", style="dim")
      .append(self.program.render_str, style=self.program.render_style)
      .append(f" {self.package}", style="cyan")
      .append(
        (" -- " + " ".join(self.args)) if self.args else "",
        style="dim",
      )
    )

  @override
  def build(self) -> ShellArgsType:
    return [
      *self._env_prefix(),
      *self.program.shell_args,
      *_get_nix_flags(),
      self.package,
      *(["--", *self.args] if self.args else []),
    ]
