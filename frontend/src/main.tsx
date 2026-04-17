import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { getDesktopConfig, setDesktopConfig } from "./lib/desktopBridge";
import "./styles.css";

async function bootstrap() {
  const config = await getDesktopConfig();
  setDesktopConfig(config);
  ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

void bootstrap();
