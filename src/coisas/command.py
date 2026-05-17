import shlex
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from functools import partial
from typing import (
  TYPE_CHECKING,
  Protocol,
  overload,
  override,
  runtime_checkable,
)

from attrs import Factory, define
from rich.text import Text

if TYPE_CHECKING:
  from pathlib import Path

type ShellArgsType = Sequence[str]
type EnvType = Mapping[str, str]


@runtime_checkable
class Command(Protocol):
  def render(self) -> Text:
    """Render command for human-facing view."""
    ...

  def build(self) -> ShellArgsType:
    """Build command into shell-facing structure."""
    ...


def _render_env(env: EnvType) -> Text:
  """Render envvars as multi-line header."""
  text = Text()
  for key, value in env.items():
    text = (
      text.append("  ")
      .append(key, style="yellow")
      .append("=", style="dim")
      .append(value, style="white")
      .append("\n")
    )
  return text


def _env_prefix(env: EnvType) -> ShellArgsType:
  return (
    [
      "env",
      *[f"{k}={v}" for k, v in env.items()],
    ]
    if env
    else []
  )


def _default_env(_: ShellCommand) -> EnvType:
  return {}


def _default_shell_args(_: ShellCommand) -> ShellArgsType:
  return []


def _default_render_str(cmd: ShellCommandProgram) -> str:
  return " ".join(cmd.shell_args)


@define(kw_only=True)
class ShellCommandProgram:
  shell_args: ShellArgsType
  render_str: str = Factory(_default_render_str, takes_self=True)
  render_style: str = "bold"


@define(kw_only=True)
class ShellCommand:
  program: ShellCommandProgram
  args: ShellArgsType = Factory(_default_shell_args, takes_self=True)
  env: EnvType = Factory(_default_env, takes_self=True)

  def render(self) -> Text:
    """Render command for human viewing."""
    return (
      Text()
      .append(_render_env(self.env))
      .append("$ ", style="dim")
      .append(self.program.render_str, style=self.program.render_style)
      .append((" " + " ".join(self.args)) if self.args else "", style="dim")
    )

  def build(self) -> ShellArgsType:
    """Build command for shell execution."""
    return [
      *_env_prefix(self.env),
      *self.program.shell_args,
      *self.args,
    ]


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
      *_env_prefix(self.env),
      *self.program.shell_args,
      *_get_nix_flags(),
      *self.args,
    ]


@define(kw_only=True)
class NixRunCommand(NixCommand):
  program: ShellCommandProgram = Factory(
    partial(_default_nix_program, is_nix_run=True), takes_self=True
  )


@define(kw_only=True)
class GitCommand(ShellCommand):
  program: ShellCommandProgram = Factory(
    lambda: ShellCommandProgram(
      shell_args=["git"],
      render_style="bold yellow",
    )
  )
  repo_path: str | None = None
  config: dict[str, str] | None = None

  @override
  def render(self) -> Text:
    return (
      super()
      .render()
      .append(
        f" @({self.repo_path})" if self.repo_path else "", style="dim italic"
      )
    )

  @override
  def build(self) -> ShellArgsType:
    return [
      *_env_prefix(self.env),
      *self.program.shell_args,
      *(
        [x for k, v in self.config.items() for x in ["-c", f"{k}={v}"]]
        if self.config
        else []
      ),
      *(["-C", self.repo_path] if self.repo_path else []),
      *self.args,
    ]


@define(kw_only=True)
class GitCommandFactory:
  config: dict[str, str]
  repo_path: str

  def _make(self, args: ShellArgsType) -> GitCommand:
    return GitCommand(
      args=args,
      config=self.config,
      repo_path=self.repo_path,
    )

  def add(self, paths: list[str]) -> GitCommand:
    """Make command for a `git add` operation."""
    return self._make(
      args=["add", *paths],
    )

  def commit(self, msg: str) -> GitCommand:
    """Make command for a `git commit` operation."""
    return self._make(
      args=["commit", "-m", msg],
    )

  def push(
    self,
    remote: str = "origin",
    ref: str = "HEAD",
  ) -> GitCommand:
    """Make command for a `git commit` operation."""
    return self._make(
      args=["push", "-u", remote, ref],
    )


@define(kw_only=True)
class SSHConfig:
  host: str
  port: int
  identity_file: Path


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
class SSHCommand(ShellCommand):
  program: ShellCommandProgram = Factory(
    lambda: ShellCommandProgram(
      shell_args=["ssh"],
      render_style="bold orange",
    )
  )
  inner_command: Command
  config: SSHConfig

  @override
  def render(self) -> Text:
    return (
      Text()
      .append(_render_env(self.env))
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
      *_env_prefix(self.env),
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
class RsyncCommand(ShellCommand):
  program: ShellCommandProgram = Factory(
    lambda: ShellCommandProgram(
      shell_args=["rsync"],
    )
  )
  src: str
  dest: str
  ssh_config: SSHConfig | None = None
  extra_args: ShellArgsType = Factory(_default_shell_args, takes_self=True)
  remote_dest: bool = True

  @override
  def render(self) -> Text:
    display_args = [*self.args, *self.extra_args]
    text = Text().append(_render_env(self.env))
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
      *_env_prefix(self.env),
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


@define(kw_only=True)
class SudoCommand(ShellCommand):
  program: ShellCommandProgram = Factory(
    lambda: ShellCommandProgram(
      shell_args=["sudo"],
      render_style="bold red",
    )
  )
  inner_command: Command

  @override
  def render(self) -> Text:
    return (
      Text()
      .append(_render_env(self.env))
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


class BaseCommandWrapper(ABC):
  @abstractmethod
  def wrap(self, cmd: Command) -> Command:
    """Wrap instance of command in another command."""

  @overload
  def __or__(self, other: Command) -> Command: ...
  @overload
  def __or__(self, other: BaseCommandWrapper) -> BaseCommandWrapper: ...
  def __or__(
    self, other: BaseCommandWrapper | Command
  ) -> BaseCommandWrapper | Command:
    """Perform a wrap on a command or a wrapper."""
    if isinstance(other, Command):
      return self.wrap(other)
    return _ComposedCommandWrapper(
      outer=self,
      inner=other,
    )


@define(kw_only=True)
class _ComposedCommandWrapper(BaseCommandWrapper):
  """Represents a nested wrapper, a command wrapper composed with another."""

  outer: BaseCommandWrapper
  inner: BaseCommandWrapper

  @override
  def wrap(self, cmd: Command) -> Command:
    return self.outer.wrap(self.inner.wrap(cmd))


@define(kw_only=True)
class SSHCommandWrapper(BaseCommandWrapper):
  config: SSHConfig

  @override
  def wrap(self, cmd: Command) -> SSHCommand:
    """Wrap a command within a SSHCommand."""
    return SSHCommand(
      inner_command=cmd,
      config=self.config,
    )


class SudoCommandWrapper(BaseCommandWrapper):
  @override
  def wrap(self, cmd: Command) -> SudoCommand:
    """Wrap a command within a SudoCommand."""
    return SudoCommand(inner_command=cmd)


class PassthroughCommandWrapper(BaseCommandWrapper):
  @override
  def wrap(self, cmd: Command) -> Command:
    """Don't wrap a command, a no-op."""
    return cmd
