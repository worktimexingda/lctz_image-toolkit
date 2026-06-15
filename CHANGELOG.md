# Changelog

## 0.01

- Renamed the public project and build artifacts to lctz_image-toolkit.
- Rebuilt the project as a PySide6 desktop image toolbox.
- Added ratio calculator with preset and custom ratios.
- Added image comparison tab with click/drag upload slots.
- Added slide comparison, click comparison, difference highlight, and merge preview.
- Added horizontal, vertical, and automatic merge direction.
- Added optional preview downscaling: no compression, 16K, 8K, and 4K.
- Added mouse-position-centered zoom and left-button canvas panning.
- Added background presets for preview observation.
- Exported merged images with white padding and original image dimensions.
- Added asynchronous merge export to keep the UI responsive.
- Added attribution for rgthree-comfy's Image Comparer interaction inspiration.
- Added open-source project files: MIT license, notice, changelog, and git ignore rules.
- Added macOS build scripts and GitHub Actions workflow templates for x86_64 and arm64 builds.
- Improved ratio calculator defaults: custom ratio is selected by default, empty custom ratio allows free width/height input, and ratio results update in real time.
- Improved ratio preset table sizing, row selection, hover styling, and preset-to-combo synchronization.
- Relaxed the application minimum window size.
- Simplified the ratio selector so it only shows custom mode and the currently selected preset.
- Set the ratio calculator as the default first tab, with image comparison as the second tab.
