/*
   Use the Normie Linux logo (the system "start-here" icon) on the Start button.
   Based on the setup script KDE distributions use for this; same licence (GPL-2.0-or-later).
*/

if ( applet.readConfig("icon", "start-here-kde") == "start-here-kde" ) {
  applet.currentConfigGroup = ["General"]
  applet.writeConfig("icon", "start-here");
}
