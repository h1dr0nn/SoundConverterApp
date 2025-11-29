# 🚀 Harmonix SE – Project Roadmap

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

**Status: ✅ Complete**

- [x] Init repo cấu trúc 3 phần: `/frontend`, `/backend`, `/src-tauri`.
- [x] Setup Tauri project + React + Tailwind.
- [x] Setup Python backend tối giản (main entrypoint, convert function).
- [x] Tạo cơ chế IPC: React → Tauri → Python → Tauri → React.
- [x] File drag-and-drop UI (frontend only).

---

### 🎨 **Phase 2 — UI/UX (iOS/macOS style)**

**Status: ✅ Complete**

- [x] Thiết kế layout chính: sidebar + content area.
- [x] Glassmorphism: blur, semi-transparent layer.
- [x] Component:
  - [x] File list panel.
  - [x] Format selector.
  - [x] Output folder chooser.
  - [x] Progress bar / processing indicator.
  - [x] Toast notifications.
- [x] Light/Dark theme theo phong cách macOS Sonoma.
- [x] Transition/Animation (150–250ms).

---

### 🔧 **Phase 3 — Backend Integration**

**Status: ✅ Complete**

- [x] Tạo command Tauri gọi Python.
- [x] Python: load FFmpeg path từ bundle.
- [x] Xử lý nhiều file (batch mode).
- [x] Streaming progress về frontend.
- [x] Log pipeline (Tauri, Python, FFmpeg).

---

### 📦 **Phase 4 — Packaging**

**Status: ✅ Complete**

- [x] Embed Python runtime vào `/src-tauri/bin/python`.
- [x] Embed FFmpeg vào `/src-tauri/bin/ffmpeg`.
- [x] Tauri: platform-specific bundling.
- [x] Test app chạy độc lập không cần cài Python.

---

### 🛠 **Phase 5 — CI/CD**

**Status: 🚧 In Progress**

- [x] GitHub Actions:
  - [x] Setup Node + Rust + Python.
  - [x] Install dependencies (frontend + backend).
  - [x] Download FFmpeg.
  - [x] Copy Python + FFmpeg vào bundle.
  - [x] Build Tauri cho macOS + Windows + Linux.
  - [x] Auto-publish vào GitHub Releases (tag push).
- [ ] Xác nhận app chạy ổn trên máy thật.

---

### 🌟 **Phase 6 — Advanced Polish & Features**

**Status: 🚧 In Progress**

#### **6.1 — Native Integration (macOS Focus)**

- [ ] **Dock Drag & Drop**: Kéo file vào icon Dock để mở app và thêm file.
- [ ] **Native Menu & Shortcuts**: Cải thiện menu bar và phím tắt chuẩn macOS (Cmd+O, Cmd+,).

#### **6.2 — Visual & Intelligence**

- [ ] **Waveform Preview**: Hiển thị visual sóng âm đơn giản cho file.
- [ ] **Smart Analysis**: Auto-detect format và gợi ý preset phù hợp.

#### **6.3 — System & Distribution**

- [ ] **Multi-language**: Hỗ trợ i18n (EN/VI).
- [ ] **Auto-updater**: Cơ chế tự cập nhật app.

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
