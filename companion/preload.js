const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  onHookEvent: (callback) => {
    ipcRenderer.on('hook-event', (event, data) => callback(data));
  },
  onVaultStatus: (callback) => {
    ipcRenderer.on('vault-status', (event, data) => callback(data));
  },
  setIgnoreMouseEvents: (ignore, options) => {
    ipcRenderer.send('set-ignore-mouse-events', ignore, options);
  },
});
