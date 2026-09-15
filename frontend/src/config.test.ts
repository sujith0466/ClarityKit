import { describe, it, expect } from "vitest";
import { config } from "./config";

describe("Frontend Configuration Module", () => {
  it("provides valid default configuration values", () => {
    expect(config.apiBaseUrl).toBeDefined();
    expect(typeof config.apiBaseUrl).toBe("string");
    expect(config.apiBaseUrl.length).toBeGreaterThan(0);
    expect(config.mode).toBeDefined();
    expect(typeof config.isDev).toBe("boolean");
    expect(typeof config.isProd).toBe("boolean");
  });
});
