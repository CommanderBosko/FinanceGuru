{
  description = "FinanceGuru — personal finance desktop app";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
  let
    # Every system the app is expected to work on. The current hosts are all
    # x86_64-linux; aarch64-linux is evaluated (and CI-checkable on an ARM
    # builder) so a future ARM machine can consume the flake unchanged.
    systems = [ "x86_64-linux" "aarch64-linux" ];

    # Instantiate an output set once per system, handing each builder the
    # per-system pkgs/python/deps it needs.
    forAllSystems = f: nixpkgs.lib.genAttrs systems (system:
      f rec {
        inherit system;
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
        pythonDeps = ps: with ps; [
          pyside6
          yfinance
        ];
      });
  in {
    packages = forAllSystems ({ pkgs, python, pythonDeps, ... }: {
      default = python.pkgs.buildPythonApplication {
        pname = "financeguru";
        version = "0.1.0";
        pyproject = true;
        src = ./.;

        nativeBuildInputs = [
          python.pkgs.setuptools
          pkgs.qt6.wrapQtAppsHook
        ];

        buildInputs = [ pkgs.qt6.qtbase pkgs.libxcb-cursor ];

        # wrapQtAppsHook's automatic wrap pass only wraps ELF/Mach-O files it
        # finds directly in $out/bin, keyed off whether they link Qt libs. For
        # buildPythonApplication that file is bin/financeguru, a makeWrapper
        # stub around a plain Python entry-point script — Qt is loaded
        # indirectly through the PySide6 .so extension modules, so the
        # auto-detect wraps it before Python's own wrapPythonPrograms hook
        # rewraps it for PYTHONPATH/PATH, and the Qt env vars (crucially
        # QT_PLUGIN_PATH — without it Qt can't find *any* platform plugin,
        # hence "no Qt platform plugin could be initialized" even before
        # considering the libxcb-cursor.so problem fixed for the devShell in
        # 2b9efdc) get silently dropped. Disable the automatic pass and wrap
        # explicitly in postFixup, which runs after the Python wrap, so our
        # Qt args land on the final wrapper instead of being clobbered.
        dontWrapQtApps = true;

        propagatedBuildInputs = pythonDeps python.pkgs;

        postInstall = ''
          install -Dm644 share/applications/financeguru.desktop \
            $out/share/applications/financeguru.desktop
          install -Dm644 share/icons/hicolor/scalable/apps/financeguru.svg \
            $out/share/icons/hicolor/scalable/apps/financeguru.svg
        '';

        # Runs after wrapPythonPrograms, so this is the last wrap applied —
        # see the dontWrapQtApps comment above for why that ordering matters.
        # wrapQtApp (from wrapQtAppsHook) still populates $qtWrapperArgs with
        # QT_PLUGIN_PATH etc. from buildInputs even with dontWrapQtApps set.
        postFixup = ''
          wrapQtApp "$out/bin/financeguru" \
            --prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [ pkgs.libxcb-cursor ]}
        '';

        meta = {
          description = "Personal finance desktop app";
          mainProgram = "financeguru";
        };
      };
    });

    checks = forAllSystems ({ pkgs, python, pythonDeps, system, ... }: {
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

      # `package` above only proves the derivation builds — it does not prove
      # the wrapped binary can actually find a Qt platform plugin at runtime
      # (see the dontWrapQtApps/postFixup comments on the package derivation:
      # that exact gap shipped silently on 2026-07-07 and broke natalie-laptop).
      # Launch it for real under Xvfb with the xcb platform — the same plugin
      # family used on the wayland;xcb hosts — so a regression here fails
      # `nix flake check` instead of surfacing only on a real machine.
      qt-launch = pkgs.runCommand "financeguru-qt-launch"
        {
          nativeBuildInputs = [ pkgs.xvfb-run ];
        } ''
        export HOME=$TMPDIR
        LOG=$TMPDIR/launch.log
        set +e
        xvfb-run -a bash -c "QT_QPA_PLATFORM=xcb timeout 5 ${self.packages.${system}.default}/bin/financeguru" > "$LOG" 2>&1
        status=$?
        set -e
        cat "$LOG"
        # timeout's 124 means the app launched and was still running when we
        # killed it — that's success. Any other exit means it died early,
        # almost always a Qt platform-plugin or missing-library error.
        if [ "$status" -ne 124 ]; then
          echo "financeguru exited early (code $status) instead of staying up under Xvfb — see log above"
          exit 1
        fi
        touch $out
      '';
    });

    devShells = forAllSystems ({ pkgs, python, pythonDeps, ... }: {
      default = pkgs.mkShell {
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
    });
  };
}
