# Changelog

All notable changes to GestureSesh will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.5.5 - 2026-05-25

### Fixed

- JPEG XL (`.jxl`) images now display during sessions. Pillow has no built-in JXL support, so the `pillow-jxl-plugin` dependency was added and registered, removing the reliance on an external `djxl` executable.
- Manage Order / Selection Order Viewer previews now render `.avif` and `.jxl` files. When Qt lacks a plugin for the format, the preview falls back to decoding via Pillow.
- Closing the Shortcut Map or Manage Order dialogs now destroys them instead of leaving hidden window instances parented to the session, which had been accumulating in the Windows taskbar thumbnail preview.

### Changed

- Improved Shortcut Map readability with higher-contrast text and explicit row, header, and selection colors.

## v0.5.4 - 2026-04-24

### Added

- Session display preferences now persist between runs, including zoom/inspect toggles, grayscale mode, resize/fill behavior, frameless, and always-on-top settings.
- Image modification state now persists across sessions (`hflip`, `vflip`, brightness, contrast, threshold, edge mode), so your display adjustments are restored on next launch.
- Broader image-format support in selection and session playback: `.avif`, `.gif`, `.jxl`, and `.webp` were added to supported types.
- New **Selection Order Viewer** (`Ctrl+Shift+I`) for curation workflows:
  - thumbnail list with selection order, filename, path, and status markers
  - detail preview panel with image metadata
  - selection stats for scheduled/extra/short images, folders, missing files, duplicates, and file types
  - filter by name/path
  - add files/folders
  - remove selected/missing entries
  - move selected items up/down/top/bottom
  - shuffle or sort by filename/path
  - duplicate highlighting toggle
  - open containing folder
- New in-session order viewer access (`Ctrl+Shift+I`) for inspecting the live session order and editing upcoming images while already-shown items and break markers remain locked.
- Randomized selections can now be previewed in their effective order; applying that preview locks the order and disables additional randomization for the next session start.
- New **Shortcut Map** dialog (`F1` / `Ctrl+/`) available in the session window for quick access to keyboard, wheel, trackpad, and stylus controls.
- New zoom and inspection controls in the session window:
  - zoom enable toggle (`Z`)
  - reset zoom (`0`)
  - quick inspect toggle (`I`)
  - auto-reset zoom (`Ctrl+Shift+Z`)
- New frameless fullscreen toggle (`Ctrl+Shift+F`) for distraction-free sessions.
- New touch/pen zoom-panning paths:
  - cursor-aware mouse-wheel zoom
  - trackpad pinch/native gesture zoom
  - stylus drag panning and `Ctrl+stylus` zoom adjustment
- Added image decode fallbacks and animation decode support:
  - `cv2`/Pillow/`djxl` still decode fallback chain
  - Pillow-first animated decode with optional `ffmpeg` fallback
  - decode caching for still and animated sources

### Changed

- Presets now use a wrapped payload format (`schedule` + optional `session_settings`) while remaining backward-compatible with legacy preset entries.
- Preset snapshots can now include linked selection data (files and folders); loading such a preset restores the associated image set where possible.
- Active preset resize behavior (`toggle_resize_status`) is now preserved with each preset and reused at session startup.
- Refactored the app structure for maintainability:
  - extracted session runtime out of `main.py` into `session_window.py`
  - split main-window logic into app-layer modules (`selection`, `status`, `presets`, `session`, plus shared models)
- Refactored the session runtime further so image decode/render logic now lives in a dedicated loader mixin instead of `session_window.py`, and shortcut registration is centralized in `SessionShortcutsMixin`.
- Reworked status messaging into a queued system with dedupe behavior and richer fade/blink rendering.
- Session startup now builds randomized and break-inserted playlists from copies, so the saved selection order is no longer mutated just by starting a session.
- Session controls were simplified for a cleaner display:
  - removed queue-preview feature and its toggle/shortcut
  - removed session top-bar total-count wording/label
- Updated main-window selection placeholder text to reflect the expanded supported image types.

### Fixed

- Improved always-on-top reliability on X11 by applying and clearing `X11BypassWindowManagerHint` with the topmost toggle lifecycle.
- Prevented config-save failures by normalizing recent-session folder/file selections to JSON-safe list values.
- Recent-session restore now reloads both selected folders and directly-added files, with de-duplication and break-placeholder filtering.
- Fixed duplicate detection and duplicate reporting for file additions with more robust file identity handling.
- Improved review-mode and break synchronization behavior across playlist navigation:
  - better alignment between scheduled entries and current playlist position
  - safer end-of-session anchoring to scheduled span
- Improved decode robustness for high bit-depth and mixed-source images via normalization before render.
- Improved selection viewer responsiveness by loading only visible thumbnails plus a small scroll buffer, using scaled image reads instead of decoding every selected image during dialog startup.
- Preserved import and patch compatibility during refactor (`MainApp`, `SessionDisplay`, `BREAK_IMAGE_PATH`, `ScheduleEntry`, and `save_config` patch points).

### Technical

- Expanded modularization by splitting `SessionDisplay` behavior into focused session mixins (`image_mods`, `image_loader`, `shortcuts`, `timer`, `zoom_pan`) and moving utility helpers to `gesturesesh.utils`.
- Added and expanded automated coverage for:
  - decode fallbacks and dtype normalization
  - animation decode decisions and cache behavior
  - extracted loader-path cache reuse behavior
  - zoom pacing/snap behavior
  - break/review-mode schedule synchronization
  - preset-linked selection persistence and backward compatibility
  - duplicate detection/reporting paths
  - selection order helper behavior, shortcut registration, and order-dialog mutation rules

## v0.5.2 - 2026-04-23

### Fixed

- Prevent infinite loop when break images are encountered during session playback — introduced `BREAK_IMAGE_PATH` constant, fixed break insertion/removal indexing, clamped negative item counters, and added `_last_scheduled_playlist_index` / `_sync_entry_to_playlist_position` helpers. Closes #28.

### Changed

- Decomposed the ~1,200-line `src/gesturesesh/main.py` monolith into focused modules composed via mixins:
  - `app/models.py` — `ScheduleEntry`, `StatusMessage` dataclasses
  - `app/file_dialog.py` — file dialog helpers
  - `app/presets.py` — `MainAppPresetsMixin`
  - `app/selection.py` — `MainAppSelectionMixin`
  - `app/session.py` — `MainAppSessionMixin`
  - `app/status.py` — `MainAppStatusMixin`
  - `session_window.py` — `SessionDisplay`, `BREAK_IMAGE_PATH`, `SUPPORTED_IMAGE_TYPES`
  - `ui/dialogs.py` — standalone dialog widgets
- `main.py` is now a thin composition root; all behaviour is preserved with no functional changes.
- Updated image-selection placeholder text to reflect the full set of supported formats.


## v0.5.1 - 2025-07-31

### Fixed

* Fixed directory opening functionality - Ctrl+O hotkey and double-click now properly open file explorer/finder to the correct image location with file highlighted
* Improved path resolution using Path.resolve() for consistent cross-platform behavior
* No new features or breaking changes were introduced; this update solely addresses the directory opening bug introduced in v0.5.0.

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
