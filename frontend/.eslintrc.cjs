module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  ignorePatterns: ['dist/**'],
  extends: [
    'eslint:recommended',
    'plugin:react-hooks/recommended',
  ],
  plugins: ['react', 'react-refresh'],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  settings: { react: { version: '18.2' } },
  rules: {
    'react/jsx-uses-vars': 'error',
    'react-refresh/only-export-components': 'off',
    'react-hooks/exhaustive-deps': 'off',
  },
  overrides: [{ files: ['vite.config.js'], env: { node: true, browser: false } }],
};
