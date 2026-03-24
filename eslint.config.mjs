import globals from "globals";
import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.jquery,
        ...globals.jest,
        ...globals.node,
        google: "readonly",
        L: "readonly", // Leaflet
        Swal: "readonly", // SweetAlert2
        Chart: "readonly", // Chart.js
        API: "readonly", // Internal module
        MapManager: "readonly", // Internal module
        initTheme: "readonly", // Internal helper
        handleRoute: "readonly", // Internal helper
      },
    },
    rules: {
      "indent": ["error", 2],
      "no-unused-vars": "warn",
      "no-console": "off", // Для веба консоль полезна
      "quotes": ["error", "double"],
      "semi": ["error", "always"],
    },
  },
  {
    ignores: ["node_modules/", "venv/", "dist/", "static/vendor/"],
  }
];
