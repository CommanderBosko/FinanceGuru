{
  description = "FinanceGuru — personal finance desktop app";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
  let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    python = pkgs.python312;

    pythonDeps = ps: with ps; [
      pyside6
    ];
  in {
    packages.${system}.default = python.pkgs.buildPythonApplication {
      pname = "financeguru";
      version = "0.1.0";
      pyproject = true;
      src = ./.;

      nativeBuildInputs = [
        python.pkgs.setuptools
        pkgs.qt6.wrapQtAppsHook
      ];

      propagatedBuildInputs = pythonDeps python.pkgs;

      meta = {
        description = "Personal finance desktop app";
        mainProgram = "financeguru";
      };
    };

    devShells.${system}.default = pkgs.mkShell {
      packages = [
        (python.withPackages (ps: (pythonDeps ps) ++ [ ps.pytest ]))
        pkgs.adwaita-icon-theme
        pkgs.hicolor-icon-theme
      ];

      shellHook = ''
        export QT_QPA_PLATFORM="wayland;xcb"
        export PYTHONPATH="$PWD/src:$PYTHONPATH"
        export XDG_DATA_DIRS="${pkgs.adwaita-icon-theme}/share:${pkgs.hicolor-icon-theme}/share:$XDG_DATA_DIRS"
      '';
    };
  };
}
