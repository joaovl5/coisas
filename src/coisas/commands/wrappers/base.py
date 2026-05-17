from abc import ABC, abstractmethod
from typing import overload, override

from attrs import define

from coisas.commands.shell import ShellCommand


class BaseCommandWrapper(ABC):
  @abstractmethod
  def wrap(self, cmd: ShellCommand) -> ShellCommand:
    """Wrap instance of command in another command."""

  @overload
  def __or__(self, other: ShellCommand) -> ShellCommand: ...
  @overload
  def __or__(self, other: BaseCommandWrapper) -> BaseCommandWrapper: ...
  def __or__(
    self, other: BaseCommandWrapper | ShellCommand
  ) -> BaseCommandWrapper | ShellCommand:
    """Perform a wrap on a command or a wrapper."""
    if isinstance(other, ShellCommand):
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
  def wrap(self, cmd: ShellCommand) -> ShellCommand:
    return self.outer.wrap(self.inner.wrap(cmd))
