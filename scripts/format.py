from typing import TYPE_CHECKING

from coisas.main import p, run
from coisas.templates import get_shell_template_params, gils

if TYPE_CHECKING:
  from string.templatelib import Template


def run_pat(*cmds: Template) -> None:
  """Run commands, skipping those if `gils` param has no matches.

  Will expect commands to have either zero or one params of type
  `GitLsFilesShellParam`.
  """
  for cmd in cmds:
    cmd_params = get_shell_template_params(cmd)
    # this will at most expect one param of type to be `gils` in `cmd`
    if cmd_params:
      cmd_param = cmd_params.pop()
      cmd_name = cmd.strings[0].split(" ")[0].strip()
      if len(cmd_param.expand()) == 0:
        p(
          f"[yellow dim]Skipping [bold]{cmd_name}[/bold] due to zero matching files"
        )
        continue
    run(cmd)


run_pat(
  # markdown
  t"rumdl fmt --no-cache {gils('md')}",
  # nix
  t"alejandra {gils('nix')}",
  t"deadnix -_ -L --edit {gils('nix')}",
  t"statix fix -- .",
  # python
  t"ruff format",
  # shell
  t"shfmt -w -i 2 -s {gils('sh,bash,envrc,envrc.*')}",
  # toml
  t"taplo format {gils('toml')}",
  # yaml
  t"yamlfmt {gils('yaml,yml')}",
  # json
  t"jsonfmt -w {gils('json')}",
  # general
  t"keep-sorted {gils('*')}",
)
