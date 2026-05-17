from typing import TYPE_CHECKING, override

from attrs import Factory, define

from coisas.commands.shell import (
  ShellArgsType,
  ShellCommand,
  ShellCommandProgram,
)

if TYPE_CHECKING:
  from rich.text import Text


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
      *self._env_prefix(),
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
