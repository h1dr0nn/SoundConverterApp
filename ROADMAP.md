# 🚀 Sound Converter – Project Roadmap

Modern desktop sound converter using **Tauri + React + Python (FFmpeg)** with an **iOS/macOS-style UI**.

---

## 1. Goals

- Xây dựng giao diện hiện đại theo phong cách **iOS/macOS** (glassmorphism, blur, rounded).
- Giữ backend Python (FFmpeg wrapper) để xử lý audio.
- Đảm bảo app **nhẹ**, **ổn định**, **mượt** theo tiêu chuẩn Tauri.
- Thiết lập CI/CD tự động build và publish release.
- Packaging độc lập: bao gồm Python runtime + FFmpeg trong app bundle.

---

## 2. Architecture Overview

```
Tauri (App Shell)
├── React + Tailwind (UI Layer)
├── Python Backend (Conversion Logic)
└── FFmpeg Binary
```

---

## 3. Milestones

### 🧩 **Phase 1 — Foundation Setup**

**Status: In Progress**

- [x] Init repo cấu trúc 3 phần: `/frontend`, `/backend`, `/src-tauri`.
- [x] Setup Tauri project + React + Tailwind.
- [x] Setup Python backend tối giản (main entrypoint, convert function).
- [ ] Tạo cơ chế IPC: React → Tauri → Python → Tauri → React. (React ↔️ Tauri ping ready; Python bridge planned.)
- [x] File drag-and-drop UI (frontend only).

---

### 🎨 **Phase 2 — UI/UX (iOS/macOS style)**

**Status: Pending**

- [ ] Thiết kế layout chính: sidebar + content area.
- [ ] Glassmorphism: blur, semi-transparent layer.
- [ ] Component:
  - [ ] File list panel.
  - [ ] Format selector.
  - [ ] Output folder chooser.
  - [ ] Progress bar / processing indicator.
  - [ ] Toast notifications.
- [ ] Light/Dark theme theo phong cách macOS Sonoma.
- [ ] Transition/Animation (150–250ms).

---

### 🔧 **Phase 3 — Backend Integration**

**Status: Pending**

- [ ] Tạo command Tauri gọi Python.
- [ ] Python: load FFmpeg path từ bundle.
- [ ] Xử lý nhiều file (batch mode).
- [ ] Streaming progress về frontend.
- [ ] Log pipeline (Tauri, Python, FFmpeg).

---

### 📦 **Phase 4 — Packaging**

**Status: Pending**

- [ ] Embed Python runtime vào `/src-tauri/bin/python`.
- [ ] Embed FFmpeg vào `/src-tauri/bin/ffmpeg`.
- [ ] Tauri: platform-specific bundling.
- [ ] Test app chạy độc lập không cần cài Python.

---

### 🛠 **Phase 5 — CI/CD**

**Status: Pending**

- [ ] GitHub Actions:
  - [ ] Setup Node + Rust + Python.
  - [ ] Install dependencies (frontend + backend).
  - [ ] Download FFmpeg.
  - [ ] Copy Python + FFmpeg vào bundle.
  - [ ] Build Tauri cho macOS + Windows.
  - [ ] Auto-publish vào GitHub Releases (tag push).
- [ ] Xác nhận app chạy ổn trên máy thật.

---

### 🌟 **Phase 6 — Optional Enhancements**

**Status: Optional**

- [ ] Plugin drag file vào Dock icon (macOS).
- [ ] Auto-detect input format + smart preset.
- [ ] Show waveform preview.
- [ ] Auto-update (Tauri updater).
- [ ] Multi-language (i18n).

---

## 4. Success Criteria

- App chạy ổn trên Windows/macOS.
- UI đẹp, mượt, đúng triết lý iOS/macOS.
- Build tự động, release tự động.
- Không cần user cài Python hay FFmpeg.
- Update dễ dàng, architecture rõ ràng.

---

## 5. Long-term Vision

**Trở thành app nhỏ – nhẹ – đẹp – có chiều sâu kỹ thuật**, hướng tới chuẩn UX/macOS:

- Ứng dụng native feel, chuyên nghiệp.
- Từ converter → mở rộng thành audio toolkit mini.
