from coisas.main import run_pat
from coisas.templates import gils

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
