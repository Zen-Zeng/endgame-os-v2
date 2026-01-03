use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      let _child = app.shell().sidecar("brain")?
        .args(&["--host", "127.0.0.1", "--port", "8000"])
        .spawn()
        .expect("Failed to spawn sidecar process");

      log::info!("Sidecar process started");

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}