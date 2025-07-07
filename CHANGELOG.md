# Changelog

All notable changes to GestureSesh will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- New features in development

### Changed

- Improvements in progress

### Fixed

- Bug fixes in development


## v0.5.0 - 2025-07-05

### Added

* macOS support with unified **Fusion** style and dedicated build scripts.
* Recursive folder scanning when adding directories.
* **Skip current image** feature with hotkey (`S`). *Thanks to @TNychka for the [implementation!](https://github.com/adnv3k/GestureSesh/pull/18)*
* Review mode with 15‑second auto‑close and `Ctrl+O` to open the image's folder.
* Dragging an image now pauses the timer while it is dragged.
* **DotIndicator** widget for visual progress with customizable themes and animations.
* Dynamic font scaling and richer tooltips.
* Double‑click any image to open its containing directory with the image highlighted.
* Improved session display capabilities.
* Automated build process with code‑signing and notarization.
* Comprehensive codebase audit for import and path correctness
* Enhanced DMG build process with improved CI compatibility

### Changed

* Renamed project from **Image Queuer** to **GestureSesh**.
* Optimized rendering performance and UI responsiveness.
* Enhanced cross‑platform compatibility (Windows & macOS).
* Updated README with cross‑platform installation steps.
* Requirements trimmed and reorganized; Python dependencies updated for stability.
* Improved build script robustness for automated CI/CD workflows
* Optimized DMG window layout and icon positioning for consistent appearance

### Fixed

* Resolved memory leaks in long sessions.
* Fixed display issues on high‑DPI screens.
* Corrected timing accuracy in session tracking.
* Improved duplicate detection and directory handling.
* Various UI and status‑message refinements.
* Ensured all file imports and path references are correct after directory reorganization
* Improved DMG creation reliability across different macOS versions and environments

### Technical

* Refactored codebase for clarity and modularity; added comprehensive tests.
* Implemented full CI/CD with GitHub Actions (build ➜ sign ➜ notarize ➜ release).
* Hardened runtime & automated signing for macOS binaries.
* Updated documentation and developer setup instructions.

> [!NOTE]
> **Antivirus False Positives:** Some antivirus programs (including Avast and AVG) may flag GestureSesh as potentially harmful due to how PyInstaller packages Python applications. As @4Sol has [pointed out in Issue #13](https://github.com/adnv3k/GestureSesh/issues/13), this is a **false positive** - GestureSesh is completely safe.
>
> **Why this happens:**
> - PyInstaller bundles Python and libraries into a single executable
> - Some malware also uses PyInstaller, causing pattern-matching false positives
> - This affects many legitimate Python applications, not just GestureSesh
>
> **What you can do:**
> - **Download only from official sources:** GitHub releases or the official website
> - **Verify file integrity:** Check the SHA256 checksums provided with each release
> - **Add to antivirus exceptions:** If your antivirus blocks it, add GestureSesh to your whitelist
> - **Build from source:** Advanced users can compile from the source code themselves
>
> The macOS version is Apple-notarized and doesn't have this issue.


## v0.4.2 Mute and update fix — v0.4.2 — 2021-10-14

**EDIT** edited file names in directory to reflect new name.
**EDIT** file names to reflect name change.


Minor
Mute now works properly.
Display now shows "Up to date." if the version was compared to the newest version available, and will only check once per day.
Version removed from window title.

If you have any suggestions or issues, I'd love to hear about them!
adnv3k@gmail.com

---

## v0.4.1 Frameless window, autocomplete preset names, and major bug fixes — v0.4.1 — 2021-10-08

Major
Autocomplete preset names
Frameless window with Ctrl + F
-resizing with mouse is not enabled when frameless window is toggled.
Move window by clicking anywhere on the window and dragging.

Fixes
Scheduling functions now work properly.
Minor bug fixes for speed and function.

If you have any suggestions or issues, I'd love to hear about them! adnv3k@gmail.com

---

## v0.3.8 - Resizing and scheduler fixes  — v0.3.8 — 2021-09-30

Minor update
Resizing the session window without toggling the resizing (hotkey: R), no longer causes a crash. 
Scheduling no longer incorrectly counts total images after closing the session window, and starting a new session. 
File size reduced.

If you have any suggestions or issues, I'd love to hear about them! adnv3k@gmail.com

---

## v0.3.7 - Audio cues, file path, 32bit, bug fixes — v0.3.7 — 2021-09-10

Minor update
Audio cues added!
Different sounds will be played for:
Total time reaching the halfway point
Timer reaching 10/5/0 seconds
Start of a new entry
Last image of an entry
New image being displayed
*toggle mute by pressing "M"

Image path now set as window title temporarily
32bit compatibility added

Hotkey changes:
Add Entry changed from "Enter" to "Shift + Enter"
Added "Delete" hotkey for delete entry
"M" added to mute audio cues
Bug fixes:
Entry column no longer editable
Error notice for letters in schedule items
"Enter" key now be accessible for schedule item edits

What's to come: 
Skip button that displays the next image without reducing the
amount of images scheduled
Frameless session window
New way to interact with buttons
Item selection per entry
Still working on better customization for entries
Still looking out for better compression methods to decrease file size for future updates!

If you have any suggestions or issues, I'd love to hear about them! adnv3k@gmail.com

---

## v0.3.6 - Always on top, Flip vertical, end of session notice — v0.3.6 — 2021-08-17

Minor update
Mostly minor quality of life updates
Added flip vertical. Hotkey set to V
Added always on top. Hotkey set to A
Changed flip horizontal hotkey from F to H
Removed timer buttons. Hotkeys remain the same. Minimum size for the session window is now smaller as a result.
Added notification for end of session. The session window will now close after 5 seconds.

Added processor type for future updating

Reminders:
Pressing R will toggle window resizing. So, if you would like to have your session window full screen, press R.
Hotkeys are updated in the readme!
Saving folders is possible by dragging and dropping folders to the left side in the folder selection window.

Things to look at for:
Audio feedback (also, mute) for when the timer ends.
UI tweaks
Skip button for sessions
Folder presets
32bit compatibility (Still working out some kinks)
Of course, better customization for entries coming soon!
Still researching better compression methods to decrease file size for future updates!

If you have any suggestions or issues, I'd love to hear about them! adnv3k@gmail.com

---

## v0.3.5 - Grayscale, Dynamic resizing, Flip horizontal, bug fixes — v0.3.5 — 2021-08-05

v0.3.5
Grayscale - geared for visibility. Shortcut G
Dynamic window resizing to remove borders when displaying images. Shortcut R to toggle between a static window and a dynamic one.
Flip horizontal - Flips image horizontally. Shortcut F 

Some minor quality of life improvements:
Main window raises to the front after session is closed
The break light turns on when there is 10 seconds or left on the clock
Reformatted timer display to show only relevant measures of time
Reformatted Entry/Image positions to just numbers and spacing
Revised spacing to reduce minimum window size. 
Recolored session buttons with a more muted color to be less distracting
Fixed jpeg not adding
Checking for updates no longer causes crashes

Things to look at for
UI tweaks
Skip button for sessions
Audio feedback (also, mute)
Window always on top
32bit compatibility
Of course, better customization for entries coming soon!
Adding numpy and cv2 for image processing greatly increases the folder size. However, the exe remains compact. I'll be looking in to other compression methods for future updates!

If you have any suggestions or issues, I'd love to hear about them! adnv3k@gmail.com

---

## Image Queuer v0.3.4 - Contrast, hotkeys, bugfix — v0.3.4 — 2021-07-23

Contrast on buttons now WCAG AAA 
New hotkeys added: Ctrl+Enter: start session, Esc: close window, Enter: add entry, F: open files... full list in the README
Randomization will now be handled as a toggle, and will be loaded up along with the recent session settings
BUGFIX break.png now adequately handled
*update checks now correctly checking for updates
*version correction
Better customization for entries coming soon!
If you have any suggestions or issues, I'd love to hear them! adnv3k@gmail.com

---

## Image Queuer v0.3.3 - minor update — v0.3.3 — 2021-07-20

*reuploaded! 
*fixed bug that would cause a crash when selecting folders
Minor update
Update notices will now be displayed. 
Bug fixes
Timer no longer cut off when resizing the session window.
Missing files will now be removed from the selection, and will need to be re-added.
Total now displays properly on start.


Better customization for entries coming soon!
If you have any suggestions or issues, I'd love to hear them! adnv3k@gmail.com

---

## Image Queuer v0.3.2 - minor update - quickfix! — v0.3.2 — 2021-07-13

v0.3.2
Minor updates
Number of Images box now accepts 999999999 max images (if needed, double click the item in the table to edit the number to one greater than 999999999)
Display text for recent load now reflects that a recent profile was loaded
Total images and duration now shown
Fixed file extension bug
Reformatted time display to include hours
Fixed selection bug when removing last entry
Some tooltips revised
*quickfix total wasn't showing the right total
*quickfix either move entry button would cause a crash when no entry was selected

More features coming soon! 
If you have any suggestions or issues, I'd love to hear them! adnv3k@gmail.com

---

## Image Queuer - minor fix — v0.3.1 — 2021-07-05

Changed texts to reflect added multi-folder selection functionality.

---

## Image Queuer - update + fixes — v0.3.0 — 2021-07-05

Added multi-folder selection

Minor bug fixes

Will be including a folder with dependencies, along with a single exe with every release

---

## v0.2 Image Queuer - minor fixes — v0.2 — 2021-07-02

Bug fixes:
Removing row when sorted by any column other than Entry now displays the correct Entry numbers.

Fixed button icons.

---

## Image Queuer — v0.1 — 2021-07-02

Initial Release.

---


