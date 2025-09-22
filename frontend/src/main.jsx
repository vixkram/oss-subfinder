import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import SubfinderUI from "./components/SubfinderUI.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <div className="min-h-screen">
      <div className="mx-auto w-full max-w-7xl px-6 py-10">
        <SubfinderUI />
      </div>
    </div>
  </React.StrictMode>
);
