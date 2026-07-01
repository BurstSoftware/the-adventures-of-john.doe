# Voice Changer Project: English Input to Chinese Accent Output on macOS

## Overview
This project implements a real-time voice changer that takes English speech input and outputs it with a Chinese accent. Targeted for macOS 15.6.1 (Sequoia) on Apple Silicon.

## Recommended Solution: Seed-VC (Zero-Shot Voice Conversion)

**Why Seed-VC?**
- Zero-shot voice conversion (no training required initially).
- Supports accent/style/emotion transfer.
- Real-time GUI with low latency (~300-500ms).
- Native support for Apple Silicon (M-series Macs).
- Open-source and free.

### Setup Instructions

1. **Prerequisites**
   - macOS 15+
   - Python 3.10+ (with Tkinter support)
   - Git
   - FFmpeg (`brew install ffmpeg`)

2. **Installation**
   ```bash
   git clone https://github.com/Plachtaa/seed-vc.git
   cd seed-vc
   pip install -r requirements-mac.txt
