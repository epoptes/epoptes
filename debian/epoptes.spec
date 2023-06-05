%filter_from_requires /^python3(_common)/d
%filter_from_requires /^xfce4-session/d
%filter_from_requires /^\/sbin\/poweroff/d
%filter_from_requires /^\/sbin\/reboot/d

Name:          epoptes
Version:       23.01
Release:       rpm1

Summary:       Computer lab management tool
Summary(el_GR.UTF-8): Λογισμικό διαχείρισης εργαστηρίου υπολογιστών
License:       GPLv3
Group:         Networking/Remote access
Url:           https://epoptes.org

# Source0-url: https://github.com/epoptes/%name/archive/refs/tags/v%version.tar.gz
Source0:       %name-%version.tar

Source1:       %name-server.service
Source2:       %name-client.service

BuildRequires: rpm-build-python3
BuildRequires: python3-module-distutils-extra
BuildRequires: intltool

BuildArch:     noarch

Requires: python3-module-pygobject3-pygtkcompat
Requires: twisted-core-tools
Requires: cert-sh-functions
Requires: python3-module-service_identity
Requires: python3-module-hamcrest

%description
Epoptes is an open source computer lab management and monitoring tool.
It allows for screen broadcasting and monitoring, remote command execution, message sending, imposing restrictions
like screen locking or sound muting the clients and much more!
Visit https://epoptes.org for more information.

%description -l el_GR.UTF-8
Ο Επόπτης είναι ανοικτό λογισμικό διαχείρισης και εποπτείας εργαστηρίου
υπολογιστών. Επιτρέπει την εκπομπή και την παρακολούθηση της οθόνης, την
απομακρυσμένη εκτέλεση εντολών, το κλείδωμα της οθόνης ή τη σίγαση του ήχου,
και πολλά περισσότερα! Επισκεφθείτε το https://epoptes.org για περισσότερες
πληροφορίες.

%package client
Summary:       Epoptes client
Summary(el_GR.UTF-8): Υπηρεσία πελάτη του Επόπτη
Group:         Networking/Remote access
BuildArch:     noarch

%description client
The client part of Epoptes Computer lab management tool.

%description -l el_GR.UTF-8
Υπηρεσία πελάτη του λογισμικού διαχείρισης εργαστηρίων Επόπτης.

%prep
%setup -q -n %name-%version

%build
#nothing to build here

%install
%__python3 setup.py install --root=%buildroot --prefix=%_prefix
%find_lang %name

install -pD -m644 %SOURCE1 %buildroot%_unitdir/%name-server.service
install -pD -m644 %SOURCE2 %buildroot%_unitdir/%name-client.service
rm -f %buildroot/%_docdir/%name/README.md
install -pD -m644 %_builddir/%name-%version/debian/epoptes.default %buildroot%_sysconfdir/%name.conf
install -pD -m644 %_builddir/%name-%version/debian/epoptes-client.default %buildroot%_sysconfdir/%name-client.conf

%pre
getent group epoptes >/dev/null || groupadd -f -r epoptes

%files -f %name.lang
%doc README.md
%config(noreplace) %_sysconfdir/%name.conf
%_unitdir/%name-server.service
%_bindir/%name
%_datadir/%name/
%_datadir/ltsp/
%python3_sitelibdir_noarch/%name/
%python3_sitelibdir_noarch/twisted/
%python3_sitelibdir_noarch/%{name}-%{version}*.egg-info
%_desktopdir/%name.desktop
%_iconsdir/hicolor/*/apps/%name.svg
%_man1dir/*.1*

%files client
%config(noreplace) %_sysconfdir/%name-client.conf
%_sysconfdir/xdg/autostart/%name-client.desktop
%_unitdir/%name-client.service
%_sbindir/%name-client
%_datadir/%name-client/
%_man8dir/*.8*

%changelog
* Sat Jun 10 2023 Myrto Georgopoulou <myrto.georgopoulou@gmail.com> 23.01-rpm1
- Initial build
