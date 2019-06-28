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
3. Find the CommunicationMod config file in %LOCALAPPDATA%\ModTheSpire\CommunicationMod\config.properties and edit the command to command=python C\\:\\\\ _...path\\\\to..._ \\\\spirecomm\\\\utilities\\\\simple_gui.py Note the double backslashes in the path!
4. Run `python setup.py install` from the root directory of spirecomm. Note that when you make changes to the AI, you will need to run this install command again *and* restart the game. You'll probably want to set runAtGameStart=true, otherwise to start the AI you'll need to click Mods > CommunicationMod > Run process to start the AI after loading up Slay the Spire.
5. Open `spirecomm/config.py` and set `SPIRECOMM_PATH` to the correct path to your repository. This enables the AI to load in its data on specific cards and monsters from `ai/cards` and `ai/monsters` respectively. Note that if you plan on pushing changes to the repository, you should call `git update-index --assume-unchanged spirecomm/config.py` so that you don't push your path to the repo.

As a test, you can now run `python utilities/simple_gui.py` from your terminal and the Kivy window should load.

Optionally, if you installed SuperFastMode, find its config file in %LOCALAPPDATA%\ModTheSpire\SuperFastMode and set the  deltaMultiplier to 10.

If everything was installed correctly, when you run Slay the Spire with the mods on, the AI will begin playing.


## Troubleshooting
Because CommunicationMod eats all print statements when the program is running, debugging the AI can sometimes be non-intuitive. For this reason, four error log files are used for assistance with debugging.
1. ai.log: This is the primary output file for any messages from the AI agent
2. ai_comm.log: This is a mostly deprecated output file for any messages from the script which coordinates the AI and CommunicationMod (Coordinator.py)
3. err.log: This is the primary error file for logging compile and runtime errors
4. communication_mod_errors.log: This log file comes from CommunicationMod and is located in the SlayTheSpire directory.
**Note:** When running spirecomm from your terminal, the first three log files will appear in your local repository, but when running spirecomm through ModTheSpire, these files will appear in your SlayTheSpire directory along with communication_mod_errors.log.

### General Troubleshooting Tips
- Check all log files for errors
- Make sure you are using Python 3
- Make sure you have installed kivy and py_trees
- Make sure you never call print() in any code changes you've made to the AI
- If running through ModTheSpire, check the ModTheSpire output for clues
- If you made changes and you're not seeing them, did you re-run `python setup.py install` and restart Slay the Spire with mods? If you added files, you may also need to run `python setup.py build` before these steps.

#### Kivy window won't open
Symptoms: when running `python utilities/simple_gui.py` from the terminal, it prints ready but doesn't open a Kivy window

- Make sure that you are using Python 3 and check the log files for errors.
- Try running the Kivy test provided in the kivy_test folder.
