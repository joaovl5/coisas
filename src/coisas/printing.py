from rich import print as rprint

from coisas.state import GlobalState

state: GlobalState = GlobalState()


def p(txt: str) -> None:
  """Print `txt` into current stream."""
  rprint(
    txt,
    file=state.info_stream,
  )
