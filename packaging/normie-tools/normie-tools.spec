# Normie Linux's own tools: the Update & Repair window and the scripts behind it, the reminder, the NVIDIA
# driver step, and the service that adds Flathub and RPM Fusion. They used to be copied into the
# ISO as loose files; as a package they reach installed systems through Update & Repair like everything else.
%global tools_version 0.1

Name:           normie-tools
Version:        %{tools_version}
Release:        2%{?dist}
Summary:        Normie Linux Update & Repair tools
License:        GPL-3.0-or-later
BuildArch:      noarch
# everything in this package's folder except the spec, packed by tools/pack-sources.sh
Source0:        normie-tools-sources.tar.gz

Requires:       bash
Requires:       python3
Requires:       python3-pyqt6
Requires:       polkit
Requires:       curl
Requires:       flatpak
Requires:       pciutils
Requires:       mokutil

%description
The Update & Repair application and the scripts it runs as administrator, the "time to update" reminder,
the NVIDIA graphics driver step, and the service that adds the Flathub and RPM Fusion
software sources. Normie Linux's settings for them are in /etc/normie/update.conf.

%prep
%setup -q -c

%build

%install
mkdir -p %{buildroot}
cp -a files/. %{buildroot}/

%files
%dir %{_sysconfdir}/normie
%config(noreplace) %{_sysconfdir}/normie/update.conf
%dir %{_sysconfdir}/skel/Desktop
%config(noreplace) %{_sysconfdir}/skel/Desktop/normie-update.desktop
%{_sysconfdir}/systemd/system/multi-user.target.wants/normie-sources.service
%dir %{_sysconfdir}/systemd/user/timers.target.wants
%{_sysconfdir}/systemd/user/timers.target.wants/normie-remind.timer
%{_prefix}/lib/systemd/system/normie-sources.service
%{_prefix}/lib/systemd/user/normie-remind.service
%{_prefix}/lib/systemd/user/normie-remind.timer
%dir %{_prefix}/libexec/normie
%{_prefix}/libexec/normie/normie-gpu
%{_prefix}/libexec/normie/normie-lib.sh
%{_prefix}/libexec/normie/normie-remind
%{_prefix}/libexec/normie/normie-sources
%{_prefix}/libexec/normie/normie-update
%{_prefix}/libexec/normie/normie-update-gui
%{_datadir}/applications/normie-update.desktop
%{_datadir}/polkit-1/actions/org.normielinux.update.policy

%changelog
* Fri Nov 27 2026 Normie Linux contributors <noreply@invalid> - 0.1-2
- Remove the separate NVIDIA prompt at first login; Update & Repair already sets up the driver in its normal run
* Wed Nov 25 2026 Normie Linux contributors <noreply@invalid> - 0.1-1
- First package of the tools (they were loose files in the ISO before).
