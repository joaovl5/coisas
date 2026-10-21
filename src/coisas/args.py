import sys
from typing import TYPE_CHECKING, Annotated, Protocol, cast

from cyclopts import App, Parameter
from pydantic import BaseModel

if TYPE_CHECKING:
  from collections.abc import Callable, Sequence
  from inspect import BoundArguments


from coisas.output import OutputMode


class ArgvOutputState(Protocol):
  argv: tuple[str, ...]
  output_mode: OutputMode.Type


class CoisasArgs(BaseModel):
  condense: bool = False
  quiet: bool = False

  def output_mode(self) -> OutputMode.Type:
    """Convert parsed flags into the corresponding output mode."""
    if self.quiet:
      return OutputMode.Quiet()
    if self.condense:
      return OutputMode.Condense()
    return OutputMode.Panel()


def _invoke_bound[TResult](
  command: Callable[..., TResult],
  bound: BoundArguments,
) -> TResult:
  return command(*bound.args, **bound.kwargs)


def _build_common_args_app() -> App:
  app = App(
    help_flags=(),
    version_flags=(),
  )

  def parse_common(
    *tokens: Annotated[
      str,
      Parameter(
        show=False,
        allow_leading_hyphen=True,
      ),
    ],
    args: Annotated[CoisasArgs | None, Parameter(name="*")] = None,
  ) -> tuple[CoisasArgs, tuple[str, ...]]:
    return args or CoisasArgs(), tuple(tokens)

  _ = app.default(parse_common)
  return app


def _parse_common_args(
  argv: Sequence[str],
) -> tuple[CoisasArgs, tuple[str, ...]]:
  app = _build_common_args_app()
  command, bound, _ignored = app.parse_args(
    argv,
    exit_on_error=False,
  )
  return _invoke_bound(command, bound)


def parse_output_args(
  argv: Sequence[str] | None = None,
) -> tuple[OutputMode.Type, tuple[str, ...]]:
  """Parse common output args and return the chosen mode plus script tokens."""
  raw = tuple(sys.argv[1:] if argv is None else argv)
  args, remaining = _parse_common_args(raw)
  return args.output_mode(), remaining


def parse_output_mode(argv: Sequence[str] | None = None) -> OutputMode.Type:
  """Parse common output args and return the chosen output mode."""
  mode, _remaining = parse_output_args(argv)
  return mode


def _build_model_args_app[TArgs: BaseModel](model: type[TArgs]) -> App:
  app = App()

  def parse_model(args: TArgs | None = None) -> TArgs:
    return args or model()

  parse_model.__annotations__ = {
    "args": Annotated[model | None, Parameter(name="*")],
    "return": model,
  }
  _ = app.default(parse_model)
  return app


def _parse_model_args[TArgs: BaseModel](
  model: type[TArgs],
  argv: Sequence[str],
) -> TArgs:
  app = _build_model_args_app(model)
  command, bound, _ignored = app.parse_args(
    argv,
    exit_on_error=False,
  )
  return cast("TArgs", _invoke_bound(command, bound))


def parse_extra_args[TArgs: BaseModel](
  state: ArgvOutputState,
  model: type[TArgs],
  argv: Sequence[str] | None = None,
) -> TArgs:
  """Parse common output flags plus script-specific Pydantic args."""
  raw = state.argv if argv is None else tuple(argv)
  output_mode, remaining = parse_output_args(raw)
  extra_args = _parse_model_args(model, remaining)

  state.argv = raw
  state.output_mode = output_mode
  return extra_args
