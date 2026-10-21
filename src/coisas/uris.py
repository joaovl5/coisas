"""Repository URI parsing for git forge, SSH, HTTPS, and local paths."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Annotated, override

from attrs import define
from pydantic import BeforeValidator, PlainSerializer


class BaseGitURI(ABC):
  @abstractmethod
  def render(self) -> str:
    """Render URI into cloneable/usable string."""


_GIT_URL_PREFIXES = ("git@", "git+ssh://", "ssh://", "https://", "http://")
_LOCAL_PATH_PREFIXES = ("/", "./", "~/")
# do others later (forges etc)


class GitURI:
  type _IsGitURI[T: BaseGitURI] = T
  type Type = _IsGitURI[Local]

  @define
  class Local(BaseGitURI):
    """Local-based URI for git repo."""

    path: Path

    @override
    def render(self) -> str:
      return str(self.path)

  @staticmethod
  def parse(raw: str) -> GitURI.Type:
    """Parse raw value into GitURI."""
    if not raw:
      msg = "Cannot parse empty string into URI."
      raise ValueError(msg)

    if any(raw.startswith(prefix) for prefix in _LOCAL_PATH_PREFIXES):
      return GitURI.Local(Path(raw))

    msg = f"Unknown value for an URI: {raw!r}"
    raise ValueError(msg)


@define
class SerializedGitURI:
  uri: GitURI.Type
  raw: str


GitURIType = Annotated[
  SerializedGitURI,
  BeforeValidator(
    lambda x: SerializedGitURI(raw=x, uri=GitURI.parse(x)),
    json_schema_input_type=str,
  ),
  PlainSerializer(
    lambda x: x.raw,
    return_type=str,
  ),
]
