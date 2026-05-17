import os
import pwd
import shlex
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from string.templatelib import Interpolation
from typing import TYPE_CHECKING, Final, override

from attrs import Factory, define

if TYPE_CHECKING:
  from string.templatelib import Template

  from coisas.commands.shell import ShellArgsType


class BaseShellParam(ABC):
  """Base class for injectable tstring params."""

  @abstractmethod
  def expand(self) -> ShellArgsType:
    """Expand param into shell args."""


@define
class PathShellParam(BaseShellParam):
  path: Path

  @override
  def expand(self) -> ShellArgsType:
    return [str(self.path)]


def path(x: Path) -> PathShellParam:
  """Convert a Path into a PathShellParam."""
  return PathShellParam(x)


@define
class HomeShellParam(BaseShellParam):
  user: str | None = None

  @property
  def _path(self) -> Path:
    return (
      Path(
        pwd.getpwnam(
          self.user,
        ).pw_dir
      )
      if self.user
      else Path.home()
    )

  @property
  def _path_param(self) -> PathShellParam:
    return PathShellParam(path=self._path)

  @override
  def expand(self) -> ShellArgsType:
    return self._path_param.expand()


def home(user: str) -> HomeShellParam:
  """Return a HomeShellParam for a given user."""
  return HomeShellParam(user)


HOME: Final[HomeShellParam] = HomeShellParam()


@define
class GlobShellParam(BaseShellParam):
  glob_pattern: str | Sequence[str]
  cwd: Path = Factory(Path.cwd)

  @override
  def expand(self) -> ShellArgsType:
    patterns = (
      [self.glob_pattern]
      if isinstance(self.glob_pattern, str)
      else self.glob_pattern
    )
    return [
      str(match)
      for pattern in patterns
      for match in self.cwd.glob(
        pattern,
        recurse_symlinks=True,
      )
    ]


@define
class GitLsFilesShellParam(BaseShellParam):
  """BaseShellParam backed by raw `git ls-files` pathspecs."""

  pathspecs: str | Sequence[str]
  cwd: Path = Factory(Path.cwd)

  @override
  def expand(self) -> ShellArgsType:
    specs = (
      [self.pathspecs] if isinstance(self.pathspecs, str) else self.pathspecs
    )
    result = subprocess.run(  # noqa: S603
      ["git", "ls-files", "-z", "--", *specs],  # noqa: S607
      cwd=self.cwd,
      check=True,
      stdout=subprocess.PIPE,
    )
    return [os.fsdecode(path) for path in result.stdout.split(b"\0") if path]


"""HomeShellParam for current user."""


def glob(*patterns: str, full_expand: bool = False) -> GlobShellParam:
  """Return a GlobShellParam.

  Args:
    *patterns: Sequence of patterns for creating globs with.
    full_expand: If set, will treat all pattern strings as extensions and
                 transform them into `**/**.{x}` value, where `{x}` is the
                 old value.

  Returns:
    GlobShellParam

  """
  if full_expand:
    patterns = tuple(f"**/**.{x}" for x in patterns)

  return GlobShellParam(patterns)


def glex(extensions: str) -> GlobShellParam:
  """Return a GlobShellParam from a set of extensions.

  It's basically equivalent to calling `glob` with `full_expand` set, example:
  - `glex("md,mdc")` is equivalent to `glob("md", "mdc", full_expand=True)`

  Args:
    extensions: comma-separated list of extensions in a single string

  Returns:
    GlobShellParam

  """
  return glob(*extensions.split(","), full_expand=True)


def gils(extensions: str) -> GitLsFilesShellParam:
  """Return a GitLsFilesShellParam from a set of extensions.

  This mirrors `glex`, but expands via `git ls-files` instead of Path.glob.

  Args:
    extensions: comma-separated list of extensions in a single string

  Returns:
    GitLsFilesShellParam

  """
  return GitLsFilesShellParam(
    tuple(f":(glob)**/*.{extension}" for extension in extensions.split(","))
  )


def get_shell_template_params(cmd: Template) -> list[BaseShellParam]:
  """Extract instances of `BaseShellParam` from `cmd`."""
  params: list[BaseShellParam] = []
  for item in cmd:
    match item:
      case Interpolation(value):
        match value:
          case BaseShellParam() as param:
            params.append(param)
          case _:
            raise RuntimeError
      case _:
        continue
  return params


def process_shell_template(cmd: Template) -> ShellArgsType:
  """Process a t-string cmd template into appropriate ShellArgsType."""
  parts: list[str] = []

  for item in cmd:
    match item:
      case str() as s:
        parts.extend(shlex.split(s))
      case Interpolation(value):
        match value:
          case BaseShellParam() as param:
            parts.extend(param.expand())
          case _:
            raise RuntimeError

  return parts
