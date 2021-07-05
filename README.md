# Image Queuer
A free tool intended to help artists practice gesture/figure drawing with their own pictures. The tool itself is a GUI app that displays image files based on a user defined schedule. A session will display images, while maintaining their original aspect ratio, according to the schedule with image navigation that maintains its respective schedule configuration. 

# Usage
No installation needed. Either zip in Releases includes a standalone exe. 

## Hotkeys
### Navigation Bar: 
Button | Hotkey
------------ | -------------
Previous Image | Left Arrow Key
Stop | Esc 
Pause | Spacebar
Next Image | Right Arrow Key
#### Pressing Stop closes the window, and ends the session.

# About
Current supported file types: .bmp, .jpg, .jpeg, .png. Settings are stored using the shelve module, and are saved in the folders 'presets' and 'recent' as .bak, .dat, and .dir files. These folders are saved in the same directory as Image Queuer.exe. The most recent images and schedule used will be automatically loaded when reopening Image Queuer.exe. 

GUI created using PyQt5. 
