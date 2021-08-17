# Image Queuer
A free tool intended to help artists practice gesture/figure drawing with their own pictures. The tool itself is a GUI app that displays image files based on a user defined schedule. A session will display images, while maintaining their original aspect ratio, according to the schedule with image navigation that maintains its respective schedule configuration. 

# Usage
No installation needed. Either zip in Releases includes a standalone exe. 

## Hotkeys
### Session Configuration:
Button | Hotkey
------------ | -------------
Open Folders | F
Open Files | Ctrl + F
Clear Selection | Ctrl + C
Toggle Randomization | Ctrl + R
Remove Duplicates | Ctrl + 1 (only 1 of a kind)
Add Entry | Enter
Save Preset | Ctrl + S
Delete Preset | Ctrl + Shift + D
Delete Entry | D
Move Entry Up | W
Move Entry Down | S
Clear Schedule | C
Start Session | Ctrl + Enter
Close Window | Escape

### Navigation Bar: 
Button | Hotkey
------------ | -------------
Grayscale | G
Flip Horizontal | H
Flip Vertical | V
Toggle Resizing (dynamic/static) | R
Toggle Always On Top | A
Previous Image | Left Arrow Key
Stop | Esc 
Pause | Spacebar
Next Image | Right Arrow Key
Add 30s | Up Arrow Key
Add 1 Minute | Ctrl + Up Arrow Key
Reset timer | Ctrl + Shift + Up Arrow Key
#### Pressing Stop closes the window, and ends the session.

# Note
Current supported file types: .bmp, .jpg, .jpeg, .png. Settings are stored using the shelve module, and are saved in the folders 'presets' and 'recent' as .bak, .dat, and .dir files. These folders are saved in the same directory as Image Queuer.exe. The most recent images, randomization setting, and schedule used will be automatically loaded when reopening Image Queuer.exe. 

Updates are checked every 3 days, and a notice of available update will be displayed if there is one.

GUI created using PyQt5

# Contact
If you have any suggestions or issues, any input is appreciated!

Email: adnv3k@gmail.com

Any support is appreciated!

https://www.paypal.com/donate?hosted_button_id=TL97W8RXVNARC
