import pwd
from abc import ABC, abstractmethod
from pathlib import Path
from string.templatelib import Interpolation, Template
from typing import override

from attrs import Factory, define

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


@define
class GlobShellParam(BaseShellParam):
  glob_pattern: str
  cwd: Path = Factory(Path.cwd)

  @override
  def expand(self) -> ShellArgsType:
    return []


def process_shell_template(cmd: Template) -> ShellArgsType:
  """Process a t-string cmd template into appropriate ShellArgsType."""
  parts: list[str] = []

  for item in cmd:
    match item:
      case str() as s:
        parts.append(s)
      case Interpolation(
        value,
        _expression,
        conversion,
        format_spec,
      ):
        pass
