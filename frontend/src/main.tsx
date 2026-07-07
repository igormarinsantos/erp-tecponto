import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource/space-grotesk/latin-400.css";
import "@fontsource/space-grotesk/latin-500.css";
import "@fontsource/space-grotesk/latin-600.css";
import "@fontsource/space-grotesk/latin-700.css";

import { App } from "./App";
import "./styles/tailwind.css";

ReactDOM.createRoot(document.getElementById("tecponto-root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
