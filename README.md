# Sound Converter App

Ứng dụng desktop viết bằng Python/PySide6 giúp bạn kéo thả file âm thanh, chọn định dạng xuất và chuyển đổi nhanh chóng với giao diện hiện đại.

## Tính năng chính

- Giao diện tối giản, hiện đại với QSS tuỳ biến và icon vector.
- Hỗ trợ kéo & thả hoặc duyệt nhiều file âm thanh từ máy.
- Tuỳ chọn định dạng đầu ra (MP3, WAV, OGG, FLAC, AAC, WMA...).
- Chọn thư mục lưu và xem trước đường dẫn xuất.
- Xử lý chuyển đổi trên luồng phụ (worker thread) để UI luôn mượt.

## Yêu cầu

- Python 3.9 trở lên.
- [FFmpeg](https://ffmpeg.org/download.html) đã được cài và thêm vào `PATH` (pydub cần công cụ này để xuất âm thanh).
- Các thư viện Python: PySide6, pydub và pyaudioop (cài đặt bằng `pip install -r requirements.txt`).

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy ứng dụng

```bash
python main.py
```

## Đóng gói thành file `.exe`

1. Cài đặt PyInstaller (chỉ cần thực hiện một lần):

   ```bash
   pip install pyinstaller
   ```

2. Đóng gói ứng dụng (chạy lệnh trên Windows Terminal/PowerShell tại thư mục dự án):

   ```powershell
   pyinstaller --noconfirm --windowed ^
     --name SoundConverter ^
     --add-data "app/resources;app/resources" ^
     main.py
   ```

   Hoặc sử dụng file `setup.spec` đã cấu hình sẵn đường dẫn icon `.svg`:

   ```powershell
   pyinstaller setup.spec
   ```

3. File chạy sẽ nằm trong thư mục `dist/SoundConverter/SoundConverter.exe`.

> Lưu ý: Nếu build trên Linux/macOS hãy đổi dấu phân cách trong `--add-data` từ `;` thành `:`.
