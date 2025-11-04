const { contextBridge, ipcRenderer } = require('electron');

// contextBridge.exposeInMainWorld('sdk', {
//   launch: () => ipcRenderer.invoke('sdk-launch'),
// });

contextBridge.exposeInMainWorld('electronAPI', {
  openTerminal: (args) => ipcRenderer.invoke('open-terminal', args),
  closeTerminal: () => ipcRenderer.invoke('close-terminal'),
});