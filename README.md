# Slay the Spire AI
This work is built on top of ForgottenArbiter's [spirecomm](https://github.com/ForgottenArbiter/spirecomm) which communicates with Slay the Spire through his [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod).

## Requirements
**This code has only been tested on Windows 10. No guarantees on other OSes.**

* Python 3.5+
    * kivy
    * py_trees
* Slay the Spire
    * [ModTheSpire](https://github.com/kiooeht/ModTheSpire), which I believe you can now get straight from the Steam Community
    * BaseMod
    * CommunicationMod
    * SuperFastMode (recommended, especially the [noux](https://github.com/Skrelpoid/SuperFastMode/releases/tag/noux999.0.0) release)

## Installation

(Optionally, make a new Slay the Spire profile for your bot to separate your statistics and its statistics.)

1. Install all mods by following ModTheSpire's install instructions and similarly copying all mods into the mods folder with their respective jars in your root Slay the Spire directory. (Note: their instructions say the jar should go in the mods folder, I think there's been an update where they go one level up in the root.)
2. Verify that ModTheSpire and mods are installed by running Slay the Spire With Mods (through Steam) or running the ModTheSpire executable. This step is also necessary for CommunicationMod to run first-time setup.
3. Find the CommunicationMod config file in %LOCALAPPDATA%\ModTheSpire\CommunicationMod\config.properties and edit the command to command=python C\:\\ _...path\\to..._ \\spirecomm\\utilities\\simple_gui.py Note the double backslashes in the path!
4. Run `python setup.py install` from the root directory of spirecomm. Note that when you make changes to the AI, you will need to run this install command again. You'll probably want to set runAtGameStart=true, otherwise to start the AI you'll need to click Mods > CommunicationMod > Run process to start the AI after loading up Slay the Spire.

Optionally, if you installed SuperFastMode, find its config file in %LOCALAPPDATA%\ModTheSpire\SuperFastMode and set the  deltaMultiplier to 10.

If everything was installed correctly, when you run Slay the Spire with the mods on, the AI will begin playing.
