# Normie Linux's logos: the start-menu button, system icon, installer and boot artwork.
# Our own artwork only (branding/normie-logo.svg); nothing here comes from Fedora.
# It takes the place of fedora-logos / generic-logos and provides the same capabilities.
Name:           normie-logos
Version:        0.1
Release:        1%{?dist}
Summary:        Normie Linux icons and artwork
License:        GPL-3.0-or-later
BuildArch:      noarch

Provides:       system-logos = %{version}-%{release}
Provides:       redhat-logos = %{version}-%{release}
Conflicts:      fedora-logos
Conflicts:      generic-logos

%description
The Normie Linux logo as the system icon, the Start-menu button (start-here), the installer artwork
and the boot-splash watermark. The artwork is original to this project.

%prep

%build

%install
F=%{_sourcedir}/files
ICONS=%{buildroot}%{_datadir}/icons/hicolor

install -d $ICONS/scalable/apps $ICONS/scalable/places
install -pm 0644 $F/normie-logo-icon.svg $ICONS/scalable/apps/normie-logo-icon.svg
for name in start-here kmenu gnome-main-menu icon-panel-menu; do
    ln -s normie-logo-icon.svg $ICONS/scalable/apps/$name.svg
done
ln -s ../apps/start-here.svg $ICONS/scalable/places/start-here.svg
# the installer's launcher icon. Anaconda names it this way; the name is not ours to change
ln -s normie-logo-icon.svg $ICONS/scalable/apps/org.fedoraproject.AnacondaInstaller.svg

for size in 16 22 24 32 36 48 64 96 128 256; do
    install -d $ICONS/${size}x${size}/apps $ICONS/${size}x${size}/places
    install -pm 0644 $F/icons/$size.png $ICONS/${size}x${size}/apps/normie-logo-icon.png
    ln -s ../apps/normie-logo-icon.png $ICONS/${size}x${size}/places/start-here.png
done

install -d %{buildroot}%{_datadir}/pixmaps/bootloader
install -pm 0644 $F/pixmaps/normie-logo.png %{buildroot}%{_datadir}/pixmaps/normie-logo.png
install -pm 0644 $F/pixmaps/normie-logo-small.png %{buildroot}%{_datadir}/pixmaps/normie-logo-small.png
install -pm 0644 $F/pixmaps/system-logo-white.png %{buildroot}%{_datadir}/pixmaps/system-logo-white.png
install -pm 0644 $F/pixmaps/bootloader/bootlogo_128.png %{buildroot}%{_datadir}/pixmaps/bootloader/bootlogo_128.png
install -pm 0644 $F/pixmaps/bootloader/bootlogo_256.png %{buildroot}%{_datadir}/pixmaps/bootloader/bootlogo_256.png

install -d %{buildroot}%{_datadir}/plymouth/themes/spinner
install -pm 0644 $F/plymouth/watermark.png %{buildroot}%{_datadir}/plymouth/themes/spinner/watermark.png

install -d %{buildroot}%{_datadir}/anaconda/pixmaps %{buildroot}%{_datadir}/anaconda/boot
for img in anaconda_header sidebar-bg sidebar-logo topbar-bg; do
    install -pm 0644 $F/anaconda/$img.png %{buildroot}%{_datadir}/anaconda/pixmaps/$img.png
done
install -pm 0644 $F/anaconda/splash.png %{buildroot}%{_datadir}/anaconda/boot/splash.png
install -pm 0644 $F/anaconda/syslinux-splash.png %{buildroot}%{_datadir}/anaconda/boot/syslinux-splash.png
install -pm 0644 $F/anaconda/syslinux-vesa-splash.png %{buildroot}%{_datadir}/anaconda/boot/syslinux-vesa-splash.png

%files
%{_datadir}/icons/hicolor/*/apps/*
%{_datadir}/icons/hicolor/*/places/*
%{_datadir}/pixmaps/normie-logo.png
%{_datadir}/pixmaps/normie-logo-small.png
%{_datadir}/pixmaps/system-logo-white.png
%dir %{_datadir}/pixmaps/bootloader
%{_datadir}/pixmaps/bootloader/*
%dir %{_datadir}/plymouth/themes/spinner
%{_datadir}/plymouth/themes/spinner/watermark.png
%dir %{_datadir}/anaconda
%dir %{_datadir}/anaconda/pixmaps
%dir %{_datadir}/anaconda/boot
%{_datadir}/anaconda/pixmaps/*
%{_datadir}/anaconda/boot/*

%changelog
* Tue Nov 24 2026 Normie Linux contributors <noreply@invalid> - 0.1-1
- First release: our logo as the system icon, Start button, installer and boot artwork.
