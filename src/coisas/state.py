import sys
from typing import TextIO

from attrs import Factory, define


@define(kw_only=True)
class GlobalState:
  info_stream: TextIO = Factory(lambda: sys.stdout)
  """Stream for user-facing messages."""

  log_stream: TextIO = Factory(lambda: sys.stdout)
  """Stream for information-heavy messages."""

  error_stream: TextIO = Factory(lambda: sys.stderr)
  """Stream for error messages."""
