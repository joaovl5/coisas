{
  description = "[{{project_name}}] - {{project_description}}";

  inputs = {
    # nix
    ## pkgs
    nixpkgs.url = "git+https://github.com/NixOS/nixpkgs?ref=nixos-unstable&shallow=1";
    ## systems
    all-systems = {
      url = "git+ssh://git@github.com/nix-systems/default.git?shallow=1";
    };
    ## utils
    flake-utils = {
      url = "git+ssh://git@github.com/numtide/flake-utils.git?shallow=1";
    };
    git-hooks = {
      url = "git+ssh://git@github.com/cachix/git-hooks.nix?shallow=1";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    nixpkgs,
    flake-utils,
    git-hooks,
    ...
  }: let
    flib = flake-utils.lib;
  in
    flib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {inherit system;};
      git_hooks_lib = git-hooks.lib.${system};
      git_hook = git_hooks_lib.run (import ./git-hooks.nix pkgs);

      tooling = with pkgs; [
        prek
        just

        # writing scripts
        fish
        gum
      ];

      formatters = with pkgs; [
        # general
        keep-sorted

        # nix
        alejandra
        deadnix
        statix

        # toml
        taplo

        # yaml
        yamlfmt

        # json
        jsonfmt

        # md
        rumdl
      ];
    in {
      devShells.default = pkgs.mkShell {
        inherit (git_hook) shellHook;
        buildInputs = git_hook.enabledPackages;

        packages =
          tooling
          ++ formatters;
      };
    });
}
