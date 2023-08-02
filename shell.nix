{ pkgs ? import <nixpkgs> {} }: pkgs.mkShell {
  nativeBuildInputs = with pkgs; [
    quilt

    (python3.withPackages (ps: with ps; [
      httplib2
      six
    ]))
  ];
}
