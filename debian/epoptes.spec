Name:          epoptes
Version:       main
Release:       1

Summary:       Computer lab management tool
Summary(el_GR.UTF-8): Λογισμικό διαχείρισης εργαστηρίου υπολογιστών
License:       GPLv3
Group:         Networking/Remote access
Url:           https://epoptes.org

Source:        https://github.com/eltoukos/epoptes/archive/refs/heads/main.tar.gz

BuildRequires: desktop-file-utils
BuildRequires: intltool
BuildRequires: python3-devel
BuildRequires: python3-distutils-extra
BuildRequires: python3-rpm

BuildArch:     noarch

Requires:      libfaketime
Requires:      python3-gobject-base-noarch
Requires:      python3-twisted
Requires:      socat
Requires:      x11vnc

%description
Epoptes is an open source computer lab management and monitoring tool. It
allows for screen broadcasting and monitoring, remote command execution,
message sending, imposing restrictions like screen locking or sound muting the
clients and much more!

%description -l el_GR.UTF-8
Ο Επόπτης είναι ανοικτό λογισμικό διαχείρισης και εποπτείας εργαστηρίου
υπολογιστών. Επιτρέπει την εκπομπή και την παρακολούθηση της οθόνης, την
απομακρυσμένη εκτέλεση εντολών, το κλείδωμα της οθόνης ή τη σίγαση του ήχου,
και πολλά περισσότερα!

%package client
Summary:       Epoptes client
Summary(el_GR.UTF-8): Υπηρεσία πελάτη του Επόπτη
Group:         Networking/Remote access
BuildArch:     noarch
Requires:      socat
Requires:      x11vnc

%description client
The client part of Epoptes Computer lab management tool.

%description client -l el_GR.UTF-8
Υπηρεσία πελάτη του λογισμικού διαχείρισης εργαστηρίων Επόπτης.

%prep
%setup -q -n %{name}-%{version}

%build
#nothing to build here

%install
%__python3 setup.py install --root=%{buildroot} --prefix=%{_prefix}
%find_lang %{name}

install -pD -m644 %{_builddir}/%{name}-%{version}/debian/%{name}.service  %{buildroot}%{_unitdir}/%{name}.service
install -pD -m644 %{_builddir}/%{name}-%{version}/debian/%{name}-client.service  %{buildroot}%{_unitdir}/%{name}-client.service
rm -f %{buildroot}/%{_docdir}/%{name}/README.md

%pre
getent group epoptes >/dev/null || groupadd -f -r epoptes

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

%files client
%{_sysconfdir}/xdg/autostart/%{name}-client.desktop
%{_unitdir}/%{name}-client.service
%_sbindir/%{name}-client
%{_datadir}/%{name}-client/
%{_mandir}/man8/%{name}-client.8.*

%changelog
* Sat Jun 10 2023 Myrto Georgopoulou <myrto.georgopoulou@gmail.com> 23.01-1
- Initial build
