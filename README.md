# epoptes

Project description: [https://ellak.gr/wiki/index.php?title=GSOC2018\_Projects#Epoptes](https://ellak.gr/wiki/index.php?title=GSOC2018_Projects#Epoptes)

Epoptes websites: [https://epoptes.org/](https://epoptes.org/), [https://github.com/epoptes](https://github.com/epoptes)

## Introduction

[Epoptes](https://epoptes.org/) (Επόπτης  - a Greek word for overseer) is an open source computer lab management and monitoring tool. It allows for screen broadcasting and monitoring, remote command execution, message sending, imposing restrictions like screen locking or sound muting the clients and much more! It can be installed in Ubuntu, Debian and openSUSE based labs that may contain any combination of the following: LTSP servers, thin and fat clients, non LTSP servers, standalone workstations, NX or XDMCP clients etc.

Epoptes has been undermaintained for the last couple of years. It&#39;s currently powered by Python 2 and GTK 2, while unfortunately a number of bugs have crept in due to major updates in Linux distribution packages (systemd, consolekit, VNC…).

This project aims at reviving Epoptes with Python 3 and GTK 3 support, while also addressing several outstanding issues.

## Project goals

I propose to extend the original project goals a bit, so that the following areas are covered:

1. Make Epoptes run properly in Ubuntu 18.04 and in Debian Buster.
2. Rewrite Epoptes with Python 3 support.
3. Use Gtk3 with GObject Introspection instead of pygtk2.
4. Improvements in the code structure (Break existing code into python modules/packages).
5. Make the newer version available for Ubuntu 18.04 in a PPA.

## Implementation

A more detailed description of the project goals follows. Of course any new code will be proposed as a pull request on github.

### Preliminary work

As part of my GSoC proposal, I submitted the following pull requests in github:

- [Convert lock-screen to Python 3 / GTK 3 (issue #45)](https://github.com/Epoptes/epoptes/pull/48): migrating lock-screen to Python 3 / GTK 3 was rather straightforward. I took the opportunity to also add support for HiDPI monitors, giving appropriate sizes for the lock screen icon and text, and to make it work in the absence of a window manager (issue [#47](https://github.com/Epoptes/epoptes/issues/47)), for example in client login screens.
- [Convert screenshot to Python3/Gtk3 (issue #46)](https://github.com/Epoptes/epoptes/pull/49): migrating screenshot to Python 3 / GTK 3 was a bit more challenging. Quite a bit of searching was required to map the old API into the new one, and I also bumped into issues with text encodings on stdout on Python 3, and even internal issues with the padding of the pixmap last line. I made sure the result works fine with the current Epoptes version, and I also did some benchmarking research.

### Make Epoptes run properly in Ubuntu 18.04 and in Debian Stretch

A few significant issues have arisen due to other software updates in Linux distributions:

- [replacement of ifupdown with netplan needs integration for /etc/network/if{up,down}.d scripts](https://bugs.launchpad.net/ubuntu/+source/epoptes/+bug/1718227)
- [packages providing ifupdown scripts must have those scripts fixed if needed](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=661591)
- [improve support for tigervnc](https://github.com/Epoptes/epoptes/issues/22)
- [Epoptes crashes when a user logs off](https://github.com/Epoptes/epoptes/issues/33)
- [Debian epoptes-client packaging: is the dependency on ifup still needed?](https://github.com/Epoptes/epoptes/issues/42)
- [get-display not working on systemd distributions](https://github.com/Epoptes/epoptes/issues/43)

Some of these issues will need to be addressed **before** the Python 3 / GTK 3 migration, so as to be able to run and test the resulting code in a recent development environment.

For example, launching epoptes-client with a systemd unit instead of an if-up script is essential, as modern distributions don&#39;t even run scripts in /etc/network/if-up anymore, i.e. epoptes-client isn&#39;t launched at all on boot.

### Rewrite Epoptes with Python 3 support

Epoptes is currently powered by Python 2, which is to be EOLed in 2020. No recent Linux distribution ships without Python 3 anymore. Hence, backwards compatibility with Python 2 needn&#39;t be a big concern; supporting only Python 3 should be enough.

The Python [2to3](https://docs.python.org/2/library/2to3.html) automatic conversion tool may help a bit in the initial conversion, but of course all its proposed changes will need to be manually reviewed.

The Python 3 migration needs to be implemented in the same step as the Gtk3 migration analyzed below, because there&#39;s no pygtk module in Python 3, and the code needs to be massively updated to use the new GObject Introspection methods. That means that it would be best to split the code base into chunks that can be separately updated; more on this on the timeline section.

### Use Gtk3 with GObject Introspection instead of pygtk2

Epoptes is currently using pygtk2 for its user interface, but that&#39;s deprecated and unmaintained, and bug reports have been filed that may even result in the removal of Epoptes from distributions:

- [epoptes: Depends on unmaintained pygtk](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=885278)

The migration of Epoptes from GTK 2 to 3 though won&#39;t be trivial. It&#39;s using some techniques like client-side image grabbing, for thin-client bandwidth savings, that might not be easily portable. Fortunately, thin clients themselves are getting deprecated upstream in LTSP, so some of those features are not very important anymore.

A plan for the migration would be to start with the standalone parts of epoptes, like the lock-screen code, so as to gain experience and dive into the larger parts later. More on the code base splitting in the timeline section.

The glade .ui files shouldn&#39;t be much of a problem, in many cases a simple GTK version bumping should be enough.

### Improvements in the code structure (Break existing code into python modules/packages)

Restructuring a code base as large as epoptes is no trivial task. It requires a deep familiarity with the code base, so I believe it should be the last one of the project&#39;s programming tasks.

The most obvious part to be restructured is gui.py, which currently counts 1111 lines, and whose core functionality could probably be seperated in a library, while gui.py itself would only contain the knitting between the UI and the various libraries.

### Make the newer version available for Ubuntu 18.04 in a PPA

In order to make the result of this GSoC effort more useful, a new Epoptes version should be released upstream after the end of the GSoC project, and that Epoptes version should then be published in its PPA for its Ubuntu-based users.
