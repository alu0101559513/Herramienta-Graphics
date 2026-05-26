export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type?: 'bearer' | string;
}

export interface RegisterResponse {
  message: string;
}

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

export interface UpdateUserRequest {
  username?: string;
  email?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ApiMessageResponse {
  message: string;
}

export interface LoginFormData {
  username: string;
  password: string;
}

export interface RegisterFormData {
  username: string;
  email: string;
  password: string;
}

export interface SettingsProfileFormData {
  username: string;
  email: string;
}

export interface SettingsPasswordFormData {
  currentPassword: string;
  newPassword: string;
}

export interface AuthState {
  loginForm: LoginFormData;
  registerForm: RegisterFormData;
  settingsProfileForm: SettingsProfileFormData;
  settingsPasswordForm: SettingsPasswordFormData;
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  successMessage: string | null;
}
