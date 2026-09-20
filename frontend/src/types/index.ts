/**
 * Frontend Type Definitions for ClarityKit Foundation
 */

export interface AppConfig {
  readonly apiBaseUrl: string;
  readonly environment: "development" | "production" | "test";
}

export interface ServiceStatus {
  readonly status: "ready" | "connecting" | "error";
  readonly message: string;
}

export * from "./auth";
export * from "./document";
export * from "./extraction";
export * from "./evidence";
export * from "./trust";
export * from "./workspace";
export * from "./qa";
