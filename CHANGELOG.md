# Changelog

All notable changes to this project will be documented in this file.

## [1.0.2] - 2025-11-30

### Added

- **Auto-Updater**: Integrated client-side auto-update mechanism. Users can now check for updates directly from the Settings page.
- **Settings Persistence**: Migrated settings storage from `localStorage` to a robust file-based system (`settings.json`) using `tauri-plugin-store`.
- **Crash Logging**: Added local crash logging to help diagnose issues.
- **Update UI**: Added a "Check for Updates" button in the **Settings > About** section.

### Improved

- **Reliability**: Settings are now saved asynchronously and are less prone to being cleared by browser cache clearing.

## [1.0.1] - 2025-11-29

### Added

- **Smart Analysis**: Automatically detects audio content type (Music, Podcast, Voice-over) and suggests optimal presets.
- **Waveform Preview**: Integrated, embedded audio player within file cards for quick preview without layout shifts.
- **Native Integration**: Added file associations to open supported audio files directly with Harmonix SE.
- **Native Menus**: Implemented native system menus (File, Edit, Window) for better OS integration.

### Improved

- **UI/UX**: Refined "Embedded Replacement" design for audio preview, ensuring a clean and clutter-free interface.
- **Analysis**: Bundled `ffprobe` binaries for robust audio analysis across macOS, Windows, and Linux.
- **Performance**: Optimized backend communication for analysis and conversion tasks.

### Fixed

- **Audio Cleanup**: Fixed issues where audio would continue playing or duplicate after closing the preview.
- **Layout**: Resolved layout shift issues when toggling the waveform player.

## [1.0.0] - 2025-11-28

### Audio Processing

- Multi-format support: MP3, WAV, OGG, FLAC, AAC, WMA, and more
- Batch conversion with per-file progress tracking
- Audio normalization using predefined mastering presets
- Automatic silence trimming (head/tail)
- High-performance processing powered by integrated FFmpeg

### User Interface

- iOS/macOS-inspired design with blur, glass effects, and rounded corners
- System Light/Dark mode detection
- Drag-and-drop file import
- Real-time conversion status
- Configurable output settings, quality levels, and concurrency

### Technical Highlights

- Fully standalone (Python + FFmpeg bundled)
- Built with Tauri v2 for low resource usage
- Cross-platform: macOS (Intel/Apple Silicon), Windows x64, Linux x64
- Auto-update ready for future releases
