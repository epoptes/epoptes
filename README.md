# GSoC 2023 - Epoptes improvements

This repository is a [fork](https://github.com/epoptes/epoptes/pull/191) of
[Epoptes](https://epoptes.org), an [open source](https://gplv3.fsf.org)
computer lab management and monitoring tool.

During Google Summer of Code 2023, [Epoptes
Improvements](https://ellak.gr/wiki/index.php?title=Google_Summer_of_Code_2023_proposed_ideas#Epoptes_improvements)
was accepted as one of the project ideas of the the [Open Technologies Alliance
(GFOSS)](https://summerofcode.withgoogle.com/programs/2023/organizations/open-technologies-alliance-gfoss)
organization. Many thanks to both Google and GSoC for supporting open source
development!

The project goals are:

- Make Epoptes available on more Linux distributions.
- Support screen sharing on Wayland.
- Drop the session service and keep only the system epoptes-client service.
- Use systemd socket activation and autorestart.
- Improve its firewall compatibility.

The current page tracks the development progress.

## Preliminary work

As part of the GSoC proposal, I submitted the following pull request on github:

- [Support screen broadcasting on Wayland/GNOME (PR
  #191)](https://github.com/epoptes/epoptes/pull/191)

The Linux desktop environments are migrating from X11 to Wayland, but most of
the existing screen sharing applications don’t work on Wayland yet; that
includes x11vnc, the tool that Epoptes is currently using. On Wayland/GNOME,
gnome-remote-desktop should be utilized instead, but in an automated manner. A
`vnc-wayland` shell script was developed that uses the
[grdctl](https://gitlab.gnome.org/GNOME/gnome-remote-desktop/-/blob/master/man/grdctl.txt)
gnome- remote-desktop control utility to facilitate screen broadcasting from
the Epoptes gui.py interface. The appropriate gui.py modifications were also
submitted as part of the pull request. The end result is that the screen
broadcasting button now functions the same way under Wayland/GNOME as it does
under Xorg.

## First coding period (May 29 - July 10)

The goals of the first coding period are:

- Make Epoptes available on more Linux distributions.
- Support screen sharing on Wayland.

### 2023-05-29

- Create the development progress page.
- Study the [existing Debian
  packaging](https://github.com/epoptes/epoptes/tree/main/debian).

### 2023-05-30

Study the [RPM Packaging Guide](https://rpm-packaging-guide.github.io/).

### 2023-05-31

Explore obsolete epoptes.spec and rpm versions from
  [repology](https://repology.org/project/epoptes/versions):

- [ALT Sisyphus](https://packages.altlinux.org/en/sisyphus/srpms/epoptes/) has
  a somewhat maintained 22.01 version, but the resulting .rpm isn't installable
  in Fedora 38 due to radically different dependencies.
- [openSUSE](https://build.opensuse.org/package/show/Education/epoptes) offers
  an ancient 0.5.9_bzr0.545.
- rpmsphere claims to have a [21.02
  version](https://github.com/rpmsphere/source/raw/master/e/epoptes-21.02-1.src.rpm).
  But it's actually an unmaintained 0.5.x version that depends on the
  deprecated and unavailable tightvnc and python2.7 packages, so it fails when
  trying to install it.

### 2023-06-01 / 2023-06-02

Study the [Python Packaging User Guide](https://packaging.python.org/en/latest/).

### 2023-06-05

First attempt at an epoptes.spec.

### 2023-06-06

Migrate configuration from the Debian-specific `/etc/default/epoptes-*` paths
to the distro-agnostic `/etc/epoptes/common/*.conf`,
`/etc/epoptes/server/*.conf` and `/etc/epoptes/client/*.conf` paths.

### 2023-06-07

Generate initial rpm (non-working yet) on Fedora 38 by following some [online
documentation](https://rogerwelin.github.io/rpm/rpmbuild/2015/04/04/rpmbuild-tutorial-part-1.html).
Useful commands:

    # Install development packages
    sudo yum install -y rpmdevtools rpmlint
    # Set up a development tree
    rpmdev-setuptree
    # Evaluate macros
    rpm --eval %{_localstatedir}
    # Show all definitions and marcos
    rpm --showrc
    # Download the sources of a spec file
    spectool -gR ~/rpmbuild/SPECS/epoptes.spec
    # Download build dependencies
    sudo yum builddep ~/rpmbuild/SPECS/epoptes.spec
    # Build binary packages
    rpmbuild -bb ~/rpmbuild/SPECS/epoptes.spec

### 2023-06-08

Make the epoptes-client rpm package function properly. Useful commands for
comparison with the deb package:

    # List files in an rpm package
    rpm -qlp ~/rpmbuild/RPMS/noarch/epoptes-client-main-1.noarch.rpm
    # Install a local rpm package
    sudo yum localinstall ~/rpmbuild/RPMS/noarch/epoptes-client-main-1.noarch.rpm

Fedora controls which services are automatically enabled by system-preset
files. For epoptes-client.service, this isn't a problem; it will be enabled
when the sysadmin runs `epoptes-client -c`. But for epoptes.service, we'll
either need to document `systemctl enable epoptes`, or ship a systemd-preset
file. Links for handling systemd services in .spec files:

- https://fedoraproject.org/wiki/Packaging:Systemd#Filesystem_locations
- https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/#_systemd
- https://docs.fedoraproject.org/en-US/packaging-guidelines/DefaultServices/#_how_to_enable_a_service_by_default
