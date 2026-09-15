/**
 * Frontend Application Configuration
 */

export interface Config {
  readonly apiBaseUrl: string;
  readonly mode: string;
  readonly isDev: boolean;
  readonly isProd: boolean;
}

export const config: Config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:5000",
  mode: import.meta.env.MODE || "development",
  isDev: import.meta.env.DEV ?? true,
  isProd: import.meta.env.PROD ?? false,
};

export default config;
