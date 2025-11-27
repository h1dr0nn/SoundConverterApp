//! Python backend integration module.

use crate::core::logging::log_message;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use tauri::Manager;

#[derive(Debug)]
struct PythonResolution {
    command: PathBuf,
    backend_path: PathBuf,
    bin_dir: Option<PathBuf>,
    python_home: Option<PathBuf>,
    uses_embedded: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ConvertPayload {
    pub files: Vec<String>,
    pub format: String,
    pub output: String,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct BackendResult {
    pub status: String,
    pub message: String,
    #[serde(default)]
    pub outputs: Vec<String>,
}

/// Execute Python backend with JSON input via stdin and stream progress events.
pub fn execute_python_conversion(
    app: tauri::AppHandle,
    payload: ConvertPayload,
) -> Result<BackendResult, String> {
    let resolution = resolve_python(&app)?;

    let json_input = serde_json::to_string(&serde_json::json!({
        "operation": "convert",
        "files": payload.files,
        "format": payload.format,
        "output": payload.output,
    }))
    .map_err(|e| format!("Failed to serialize request: {}", e))?;

    log_message(
        "tauri",
        &format!(
            "Spawning python backend at {} (embedded={})",
            resolution.backend_path.display(),
            resolution.uses_embedded,
        ),
    );

    let mut command = Command::new(&resolution.command);
    command
        .arg(&resolution.backend_path)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    if let Some(bin_dir) = resolution.bin_dir.as_ref() {
        let bin_dir_str = bin_dir.to_string_lossy().to_string();
        command.env("SOUNDCONVERTER_BIN_DIR", &bin_dir_str);

        if let Some(path) = std::env::var_os("PATH") {
            let mut entries = std::env::split_paths(&path).collect::<Vec<_>>();
            if !entries.contains(bin_dir) {
                entries.insert(0, bin_dir.clone());
                let merged = std::env::join_paths(entries)
                    .map_err(|e| format!("Unable to join PATH entries: {}", e))?;
                command.env("PATH", merged);
            }
        } else {
            command.env("PATH", &bin_dir_str);
        }
    }

    // Resolve bundled FFmpeg sidecar based on target platform
    let ffmpeg_binary_name = if cfg!(target_os = "windows") {
        "ffmpeg-x86_64-pc-windows-msvc.exe"
    } else if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
        "ffmpeg-aarch64-apple-darwin"
    } else if cfg!(all(target_os = "macos", target_arch = "x86_64")) {
        "ffmpeg-x86_64-apple-darwin"
    } else if cfg!(all(target_os = "linux", target_arch = "aarch64")) {
        "ffmpeg-aarch64-unknown-linux-gnu"
    } else if cfg!(all(target_os = "linux", target_arch = "x86_64")) {
        "ffmpeg-x86_64-unknown-linux-gnu"
    } else {
        "ffmpeg" // fallback
    };

    let ffmpeg_resource_path = format!("binaries/{}", ffmpeg_binary_name);

    let mut ffmpeg_path_opt = app.path_resolver().resolve_resource(&ffmpeg_resource_path);

    // In dev mode, if resource resolution fails, try direct filesystem path
    if ffmpeg_path_opt.is_none()
        || !ffmpeg_path_opt
            .as_ref()
            .map(|p| p.exists())
            .unwrap_or(false)
    {
        if cfg!(debug_assertions) {
            // Try relative to current working directory (dev mode)
            let dev_path = std::env::current_dir().ok().map(|cwd| {
                cwd.join("src-tauri")
                    .join("binaries")
                    .join(ffmpeg_binary_name)
            });

            if let Some(ref path) = dev_path {
                if path.exists() {
                    log_message(
                        "tauri",
                        &format!("Using dev FFmpeg path: {}", path.display()),
                    );
                    ffmpeg_path_opt = Some(path.clone());
                }
            }
        }
    }

    if let Some(ffmpeg_path) = ffmpeg_path_opt {
        if ffmpeg_path.exists() {
            log_message(
                "tauri",
                &format!(
                    "Using bundled FFmpeg ({}) at: {}",
                    ffmpeg_binary_name,
                    ffmpeg_path.display()
                ),
            );

            // Set FFMPEG_BINARY to the exact binary path (highest priority)
            command.env("FFMPEG_BINARY", &ffmpeg_path);

            // Also add to PATH for fallback
            if let Some(ffmpeg_bin_dir) = ffmpeg_path.parent() {
                let ffmpeg_bin_str = ffmpeg_bin_dir.to_string_lossy().to_string();

                if let Some(current_path) = std::env::var_os("PATH") {
                    let mut entries = std::env::split_paths(&current_path).collect::<Vec<_>>();
                    let ffmpeg_pathbuf = ffmpeg_bin_dir.to_path_buf();
                    if !entries.contains(&ffmpeg_pathbuf) {
                        entries.insert(0, ffmpeg_pathbuf);
                        if let Ok(merged) = std::env::join_paths(entries) {
                            command.env("PATH", merged);
                        }
                    }
                } else {
                    command.env("PATH", &ffmpeg_bin_str);
                }

                command.env("SOUNDCONVERTER_BIN_DIR", &ffmpeg_bin_str);
            }
        } else {
            log_message(
                "tauri",
                &format!("FFmpeg binary not found at: {}", ffmpeg_path.display()),
            );
        }
    } else {
        log_message(
            "tauri",
            &format!(
                "FFmpeg binary not found for resource path: {}",
                ffmpeg_resource_path
            ),
        );
    }

    if let Some(python_home) = resolution.python_home.as_ref() {
        command.env("PYTHONHOME", python_home);
    }

    command
        .env("PYTHONUNBUFFERED", "1")
        .env("PYTHONDONTWRITEBYTECODE", "1");

    let mut child = command
        .spawn()
        .map_err(|e| format!("Failed to spawn Python process: {}", e))?;

    if let Some(mut stdin) = child.stdin.take() {
        stdin
            .write_all(json_input.as_bytes())
            .map_err(|e| format!("Failed to write to stdin: {}", e))?;
    }

    let stderr_handle = child.stderr.take().map(|stderr| {
        std::thread::spawn(move || {
            let reader = BufReader::new(stderr);
            for line in reader.lines() {
                if let Ok(text) = line {
                    log_message("python", &text);
                }
            }
        })
    });

    let mut final_result: Option<BackendResult> = None;
    let mut last_stdout = String::new();

    if let Some(stdout) = child.stdout.take() {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            if let Ok(mut text) = line {
                if text.trim().is_empty() {
                    continue;
                }

                text = text.trim().to_string();
                last_stdout = text.clone();

                match serde_json::from_str::<Value>(&text) {
                    Ok(value) => {
                        if let Err(err) = app.emit_all("conversion-progress", value.clone()) {
                            log_message(
                                "tauri",
                                &format!("Failed to emit progress event: {}", err),
                            );
                        }

                        if let Some(status) = value
                            .get("event")
                            .and_then(|event| event.as_str())
                            .filter(|event| *event == "complete")
                        {
                            let outputs = value
                                .get("outputs")
                                .and_then(|raw| serde_json::from_value(raw.clone()).ok())
                                .unwrap_or_default();
                            let message = value
                                .get("message")
                                .and_then(|raw| raw.as_str())
                                .unwrap_or_default()
                                .to_string();

                            final_result = Some(BackendResult {
                                status: value
                                    .get("status")
                                    .and_then(|s| s.as_str())
                                    .unwrap_or(status)
                                    .to_string(),
                                message,
                                outputs,
                            });
                        }
                    }
                    Err(err) => {
                        log_message(
                            "tauri",
                            &format!("Failed to parse python output '{}': {}", text, err),
                        );
                    }
                }
            }
        }
    }

    if let Some(handle) = stderr_handle {
        let _ = handle.join();
    }

    let status = child
        .wait()
        .map_err(|e| format!("Failed to wait for Python process: {}", e))?;

    if !status.success() {
        let code = status.code().unwrap_or(-1);
        let message = if last_stdout.is_empty() {
            format!("Python process failed with exit code {}", code)
        } else {
            format!(
                "Python process failed with exit code {}: {}",
                code, last_stdout
            )
        };
        return Err(message);
    }

    final_result.ok_or_else(|| "Python backend did not return a final status".to_string())
}

fn resolve_python(app: &tauri::AppHandle) -> Result<PythonResolution, String> {
    // Try to resolve backend/main.py from multiple locations
    // 1. Bundled resource (production)
    // 2. Project root (dev mode)
    // 3. Relative to current exe (fallback)

    let backend_candidates = vec![
        // Production: bundled resource
        app.path_resolver().resolve_resource("backend/main.py"),
        // Dev mode: relative to project root
        std::env::current_dir()
            .ok()
            .map(|cwd| cwd.join("backend/main.py")),
        // Dev mode alt: go up from src-tauri
        std::env::current_dir()
            .ok()
            .and_then(|cwd| cwd.parent().map(|p| p.join("backend/main.py"))),
        // Fallback: relative path
        Some(PathBuf::from("backend/main.py")),
    ];

    let backend_path = backend_candidates
        .into_iter()
        .flatten()
        .find(|path| path.exists())
        .ok_or_else(|| {
            let cwd = std::env::current_dir()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|_| "unknown".to_string());
            format!(
                "Unable to locate backend/main.py. Checked multiple locations. Current dir: {}",
                cwd
            )
        })?;

    log_message(
        "tauri",
        &format!("Found backend at: {}", backend_path.display()),
    );

    // Try new binaries/ location first (for Phase 4 bundled Python)
    let binaries_root = app.path_resolver().resolve_resource("binaries");

    // Then try old bin/ locations (for backward compatibility)
    let bin_root_candidates = [
        app.path_resolver().resolve_resource("bin"),
        app.path_resolver().resolve_resource("src-tauri/bin"),
    ];

    let bin_root = bin_root_candidates
        .into_iter()
        .flatten()
        .find(|path| path.exists());

    // Collect Python candidates from both binaries/ and bin/
    let mut python_candidates = Vec::new();

    // Add candidates from binaries/ directory (Phase 4 structure)
    if let Some(ref binaries_dir) = binaries_root {
        if binaries_dir.exists() {
            python_candidates.extend(embedded_python_from_binaries(binaries_dir));
        }
    }

    // Add candidates from bin/ directory (legacy structure)
    python_candidates.extend(
        bin_root
            .iter()
            .flat_map(|bin_root| embedded_python_candidates(bin_root)),
    );

    let embedded_python = python_candidates.iter().find(|path| path.exists());

    let uses_embedded = embedded_python.is_some();
    let python_cmd = embedded_python
        .cloned()
        .or_else(|| {
            if cfg!(debug_assertions) {
                log_message(
                    "tauri",
                    "Embedded python runtime was not found. Falling back to system python for dev build.",
                );
                Some(PathBuf::from("python3"))
            } else {
                None
            }
        })
        .ok_or_else(|| {
            "Embedded Python runtime missing. Run scripts/download-binaries.sh to download it.".to_string()
        })?;

    let python_home = embedded_python
        .as_ref()
        .and_then(|bin| derive_python_home(bin.as_path()));

    Ok(PythonResolution {
        command: python_cmd,
        backend_path,
        bin_dir: bin_root.or(binaries_root),
        python_home,
        uses_embedded,
    })
}

fn embedded_python_from_binaries(binaries_root: &Path) -> Vec<PathBuf> {
    // Check for target-triple named Python directories
    // Format: python-<target-triple>/bin/python3
    let targets = [
        "aarch64-apple-darwin",      // macOS ARM64
        "x86_64-apple-darwin",       // macOS Intel
        "x86_64-pc-windows-msvc",    // Windows x64
        "aarch64-unknown-linux-gnu", // Linux ARM64
        "x86_64-unknown-linux-gnu",  // Linux x64
    ];

    targets
        .iter()
        .flat_map(|target| {
            let python_dir = binaries_root.join(format!("python-{}", target));
            vec![
                python_dir.join("bin").join("python3"),
                python_dir.join("bin").join("python"),
                python_dir.join("python.exe"),
                python_dir.join("python3.exe"),
            ]
        })
        .collect()
}

fn embedded_python_candidates(bin_root: &Path) -> Vec<PathBuf> {
    let python_dir = bin_root.join("python");
    vec![
        python_dir.join("python.exe"),
        python_dir.join("python"),
        python_dir.join("python3"),
        python_dir.join("bin").join("python3"),
        python_dir.join("bin").join("python"),
    ]
}

fn derive_python_home(python_bin: &Path) -> Option<PathBuf> {
    let parent = python_bin.parent()?;

    if parent.file_name().is_some_and(|name| name == "bin") {
        parent.parent().map(|path| path.to_path_buf())
    } else {
        Some(parent.to_path_buf())
    }
}
