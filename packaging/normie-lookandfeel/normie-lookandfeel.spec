# Normie Linux's default Plasma look: dark Breeze, our wallpaper, our logo on the Start button, and
# Update & Repair pinned in the Start menu. Based on the small, GPL-2.0-or-later look-and-feel package
# that KDE distributions ship for this; contains no Fedora artwork.
Name:           normie-lookandfeel
Version:        0.1
Release:        1%{?dist}
Summary:        Normie Linux default Plasma look and feel
License:        GPL-2.0-or-later
BuildArch:      noarch

Provides:       plasma-lookandfeel-fedora = %{version}-%{release}
Requires:       plasma-workspace
Requires:       normie-logos
Requires:       normie-backgrounds-kde

%description
The default Plasma look-and-feel for Normie Linux (id org.normielinux.normie.desktop). It selects the
dark Breeze style, the Normie wallpaper and the Normie logo on the Start button.

%prep

%build

%install
L=%{buildroot}%{_datadir}/plasma/look-and-feel/org.normielinux.normie.desktop
install -d $L/contents/layouts $L/contents/plasmoidsetupscripts $L/contents/previews
install -pm 0644 %{_sourcedir}/files/metadata.json $L/metadata.json
install -pm 0644 %{_sourcedir}/files/contents/defaults $L/contents/defaults
install -pm 0644 %{_sourcedir}/files/contents/layouts/org.kde.plasma.desktop-layout.js $L/contents/layouts/
for s in kickoff kicker kickerdash; do
    install -pm 0644 %{_sourcedir}/files/contents/plasmoidsetupscripts/org.kde.plasma.$s.js $L/contents/plasmoidsetupscripts/
done
install -pm 0644 %{_sourcedir}/files/previews/preview.png $L/contents/previews/preview.png
install -pm 0644 %{_sourcedir}/files/previews/fullscreenpreview.jpg $L/contents/previews/fullscreenpreview.jpg

%files
%{_datadir}/plasma/look-and-feel/org.normielinux.normie.desktop

%changelog
* Tue Nov 24 2026 Normie Linux contributors <noreply@invalid> - 0.1-1
- First release.
