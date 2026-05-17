from typing import TYPE_CHECKING, Annotated, Literal, Protocol, final

from attrs import define
from pydantic import BaseModel, Discriminator, Field

if TYPE_CHECKING:
  from rich.text import Text


class AppendLineFn(Protocol):
  def __call__(self, line: str | Text, style: str | None = None) -> int:
    """Append a line to panel."""
    ...


@final
class PanelStatus:
  class _Status(BaseModel):
    message: str | None = Field(
      default=None, description="Human-readable message for status"
    )
    code: str | None = Field(
      default=None, description="Machine-readable identifier for status"
    )

  class Done(_Status):
    """Status for a finalized operation."""

    warning: str | None = None
    """Set with warning message if finalized with warning."""

    kind: Literal["done"] = "done"

  class Pending(_Status):
    """Progress/pending status, ongoing operation."""

    kind: Literal["pending"] = "pending"

  class Failed(_Status):
    """Status for a failed operation."""

    kind: Literal["failed"] = "failed"

  Type = Annotated[
    Done | Pending | Failed,
    Discriminator("kind"),
  ]


class SetStatusFn(Protocol):
  def __call__(self, status: PanelStatus.Type) -> None:
    """Set panel's state to some status."""
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


@define
class PanelWriter:
  """Wrapper for writing to a panel."""

  append_line: AppendLineFn
  update_line: UpdateLineFn
  set_status: SetStatusFn
