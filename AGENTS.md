# 🤖 Project Agents — Rules & Guidelines

- UI must follow the **iOS/macOS design philosophy**.
- Codebase must remain clean, modular, and layered.
- Do **not** break the **3-layer architecture** (UI / Tauri / Python).
- All new features must align with the project’s overall vision.

---

# 1. UI Agent – (React / Tailwind)

## UI Philosophy

Target style: **iOS/macOS Sonoma**

- Glassmorphism
  - Blur: 24–40px
  - Opacity: 40–60%
- Rounded corners: 12–24px
- Font: **Inter** (cross-platform) / **SF Pro** on macOS
- Minimal and soft shadows
- Smooth animations: **≤ 250ms**
- Components must be:
  - clean and readable
  - clearly structured
  - free of clutter
- Avoid complex CSS → use **Tailwind**.

## Rules

- UI handles **state and presentation only**.
- Never call Python directly → all calls must go through `invoke()`.
- Each component must be **< 300 lines**.
- Mandatory folder structure:

```
/frontend/src/components/
/frontend/src/pages/
/frontend/src/hooks/
/frontend/src/utils/
```

---

# 2. Tauri Agent – (Rust Layer)

## Responsibilities

- Bridge between UI and Python.
- Handles:
  - IPC commands
  - Python process lifecycle
  - Build & packaging
  - Security & filesystem access

## Rules

- No audio logic inside Rust code.
- Do not modify parameters between UI → Python.
- All commands must define clear input/output schemas.
- Mandatory directories:

```
/src-tauri/src/commands/
/src-tauri/src/core/
/src-tauri/bin/  # FFmpeg + Python
```

---

# 3. Python Agent – (Backend Logic)

## Philosophy

- **Single responsibility**: audio conversion only.
- No UI logic, no dialogs, no window handling.

## Rules

- Use only the `backend/` directory.
- Do not import modules from Tauri or frontend.
- Required structure:

```
backend/
main.py
app/
ffmpeg_runner.py
utils.py
```

## Processing Flow

1. Receive JSON input (path, format).
2. Convert files using FFmpeg.
3. Stream progress through stdout (JSON line by line).
4. Exit code must indicate success or failure.

---

# 4. CI/CD Agent – (Automation)

## Responsibilities

- Build automatically.
- Package automatically.
- Publish releases automatically.
- Never commit large binaries into the repository.

## Rules

- Always download FFmpeg from official sources.
- Python runtime must be embedded automatically.
- Workflow YAML must be clean and well-commented.

## Folder Structure

```
.github/workflows/
scripts/
```

---

# 5. General Rules

- Do not modify project structure without updating `ROADMAP.md`.
- Do not add heavy libraries to frontend (avoid Electron-like bundles).
- Do not push files > 50MB to the repository.
- Do not change Tauri ↔ Python communication without a formal proposal.

---

# 6. Design Tokens (UI)

```
RADIUS: 16px
BLUR: 32px
CARD_OPACITY: 0.55
ANIMATION: 180ms
FONT: Inter / SF Pro
COLOR_BG_LIGHT: #F2F2F7
COLOR_BG_DARK: #1C1C1E
ACCENT: #007AFF
```

---

# 7. Commit Rules

- Prefixes must be:  
  `feat:`, `fix:`, `ui:`, `build:`, `refactor:`
- Do not commit build artifacts.
- PRs must describe the flow clearly and include UI screenshots if applicable.

---

# 8. Agent Purpose Summary

| Agent            | Purpose                                      |
| ---------------- | -------------------------------------------- |
| **UI Agent**     | Build clean iOS-style UI, manage view state. |
| **Tauri Agent**  | Communication, process management, bundling. |
| **Python Agent** | Audio processing (FFmpeg wrapper).           |
| **CI/CD Agent**  | Automate build and release pipeline.         |

---

> **All agents must follow the core philosophy: simple — clear — smooth — iOS/macOS style.**
