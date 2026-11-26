// App nativo do Painel Investimentos: uma janela própria que abre o site
// publicado no GitHub Pages, sem a barra de título cinza do Windows.
const { app, BrowserWindow, nativeTheme, shell } = require("electron");
const path = require("path");

const SITE = "https://davicosban.github.io/Investimentos/";
const BAR = 44; // altura da faixa do topo onde ficam os botões da janela

const cores = () =>
  nativeTheme.shouldUseDarkColors
    ? { color: "#07090D", symbolColor: "#EEF0F4", height: BAR }
    : { color: "#F4F3EF", symbolColor: "#12141A", height: BAR };

// Faz o cabeçalho do site servir para arrastar a janela e abre espaço
// para os botões minimizar / maximizar / fechar no canto direito.
const CSS = `
  header.top{-webkit-app-region:drag;padding-top:6px!important}
  header.top a,header.top button,header.top input,header.top select,nav.tabs,.dbar{-webkit-app-region:no-drag}
  header.top .topin{padding-right:150px!important}
  @media (max-width:700px){header.top .topin{padding-right:16px!important}}
`;

function criarJanela() {
  const win = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 420,
    minHeight: 500,
    title: "Painel Investimentos",
    icon: path.join(__dirname, "build", "icon.png"),
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#07090D" : "#F4F3EF",
    titleBarStyle: "hidden",
    titleBarOverlay: cores(),
    autoHideMenuBar: true,
    show: false,
    webPreferences: { contextIsolation: true, sandbox: true },
  });

  win.once("ready-to-show", () => win.show());
  win.webContents.on("did-finish-load", () => {
    if (win.webContents.getURL().startsWith(SITE)) win.webContents.insertCSS(CSS);
  });
  win.webContents.on("did-fail-load", (_e, code, _desc, url, isMain) => {
    if (isMain && code !== -3) win.loadFile(path.join(__dirname, "offline.html"), { query: { u: SITE } });
  });

  // Links para outros sites abrem no navegador, não dentro do app.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https://")) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e, url) => {
    if (!url.startsWith(SITE) && !url.startsWith("file:")) {
      e.preventDefault();
      if (url.startsWith("https://")) shell.openExternal(url);
    }
  });

  nativeTheme.on("updated", () => {
    try { win.setTitleBarOverlay(cores()); } catch {}
    win.setBackgroundColor(nativeTheme.shouldUseDarkColors ? "#07090D" : "#F4F3EF");
  });

  // Recarrega a cada 30 minutos (se a janela não estiver em uso) para pegar dados novos.
  setInterval(() => {
    if (!win.isFocused() && win.webContents.getURL().startsWith(SITE)) win.webContents.reloadIgnoringCache();
  }, 30 * 60 * 1000);

  win.loadURL(SITE);
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    const w = BrowserWindow.getAllWindows()[0];
    if (w) { if (w.isMinimized()) w.restore(); w.focus(); }
  });
  app.setAppUserModelId("io.github.davicosban.painelinvestimentos");
  app.whenReady().then(criarJanela);
  app.on("window-all-closed", () => app.quit());
}
