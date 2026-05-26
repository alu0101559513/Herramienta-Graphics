import type { AuthState } from './auth.types';

export const authInitialState: AuthState = {
  loginForm: {
    username: '',
    password: '',
  },

  registerForm: {
    username: '',
    email: '',
    password: '',
  },

  settingsProfileForm: {
    username: '',
    email: '',
  },

  settingsPasswordForm: {
    currentPassword: '',
    newPassword: '',
  },

  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  successMessage: null,
};
