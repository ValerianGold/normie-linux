/*
   Use the Normie Linux logo (the system "start-here" icon) on the Start button, and pin the
   things a new user looks for first. Based on the setup script KDE distributions use for this;
   same licence (GPL-2.0-or-later).
*/

applet.currentConfigGroup = ["General"]

if ( applet.readConfig("icon", "start-here-kde") == "start-here-kde" ) {
  applet.writeConfig("icon", "start-here");
}

// Pinned in the Start menu: browser, files, settings, software, and the one-button Update & Repair.
// (If this list is ever ignored by a newer Plasma, the Update & Repair icon on the desktop still works.)
applet.writeConfig("favorites", "preferred://browser,org.kde.dolphin.desktop,systemsettings.desktop,org.kde.discover.desktop,normie-update.desktop");
