# Normie Linux's release package: the system's name, version and defaults.
# Forked from Fedora's generic-release 45 (MIT licence, see LICENSE), which exists so that remixes can
# replace fedora-release. It keeps what the rest of the system needs from Fedora: the Fedora version
# macros (45 and .fc45), ID_LIKE=fedora, dnf5 defaults, and a requirement on Fedora's repositories and
# service presets.
%global release_name Alpha
%global dist_version 45
%global home_url %{?normie_home_url}%{!?normie_home_url:https://github.com}

Name:           normie-release
Version:        %{dist_version}
Release:        1%{?dist}
Summary:        Normie Linux release files
License:        MIT
BuildArch:      noarch

Provides:       system-release = %{version}-%{release}
Provides:       system-release(%{version})
Provides:       normie-release-identity = %{version}-%{release}

# Only one release package may be installed. These are Fedora's (and the generic remix) ones.
Conflicts:      system-release
Conflicts:      fedora-release
Conflicts:      fedora-release-common
Conflicts:      fedora-release-identity
Conflicts:      generic-release
Conflicts:      generic-release-common

Requires:       fedora-repos(%{dist_version})
Requires:       distribution-systemd-presets
Requires:       redhat-systemd-presets-desktop

%description
Release files for Normie Linux, a beginner-friendly distribution based on Fedora Linux:
/etc/os-release, the version macros, the dnf5 defaults and the login banner.

%prep

%build

%install
install -d %{buildroot}%{_prefix}/lib
sed -e 's|@VERSION_ID@|%{dist_version}|g' \
    -e 's|@RELEASE_NAME@|%{release_name}|g' \
    -e 's|@HOME_URL@|%{home_url}|g' \
    %{_sourcedir}/os-release.in > %{buildroot}%{_prefix}/lib/os-release

echo "Normie Linux release %{dist_version} (%{release_name})" > %{buildroot}%{_prefix}/lib/normie-release
echo "cpe:/o:normielinux:normie:%{dist_version}" > %{buildroot}%{_prefix}/lib/system-release-cpe

install -d %{buildroot}%{_sysconfdir}
ln -s ../usr/lib/os-release %{buildroot}%{_sysconfdir}/os-release
ln -s ../usr/lib/normie-release %{buildroot}%{_sysconfdir}/normie-release
ln -s normie-release %{buildroot}%{_sysconfdir}/system-release
ln -s normie-release %{buildroot}%{_sysconfdir}/redhat-release
ln -s ../usr/lib/system-release-cpe %{buildroot}%{_sysconfdir}/system-release-cpe

install -pm 0644 %{_sourcedir}/issue %{buildroot}%{_prefix}/lib/issue
install -pm 0644 %{_sourcedir}/issue %{buildroot}%{_prefix}/lib/issue.net
ln -s ../usr/lib/issue %{buildroot}%{_sysconfdir}/issue
ln -s ../usr/lib/issue.net %{buildroot}%{_sysconfdir}/issue.net

install -d %{buildroot}%{_rpmconfigdir}/macros.d
sed -e 's|@HOME_URL@|%{home_url}|g' %{_sourcedir}/macros.dist > %{buildroot}%{_rpmconfigdir}/macros.d/macros.dist
chmod 0644 %{buildroot}%{_rpmconfigdir}/macros.d/macros.dist

install -d %{buildroot}%{_datadir}/dnf5/libdnf.conf.d
install -pm 0644 %{_sourcedir}/dnf5-defaults.conf %{buildroot}%{_datadir}/dnf5/libdnf.conf.d/20-defaults.conf
install -d %{buildroot}%{_datadir}/dnf/plugins
install -pm 0644 %{_sourcedir}/copr.vendor.conf %{buildroot}%{_datadir}/dnf/plugins/copr.vendor.conf
install -d %{buildroot}%{_sysconfdir}/dnf/protected.d
install -pm 0644 %{_sourcedir}/protected.conf %{buildroot}%{_sysconfdir}/dnf/protected.d/normie-desktop.conf

mkdir -p licenses
install -pm 0644 %{_sourcedir}/LICENSE licenses/LICENSE

%files
%license licenses/LICENSE
%{_prefix}/lib/os-release
%{_prefix}/lib/normie-release
%{_prefix}/lib/system-release-cpe
%{_sysconfdir}/os-release
%{_sysconfdir}/normie-release
%{_sysconfdir}/system-release
%{_sysconfdir}/redhat-release
%{_sysconfdir}/system-release-cpe
%attr(0644,root,root) %{_prefix}/lib/issue
%attr(0644,root,root) %{_prefix}/lib/issue.net
%config(noreplace) %{_sysconfdir}/issue
%config(noreplace) %{_sysconfdir}/issue.net
%attr(0644,root,root) %{_rpmconfigdir}/macros.d/macros.dist
%dir %{_datadir}/dnf5
%dir %{_datadir}/dnf5/libdnf.conf.d
%{_datadir}/dnf5/libdnf.conf.d/20-defaults.conf
%dir %{_datadir}/dnf
%dir %{_datadir}/dnf/plugins
%{_datadir}/dnf/plugins/copr.vendor.conf
%dir %{_sysconfdir}/dnf
%dir %{_sysconfdir}/dnf/protected.d
%{_sysconfdir}/dnf/protected.d/normie-desktop.conf

%changelog
* Tue Nov 24 2026 Normie Linux contributors <noreply@invalid> - 45-1
- First release package. Forked from generic-release 45-0.4 (MIT), plus the KDE edition's protected package.
