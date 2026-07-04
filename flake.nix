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
      yfinance
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

      buildInputs = [ pkgs.qt6.qtbase ];

      propagatedBuildInputs = pythonDeps python.pkgs;

      postInstall = ''
        install -Dm644 share/applications/financeguru.desktop \
          $out/share/applications/financeguru.desktop
        install -Dm644 share/icons/hicolor/scalable/apps/financeguru.svg \
          $out/share/icons/hicolor/scalable/apps/financeguru.svg
      '';

      meta = {
        description = "Personal finance desktop app";
        mainProgram = "financeguru";
      };
    };

    checks.${system} = {
      # `nix flake check` should also prove the package still builds.
      package = self.packages.${system}.default;

      pytest = pkgs.runCommand "financeguru-pytest"
        {
          nativeBuildInputs = [
            (python.withPackages (ps: (pythonDeps ps) ++ [ ps.pytest ]))
          ];
          # Qt aborts in the sandbox without a usable fontconfig setup.
          FONTCONFIG_FILE = pkgs.makeFontsConf {
            fontDirectories = [ pkgs.dejavu_fonts ];
          };
        } ''
        export HOME=$TMPDIR                # Qt needs a writable ~/.cache
        export QT_QPA_PLATFORM=offscreen   # headless; devShell's "wayland;xcb" doesn't apply here
        export PYTHONPATH=${self}/src
        cd $TMPDIR
        pytest ${self}/tests -p no:cacheprovider
        touch $out
      '';
    };

    devShells.${system}.default = pkgs.mkShell {
      packages = [
        (python.withPackages (ps: (pythonDeps ps) ++ [ ps.pytest ]))
        pkgs.adwaita-icon-theme
        pkgs.hicolor-icon-theme
      ];

      # Qt6's xcb platform plugin dlopens libxcb-cursor.so at runtime; the
      # packaged output gets this for free from wrapQtAppsHook, but the
      # devShell's raw `python -m financeguru.main` needs it on LD_LIBRARY_PATH.
      #
      # QT_PLUGIN_PATH must NOT inherit from the login shell: on a KDE Plasma
      # session it already points at the system Qt (a different qtbase build
      # than the one pyside6 here links against), so the xcb/wayland plugins
      # found there fail to load with an ABI mismatch ("found... but could
      # not load"). Pin it to this flake's own qtbase plugins instead.
      shellHook = ''
        export QT_QPA_PLATFORM="wayland;xcb"
        export PYTHONPATH="$PWD/src:$PYTHONPATH"
        export XDG_DATA_DIRS="${pkgs.adwaita-icon-theme}/share:${pkgs.hicolor-icon-theme}/share:$XDG_DATA_DIRS"
        export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [ pkgs.libxcb-cursor ]}:$LD_LIBRARY_PATH"
        export QT_PLUGIN_PATH="${pkgs.qt6.qtbase}/lib/qt-6/plugins"
      '';
    };
  };
}
