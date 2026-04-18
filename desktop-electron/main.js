const electronMain = (() => {
  try {
    return require("electron/main");
  } catch (_err) {
    return require("electron");
  }
})();
const { app, BrowserWindow, dialog, ipcMain } = electronMain;
const path = require("node:path");
const fs = require("node:fs");
const { spawn } = require("node:child_process");

const BACKEND_PORT = Number(process.env.DND_VTT_DESKTOP_BACKEND_PORT || 8000);
const FRONTEND_DEV_URL = process.env.DND_VTT_DESKTOP_FRONTEND_URL || "http://127.0.0.1:5173";
const BACKEND_HOST = "127.0.0.1";

let mainWindow = null;
let backendProc = null;
let frontendProc = null;
let backendState = "booting";
let backendLastError = "";

function emitBackendState(nextState, message = "") {
  backendState = nextState;
  backendLastError = message;
  if (mainWindow) {
    mainWindow.webContents.send("desktop:backend-status", {
      state: backendState,
      message: backendLastError,
    });
  }
}

function resolvePythonExec() {
  const workspaceRoot = path.resolve(__dirname, "..");
  if (process.platform === "win32") {
    const preferredWindows = path.join(workspaceRoot, ".venv", "Scripts", "python.exe");
    if (fs.existsSync(preferredWindows)) return preferredWindows;
    return "python";
  }
  const preferred = path.join(workspaceRoot, ".venv", "bin", "python");
  if (fs.existsSync(preferred)) return preferred;
  return "python3";
}

async function waitForReady(url, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const resp = await fetch(url);
      if (resp.ok) return;
    } catch (_err) {
      // Not ready yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for readiness: ${url}`);
}

function spawnFrontendDevServer() {
  if (!process.env.DND_VTT_ELECTRON_DEV) return;
  const workspaceRoot = path.resolve(__dirname, "..");
  emitBackendState("booting", "Starting frontend dev server...");
  frontendProc = spawn(
    "npm",
    ["--prefix", path.join(workspaceRoot, "frontend"), "run", "dev", "--", "--host", BACKEND_HOST, "--port", "5173"],
    {
      cwd: workspaceRoot,
      stdio: "pipe",
      env: { ...process.env },
    },
  );
  frontendProc.stdout.on("data", (chunk) => {
    process.stdout.write(`[frontend] ${chunk}`);
  });
  frontendProc.stderr.on("data", (chunk) => {
    process.stderr.write(`[frontend] ${chunk}`);
  });
}

async function spawnBackend() {
  const workspaceRoot = path.resolve(__dirname, "..");
  const pythonExec = resolvePythonExec();
  emitBackendState("booting", "Starting backend service...");

  backendProc = spawn(
    pythonExec,
    ["-m", "uvicorn", "net.signaling_service:app", "--host", BACKEND_HOST, "--port", String(BACKEND_PORT)],
    {
      cwd: workspaceRoot,
      stdio: "pipe",
      env: { ...process.env, PYTHONPATH: workspaceRoot },
    },
  );

  backendProc.stdout.on("data", (chunk) => {
    process.stdout.write(`[backend] ${chunk}`);
  });
  backendProc.stderr.on("data", (chunk) => {
    process.stderr.write(`[backend] ${chunk}`);
  });
  backendProc.on("exit", (code, signal) => {
    if (!app.isQuitting) {
      emitBackendState("error", `Backend exited unexpectedly (code=${code}, signal=${signal ?? "none"})`);
    }
  });

  await waitForReady(`http://${BACKEND_HOST}:${BACKEND_PORT}/health/ready`, 20_000);
  emitBackendState("ready");
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1500,
    height: 980,
    minWidth: 1180,
    minHeight: 760,
    title: "DND VTT",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
    },
  });

  if (process.env.DND_VTT_ELECTRON_DEV) {
    mainWindow.loadURL(FRONTEND_DEV_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path.resolve(__dirname, "..", "frontend", "dist", "index.html"));
  }
}

function stopChild(proc) {
  if (!proc || proc.killed) return;
  proc.kill("SIGTERM");
}

function registerDesktopIpc() {
  ipcMain.handle("desktop:get-config", () => ({
    isDesktop: true,
    apiBaseUrl: `http://${BACKEND_HOST}:${BACKEND_PORT}/api`,
    wsHost: `${BACKEND_HOST}:${BACKEND_PORT}`,
    backendState,
    backendMessage: backendLastError,
  }));
}

const singleInstance = app.requestSingleInstanceLock();
if (!singleInstance) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    registerDesktopIpc();
    try {
      spawnFrontendDevServer();
      await spawnBackend();
      createWindow();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      await dialog.showErrorBox("DND VTT Startup Failed", message);
      app.quit();
    }
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });

  app.on("before-quit", () => {
    app.isQuitting = true;
    stopChild(frontendProc);
    stopChild(backendProc);
  });
}
