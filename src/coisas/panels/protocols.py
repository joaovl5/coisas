from typing import TYPE_CHECKING, Protocol

from attrs import define

if TYPE_CHECKING:
  from rich.text import Text

  from coisas.panels.types import PanelStatus


class AppendLineFn(Protocol):
  def __call__(self, line: str | Text, style: str | None = None) -> int:
    """Append a line to panel."""
    ...


class UpdateLineFn(Protocol):
  def __call__(
    self,
    index: int,
    line: str | Text,
    style: str | None = None,
  ) -> None:
    """Update a line of panel."""
    ...


class SetStatusFn(Protocol):
  def __call__(self, status: PanelStatus.Type) -> None:
    """Set panel's state to some status."""
    ...


@define
class PanelWriter:
  """Wrapper for writing to a panel."""

  append_line: AppendLineFn
  update_line: UpdateLineFn
  set_status: SetStatusFn
