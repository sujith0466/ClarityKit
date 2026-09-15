/**
 * Frontend Authentication Types
 */

export interface AuthUser {
  readonly user_id: string;
  readonly email: string;
  readonly name: string;
  readonly is_active: boolean;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface AuthResponse {
  readonly status: "success";
  readonly user: AuthUser;
  readonly token: string;
}

export interface AuthState {
  readonly user: AuthUser | null;
  readonly token: string | null;
  readonly isAuthenticated: boolean;
  readonly isLoading: boolean;
  readonly error: string | null;
}
