# torus-XM-ripper
A Python-based tool for ripping GBA games made by Torus Games to XM

Please note that a few of their games won't work because they use a different sound driver. Don't make issues if a game throws the DPAK file error.

## Currently tested games
- Backyard Football (perfect?)
- Backyard Football 2006/2007 (perfect?)
- Cabella's Big Game Hunter (accuracy is unknown, but it converts)
- Curious George (perfect?)
- Dead to Rights (accuracy is unknown, but it converts)
- Duke Nukem Advance (accuracy is unknown, but it converts)
- Fantastic 4 (accuracy is unknown, but it converts)
- Fantastic 4: Flame On (perfect?)
- Gumby Vs. the Astrobots (perfect?)
- Ice Nine (accuracy is unknown, but it converts)
- Marvel's The Invincible Iron Man (perfect?)
- Minority Report (accuracy is unknown, but it converts)
- Pitfall: The Lost Expedition (perfect?)
- Shrek Smash n' Crash Racing (perfect?)
- Spider-Man: Battle for New York (perfect?) (requires you to extract the MUSC section and put it into a DPAK file first)
- Sportsman's Pack: Cabela's Big Game Hunter + Rapala Pro Fishing (perfect?)

### Completely broken
- Space Invaders (a MUSC section is found and something gets decoded, but the audio is a broken mess)

### Games that use a different sound driver entirely
- Doom II
- Jackie Chan Adventures (GAX)
- Planet of the Apes (GAX)

## Usage instructions
- Run the script 
- Select your ROM file

In the same folder as the ROM you ran it on, there should now be a folder that has XM files in it.

## How to use the output XM files
Playing XM files can be done with the following programs:
- Foobar2000 with either the ZXTune plugin or the OpenMPT Module Decoder plugin
- OpenMPT (you can also edit them with this)

## Usage rights
Feel free to use any part of this tool (minus the output XM files, as they're copyrighted) in almost any project you'd like.

My only request is that you do not charge people for it.
