from typing import TYPE_CHECKING, override

from coisas.commands.wrappers.base import BaseCommandWrapper

if TYPE_CHECKING:
  from coisas.commands.shell import ShellCommand


class PassthroughCommandWrapper(BaseCommandWrapper):
  @override
  def wrap(self, cmd: ShellCommand) -> ShellCommand:
    """Don't wrap a command, a no-op."""
    return cmd
