# Bilingual Bedrock UI Addon

A native, zero-dependency dual-language UI translation addon for Minecraft Bedrock Edition.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Bedrock](https://img.shields.io/badge/Minecraft-Bedrock_1.26+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

📚 **Tutorials**: [English](TUTORIAL_EN.md) | [Türkçe](TUTORIAL_TR.md) | [Français](TUTORIAL_FR.md)

## 📋 Features

- **True Bilingual UI**: Displays two languages simultaneously (e.g., English on top, French italicized below)
- **Native Rendering**: Zero scripts, zero Marketplace dependencies. Powered purely by Bedrock's native JSON UI and Font engine.
- **Custom PUA Font**: Second language characters are mapped to the Private Use Area (`\uE100-\uE1FF`) to guarantee flawless rendering.
- **Zero-Overlap Engine**: Uses algorithmic padding (12px tolerance) to force Bedrock's word-wrap engine to safely push the secondary language to the next line.
- **Component Filtering**: Intelligently skips massive text blocks (like EULA or Credits) to prevent UI breakage while preserving translations for buttons and smaller UI elements.

## 🚀 Quick Start

### Installation

1. Download the latest `Bilingual_UI.mcpack` from the [Releases](#) tab (or build it yourself).
2. Open the file on your device (iOS/Android/Windows 10). Minecraft will automatically import it.
3. Navigate to **Settings > Global Resources** and activate the pack.

### Building from Source

```bash
git clone https://github.com/Haymr/minecraft-bedrock-bilingual-ui.git
cd minecraft-bedrock-bilingual-ui
python -m venv compiler/venv
source compiler/venv/bin/activate
pip install Pillow

# Run the compiler pipeline
python compiler/src/parser.py
python compiler/src/font_generator.py
python compiler/src/ui_modifier.py

# Package the mcpack
cd resource_pack && zip -r ../Bilingual_UI.mcpack . -x "*.DS_Store"
```

## 📁 Project Structure

```
├── compiler/
│   └── src/
│       ├── parser.py              # PUA padding & mapping engine
│       ├── font_generator.py      # Bedrock glyph_E1.png generator
│       └── ui_modifier.py         # JSON inheritance injector
│
├── resource_pack/                 # The actual Minecraft Addon
│   ├── manifest.json              # Pack definitions
│   ├── font/                      # default.json (if applicable)
│   ├── texts/                     # Compiled .lang files
│   ├── textures/font/             # Custom PUA glyph atlases
│   └── ui/                        # Modified JSON UI screens
│
├── TUTORIAL_EN.md                 # English documentation
├── TUTORIAL_TR.md                 # Turkish documentation
└── TUTORIAL_FR.md                 # French documentation
```

## 🔬 System Architecture

```
Language 1 (e.g., en_US) + 12px Padding + Language 2 (PUA Encoded)
    │
    ▼
┌─────────────────────────────────┐
│     Bedrock Word-Wrap Engine    │
│  • Reads primary language       │
│  • Hits bounding box limit      │
│  • Pushes secondary lang down   │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│     Bedrock Font Engine         │
│  • Reads textures/font/glyph_E1 │
│  • Renders French characters    │
└─────────────────────────────────┘
```

## 🛠️ Requirements

- Minecraft Bedrock Edition (1.26.0+)
- Python 3.9+ (Only for compiling from source)
- Pillow (Only for compiling from source)

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.
