# Use gzip compression to support older distributions
# https://stackoverflow.com/questions/9292243
%define _source_payload w9.gzdio
%define _binary_payload w9.gzdio
%define build_timestamp %(date +"%%Y%%m%%d")
Name:          epoptes
Version:       23.08
Release:       1%{?dist}
Summary:       Computer lab management tool
Summary(el_GR.UTF-8): Λογισμικό διαχείρισης εργαστηρίου υπολογιστών
License:       GPLv3
Group:         Networking/Remote access
Source:        https://github.com/epoptes/epoptes/archive/refs/tags/v%{version}.tar.gz
Url:           https://epoptes.org
BugURL:        https://github.com/epoptes/epoptes/issues
BuildRequires: desktop-file-utils
BuildRequires: intltool
BuildRequires: python3-devel
BuildRequires: python3-distutils-extra
BuildRequires: systemd
BuildRequires: systemd-rpm-macros
Requires:      libfaketime
Requires:      openssl
Requires:      python3-twisted
Requires:      socat
Recommends:    epoptes-client
Recommends:    iperf
Recommends:    python3-gobject-base-noarch
Recommends:    python3-netifaces
Recommends:    screen
Recommends:    tigervnc
Recommends:    x11vnc
Recommends:    xset
Recommends:    xterm
BuildArch:     noarch

%description
Epoptes is an open source computer lab management and monitoring tool. It
allows for screen broadcasting and monitoring, remote command execution,
message sending, imposing restrictions like screen locking or sound muting
the clients and much more!

Contains the server daemon and a GUI for controlling client PCs.

It supports LTSP installations, but it also works without LTSP.

%description -l el_GR.UTF-8
Ο Επόπτης είναι ανοικτό λογισμικό διαχείρισης και εποπτείας εργαστηρίου
υπολογιστών. Επιτρέπει την εκπομπή και την παρακολούθηση της οθόνης, την
απομακρυσμένη εκτέλεση εντολών, την επιβολή περιορισμών όπως το κλείδωμα της
οθόνης ή τη σίγαση του ήχου των σταθμών εργασίας και πολλά περισσότερα!

Περιέχει την υπηρεσία εξυπηρετητή και το γραφικό περιβάλλον για τον έλεγχο των
σταθμών εργασίας.

Υποστηρίζει εγκαταστάσεις με ή χωρίς LTSP.

%package client
Summary:       Computer lab management tool (client)
Summary(el_GR.UTF-8): Λογισμικό διαχείρισης εργαστηρίου υπολογιστών (πελάτης)
Group:         Networking/Remote access
Requires:      iperf
Requires:      openssl
Requires:      screen
Requires:      socat
Recommends:    tigervnc
Recommends:    x11vnc
Recommends:    xset
BuildArch:     noarch

%description client
Epoptes is an open source computer lab management and monitoring tool. It
allows for screen broadcasting and monitoring, remote command execution,
message sending, imposing restrictions like screen locking or sound muting
the clients and much more!

Contains the client daemon and some utilities for getting screenshots etc.

%description client -l el_GR.UTF-8
Ο Επόπτης είναι ανοικτό λογισμικό διαχείρισης και εποπτείας εργαστηρίου
υπολογιστών. Επιτρέπει την εκπομπή και την παρακολούθηση της οθόνης, την
απομακρυσμένη εκτέλεση εντολών, την επιβολή περιορισμών όπως το κλείδωμα της
οθόνης ή τη σίγαση του ήχου των σταθμών εργασίας και πολλά περισσότερα!

Περιέχει την υπηρεσία εξυπηρετητή και γραφικό περιβάλλον για τον έλεγχο των
σταθμών εργασίας.

%prep
%autosetup

%build
# Not necessary

%install
%__python3 setup.py install --root=%{buildroot} --prefix=%{_prefix}
%find_lang %{name}

install -pD -m755 %{_builddir}/%{name}-%{version}/debian/%{name}.postinst %{buildroot}%{_datadir}/%{name}/%{name}.postinst
install -pD -m644 %{_builddir}/%{name}-%{version}/debian/%{name}.service %{buildroot}%{_unitdir}/%{name}.service
mkdir -p %{buildroot}%{_sysconfdir}/firewalld/services/
install -pD -m644 %{_builddir}/%{name}-%{version}/debian/%{name}-firewalld.xml %{buildroot}%{_sysconfdir}/firewalld/services/
sed 's/twistd3/twistd-3/' -i %{buildroot}%{_unitdir}/%{name}.service
sed "s/\(__version__\).*/\1 = '%{version}-%{release}'/" -i %{buildroot}%{python3_sitelib}/epoptes/__init__.py
sed "s/\(VERSION=\).*/\1'%{version}-%{release}'/" -i %{buildroot}%{_sbindir}/epoptes-client
sed '/^#!\/bin\/sh/d' -i %{buildroot}%{_datadir}/%{name}/client-functions
install -pD -m644 %{_builddir}/%{name}-%{version}/debian/%{name}-client.service  %{buildroot}%{_unitdir}/%{name}-client.service
rm -f %{buildroot}/%{_docdir}/%{name}/README.md

%post
%systemd_post %{name}.service
if [ "$1" == 1 ]
then
    # First time install, see
    # https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/#_syntax
    /usr/share/epoptes/epoptes.postinst configure
fi

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun_with_restart %{name}.service

%files -f %{name}.lang
%doc README.md
%{_bindir}/%{name}
%{_datadir}/applications/*
%{_datadir}/icons/*
%{_datadir}/ltsp/
%{_datadir}/%{name}/
%{_mandir}/man1/%{name}.1.*
%{python3_sitelib}/*
%{_unitdir}/%{name}.service
%{_sysconfdir}/firewalld/services/*

%post client
%systemd_post %{name}-client.service

%preun client
%systemd_preun %{name}-client.service

%postun client
%systemd_postun_with_restart %{name}-client.service

%files client
%{_datadir}/%{name}-client/
%{_mandir}/man8/%{name}-client.8.*
%{_sbindir}/%{name}-client
%{_sysconfdir}/xdg/autostart/%{name}-client.desktop
%{_unitdir}/%{name}-client.service

%changelog
* Mon Aug 21 2023 Alkis Georgopoulos <alkisg@gmail.com> 23.08-1
- Merge GSoC 2023 Epoptes Improvements (#204)
- Better GPU information (#201)
- Add processor information for rpi4 (#200)
- Avoid zeroing server.crt certificate (#194)
- Drop /etc/default/epoptes* scripts (#187)
- Apply WoL to all interfaces (#186)
- Support ltsp.conf based global groups (#38)
- Save settings on SIGTERM (#30)
- Firewall friendly port ranges (#11)
- Automatic firewall configuration
- Support more distributions
