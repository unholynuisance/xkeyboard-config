Switched to versioned install directories and files, to enable installing
multiple versions of xkeyboard-config to be installed in parallel.

- Moved the keyboard keymap data to a namespace dedicated to xkeyboard-config:
  `<prefix>/<datadir>/xkeyboard-config-2`.
- Created symbolic link to maintain backward-compatibility with the X11 namespace:
  `<prefix>/<datadir>/X11/xkb` → `<prefix>/<datadir>/xkeyboard-config-2`.
- Renamed `pkg-config`, translation and manual files to include a version:
  - `<prefix>/<datadir>/pkgconfig/xkeyboard-config-2.pc`
  - `<prefix>/<mandir>/man7/xkeyboard-config-2.7`
  - `<prefix>/<localedir>/**/xkeyboard-config-2.mo`
- Created unversioned symbolic links to the previous files for backward-compatibility:
  - `<prefix>/<datadir>/pkgconfig/`: `xkeyboard-config.pc` → `xkeyboard-config-2.pc`
  - `<prefix>/<mandir>/man7/`: `xkeyboard-config.7` → `xkeyboard-config-2.7`
  - `<prefix>/<localedir>/**/`: `xkeyboard-config.mo` → `xkeyboard-config-2.mo`

See [our versioning documentation](VERSIONING.md) for further information.
