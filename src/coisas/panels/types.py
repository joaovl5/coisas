from typing import Annotated, Literal, final

from pydantic import BaseModel, Discriminator, Field


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
