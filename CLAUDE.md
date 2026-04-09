# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation
```bash
pip install -e .
```

### Execution
- **GUI Mode**: `audio-extractor --ui`
- **CLI Mode**: `audio-extractor "URL"`
- **CLI with Format**: `audio-extractor "URL" --format mp3`

### Dependencies
- Requires `ffmpeg` installed on the system.
- Python dependencies are managed in `pyproject.toml`.

## Architecture & Structure

### Overview
The project is a high-quality audio downloader supporting 1000+ sites, providing both a graphical user interface and a command-line interface.

### Core Components
- **`audio_extractor.py`**: The main entry point and core logic. It handles:
    - CLI argument parsing.
    - GUI implementation.
    - Integration with `yt-dlp` for downloading.
    - Metadata handling via `mutagen`.
    - Configuration management via `python-dotenv` and a JSON settings file.

### Configuration
- **Environment Variables**: Uses `.env` for defaults (`FORMAT`, `OUTPUT_FOLDER`).
- **User Settings**: Persistent settings are stored at `~/.config/audio_extractor/settings.json`.

### External Dependencies
- **yt-dlp**: The engine used for extracting and downloading audio.
- **mutagen**: Used for audio metadata/tagging.
- **Pillow**: Used for image processing (likely for album art).
- **ffmpeg**: External system dependency for audio conversion and extraction.
