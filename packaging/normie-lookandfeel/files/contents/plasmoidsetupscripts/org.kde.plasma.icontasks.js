/*
   Pin the things a new user looks for first on the taskbar, including Update & Repair.
   Same licence as the rest of this package (GPL-2.0-or-later).
*/

applet.currentConfigGroup = ["General"]
applet.writeConfig("launchers", ["applications:org.kde.discover.desktop",
                                 "applications:org.kde.dolphin.desktop",
                                 "preferred://browser",
                                 "applications:normie-update.desktop"]);
