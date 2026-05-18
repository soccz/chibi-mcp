// ESLint flat config for chibi-mcp desktop frontend (main.js).
// Browser globals via the `globals` package.

import globals from "globals";

export default [
    {
        languageOptions: {
            ecmaVersion: 2024,
            sourceType: "module",
            globals: {
                ...globals.browser,
            },
        },
        linterOptions: {
            reportUnusedDisableDirectives: "warn",
        },
        rules: {
            "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
            "no-undef": "error",
            "no-var": "error",
            "prefer-const": "warn",
            "no-console": "off",          // we use console.warn/error intentionally
            "no-empty": ["warn", { allowEmptyCatch: true }],
            "eqeqeq": ["warn", "smart"],
        },
    },
];
