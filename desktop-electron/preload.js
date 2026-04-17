const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("dndDesktop", {
  getConfig: () => ipcRenderer.invoke("desktop:get-config"),
  onBackendStatus: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("desktop:backend-status", listener);
    return () => ipcRenderer.removeListener("desktop:backend-status", listener);
  },
});
