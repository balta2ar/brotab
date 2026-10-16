{
  description = "BroTab browser tab control with Nix-friendly browser integration outputs";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      version = builtins.head (builtins.match ".*__version__ = ['\"]([^'\"]+)['\"].*"
        (builtins.readFile ./brotab/__version__.py));
      lib = nixpkgs.lib;
      projectSource = lib.cleanSourceWith {
        src = self;
        filter =
          path: type:
          let
            base = baseNameOf path;
          in
          !(builtins.elem base [
            ".git"
            ".pytest_cache"
            ".venv"
            "brotab.egg-info"
            "build"
            "dist"
          ])
          && !(lib.hasSuffix ".pem" base);
      };
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = f: lib.genAttrs systems (system: f system);
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          py = pkgs.python3Packages;
          brotab = py.buildPythonApplication {
            pname = "brotab";
            inherit version;
            format = "pyproject";
            src = projectSource;

            nativeBuildInputs = with py; [
              pkgs.installShellFiles
              pkgs.jq
              setuptools
              wheel
            ];

            propagatedBuildInputs = with py; [
              argcomplete
              flask
              psutil
              requests
              rich
              rich-argparse
              werkzeug
            ];

            nativeCheckInputs = with py; [
              pytestCheckHook
              pytest-cov
            ];

            postInstall = ''
              mkdir -p $out/lib/mozilla/native-messaging-hosts $out/lib/chromium/NativeMessagingHosts
              mkdir -p $out/etc/chromium/native-messaging-hosts
              mkdir -p $out/lib/brotab/extensions/chrome $out/lib/brotab/extensions/firefox

              jq --arg out "$out" '.path = "\($out)/bin/brotab_mediator"' \
                brotab/mediator/firefox_mediator.json \
                > $out/lib/mozilla/native-messaging-hosts/brotab_mediator.json

              jq \
                --arg out "$out" \
                '.path = "\($out)/bin/brotab_mediator"' \
                brotab/mediator/chromium_mediator.json \
                > $out/lib/chromium/NativeMessagingHosts/brotab_mediator.json

              cp \
                $out/lib/chromium/NativeMessagingHosts/brotab_mediator.json \
                $out/etc/chromium/native-messaging-hosts/brotab_mediator.json

              cp -R brotab/extension/chrome/. \
                $out/lib/brotab/extensions/chrome/
              cp -R brotab/extension/firefox/. \
                $out/lib/brotab/extensions/firefox/

              local bashCompletion="$TMPDIR/brotab.bash"
              local zshCompletion="$TMPDIR/_brotab"
              ${py.argcomplete}/bin/register-python-argcomplete --shell bash brotab \
                > "$bashCompletion"
              ${py.argcomplete}/bin/register-python-argcomplete --shell zsh brotab \
                > "$zshCompletion"
              installShellCompletion --bash "$bashCompletion" --zsh "$zshCompletion"
            '';

            pythonImportsCheck = [
              "brotab"
            ];
          };

        in
        {
          default = brotab;
          brotab = brotab;
        });

      apps = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          pkg = self.packages.${system}.default;
        in
        {
          default = {
            type = "app";
            program = "${pkg}/bin/brotab";
          };
          brotab = {
            type = "app";
            program = "${pkg}/bin/brotab";
          };
          sign-firefox-addon = {
            type = "app";
            program = "${pkgs.writeShellApplication {
              name = "sign-firefox-addon";
              runtimeInputs = [
                pkgs.git
                pkgs.web-ext
              ];
              text = ''
                exec "${self}/scripts/sign-firefox-addon.sh" "$@"
              '';
            }}/bin/sign-firefox-addon";
          };
        });

      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          py = pkgs.python3.withPackages (ps: [
            ps.argcomplete
            ps.build
            ps.flask
            ps.psutil
            ps.pytest
            ps.pytest-cov
            ps.requests
            ps.rich
            ps.rich-argparse
            ps.werkzeug
          ]);
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.docker
              pkgs.git
              pkgs.go-crx3
              pkgs.jq
              pkgs.just
              pkgs.nodejs
              pkgs.openssl
              pkgs.web-ext
              pkgs.zip
              py
            ];
          };
        });
    };
}
