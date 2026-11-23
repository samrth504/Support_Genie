import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import ServerWakeup from "./components/ServerWakeup.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ServerWakeup>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ServerWakeup>
    </BrowserRouter>
  </React.StrictMode>,
);
