import type { RootState } from '../../app/store';

export const selectAuthState = (state: RootState) => state.auth;
export const selectLoginForm = (state: RootState) => state.auth.loginForm;
export const selectRegisterForm = (state: RootState) => state.auth.registerForm;
export const selectSettingsProfileForm = (state: RootState) =>
  state.auth.settingsProfileForm;
export const selectSettingsPasswordForm = (state: RootState) =>
  state.auth.settingsPasswordForm;
export const selectAuthUser = (state: RootState) => state.auth.user;
export const selectAuthToken = (state: RootState) => state.auth.token;
export const selectIsAuthenticated = (state: RootState) => state.auth.isAuthenticated;
export const selectAuthIsLoading = (state: RootState) => state.auth.isLoading;
export const selectAuthError = (state: RootState) => state.auth.error;
export const selectAuthSuccessMessage = (state: RootState) => state.auth.successMessage;
