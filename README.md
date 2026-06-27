# MikTag

> Automatically identify, tag, organize and sort your music library using Shazam technology.



<p align="center">
  <img src="assets/logo.png" alt="miktag Logo" width="180">
</p>

## About

**MikTag** is an open-source desktop application that automatically organizes your music collection.

Instead of manually renaming files and editing metadata, miktag analyzes each song, identifies it using **Shazam**, retrieves its official information, updates the audio tags, and finally sorts your music into a clean and organized library.

For every recognized track, miktag can automatically:

- Detect the song using Shazam
- Retrieve the official title
- Retrieve the correct artist(s)
- Download the official album artwork
- Update the audio metadata (ID3 tags)
- Rename the music file
- Organize your library into folders automatically

Whether you have hundreds or thousands of unorganized songs, miktag helps you build a clean and properly tagged music collection in just a few clicks.

---

## Powered by ShazamIO

MikTag uses the amazing **ShazamIO** project to identify music.

A huge thank you to the developers and contributors of **ShazamIO** for making this project possible.

⭐ Repository:
https://github.com/shazamio/ShazamIO

Without their incredible work, this application would not exist.

---

## Run in development

```bash
pip install -r requirements.txt
python app.py
```

---

## Build the application

### Windows (.exe + installer)

```bat
build_windows.bat
```

**Requirements**

- Python 3.11+ (64-bit)
- Inno Setup 6 *(optional, for the installer)*

**Output**

- `dist\miktag\miktag.exe`
- `installer\miktag-setup-windows.exe`

---

### macOS (.app + .dmg)

```bash
bash build_macos.sh
```

**Requirements**

- Python 3.11+
- Xcode Command Line Tools
- `create-dmg` *(optional)*

**Output**

- `dist/miktag.app`
- `installer/miktag-macos.dmg`

---

### Linux (Binary + .deb)

```bash
bash build_linux.sh
```

**Requirements**

```bash
sudo apt install libgtk-3-dev dpkg fakeroot
```

**Output**

- `dist/miktag/miktag`
- `installer/miktag_1.0.0_amd64.deb`



---

## Supported audio formats

- MP3
- FLAC
- M4A
- AAC
- OGG
- WAV

---

## Credits

This project would not be possible without the following open-source projects:

- **ShazamIO** — Music recognition
  https://github.com/shazamio/ShazamIO
