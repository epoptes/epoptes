# Internationalization notes

When new translatable files are added in the source code, POTFILES.in should be regenerated, using the following command:

```shell
    # Be outside the po directory
    test -f "po/POTFILES.in" || exit 1
    (
        echo '[encoding: UTF-8]'
        find * -name '*.py' -o -name '*.ui' | sort | sed 's|.*.ui$|\[type: gettext/glade\]&|'
    ) >po/POTFILES.in
```

This is because when the package is being built, `setup.py build` and specifically /usr/lib/python3/dist-packages/DistUtilsExtra/command/build_i18n.py calls `intltool-update -p -g epoptes`, which, when POTFILES.in isn't provided, generates an unsorted file list, which results in .pot and .po files with very large .diffs.

Note that [Debian recommends](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=792687#30) that .pot and .po file preparation is an upstream and not a packaging task and they shouldn't be regenerated as part of the build process. We can do the upstream part but we currently cannot avoid the .pot regeneration, which might affect reproducible builds.

So when new strings are added in the source code, we should regenerate the .pot file using one of the following commands:

```shell
    # Be inside the po directory
    test -f "POTFILES.in" || exit 1
    intltool-update -p -g epoptes
```

Note that we shouldn't regenerate or merge the .po files as they're handled by https://translations.launchpad.net/epoptes. We should only download them from launchpad periodically.
