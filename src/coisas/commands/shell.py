from collections.abc import Mapping, Sequence

from attrs import Factory, define
from rich.text import Text

type ShellArgsType = Sequence[str]
type EnvType = Mapping[str, str]


def _default_env(_: ShellCommand) -> EnvType:
  return {}


def _default_shell_args(_: ShellCommand) -> ShellArgsType:
  return []


def _default_render_str(cmd: ShellCommandProgram) -> str:
  return " ".join(cmd.shell_args)


@define(kw_only=True)
class ShellCommandProgram:
  shell_args: ShellArgsType
  render_str: str = Factory(_default_render_str, takes_self=True)
  render_style: str = "bold"


@define(kw_only=True)
class ShellCommand:
  program: ShellCommandProgram
  args: ShellArgsType = Factory(_default_shell_args, takes_self=True)
  env: EnvType = Factory(_default_env, takes_self=True)

  def _render_env(self) -> Text:
    """Render envvars as multi-line header."""
    text = Text()
    for key, value in self.env.items():
      text = (
        text.append("  ")
        .append(key, style="yellow")
        .append("=", style="dim")
        .append(value, style="white")
        .append("\n")
      )
    return text

  def _env_prefix(self) -> ShellArgsType:
    return (
      [
        "env",
        *[f"{k}={v}" for k, v in self.env.items()],
      ]
      if self.env
      else []
    )

  def render(self) -> Text:
    """Render command for human viewing."""
    return (
      Text()
      .append(self._render_env())
      .append("$ ", style="dim")
      .append(self.program.render_str, style=self.program.render_style)
      .append((" " + " ".join(self.args)) if self.args else "", style="dim")
    )

  def build(self) -> ShellArgsType:
    """Build command for shell execution."""
    return [
      *self._env_prefix(),
      *self.program.shell_args,
      *self.args,
    ]
