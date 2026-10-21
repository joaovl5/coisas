import re
from typing import Annotated, Literal, final

from pydantic import BaseModel, Discriminator, Field
from rich.text import Text

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


@final
class OutputMode:
  class _Mode(BaseModel):
    message: str | None = Field(
      default=None,
      description="Optional human-readable mode note",
    )

  class Panel(_Mode):
    """Default human-facing Rich panel output."""

    kind: Literal["panel"] = "panel"

  class Condense(_Mode):
    """Plain deterministic output for CI/LLM consumption."""

    kind: Literal["condense"] = "condense"

  class Quiet(_Mode):
    """Suppress successful output; print diagnostics on failure."""

    kind: Literal["quiet"] = "quiet"

  Type = Annotated[
    Panel | Condense | Quiet,
    Discriminator("kind"),
  ]


def strip_ansi(value: str) -> str:
  """Strip ANSI escape sequences from a string."""
  return ANSI_RE.sub("", value)


def plain_text(value: str | Text) -> str:
  """Render Rich text or strings as plain text."""
  match value:
    case Text():
      return value.plain
    case str():
      return value
