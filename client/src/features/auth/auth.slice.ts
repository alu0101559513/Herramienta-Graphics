import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { authInitialState } from './auth.state';
import {
  AUTH_TOKEN_STORAGE_KEY,
  changeAuthenticatedUserPassword,
  deleteAuthenticatedAccount,
  loginUser,
  registerUser,
  restoreSession,
  updateAuthenticatedUser,
} from './auth.thunks';
import type { AuthState, AuthUser } from './auth.types';

/**
 * Helper function to reset the login form to its initial state.
 *
 * @param state Current auth state.
 */
function resetLoginForm(state: AuthState) {
  state.loginForm = {
    username: '',
    password: '',
  };
}
/**
 * Helper function to reset the registration form to its initial state.
 *
 * @param state Current auth state.
 */
function resetRegisterForm(state: AuthState) {
  state.registerForm = {
    username: '',
    email: '',
    password: '',
  };
}
/**
 * Helper function to reset the settings profile form with the provided user data or to empty values if no user is provided.
 *
 * @param state Current auth state.
 * @param user Current authenticated user data, or null to reset to empty values.
 */
function resetSettingsProfileForm(state: AuthState, user?: AuthUser | null) {
  state.settingsProfileForm = {
    username: user?.username ?? '',
    email: user?.email ?? '',
  };
}
/**
 * Helper function to reset the settings password form to its initial state.
 *
 * @param state Current auth state.
 */
function resetSettingsPasswordFormState(state: AuthState) {
  state.settingsPasswordForm = {
    currentPassword: '',
    newPassword: '',
  };
}
/**
 * Helper function to clear the authentication session data from the state and localStorage.
 *
 * @param state Current auth state.
 */
function clearSession(state: AuthState) {
  state.token = null;
  state.user = null;
  state.isAuthenticated = false;
}
/**
 * Helper function to reset all forms to their initial state.
 *
 * @param state Current auth state.
 */
function resetAllForms(state: AuthState) {
  resetLoginForm(state);
  resetRegisterForm(state);
  resetSettingsProfileForm(state, null);
  resetSettingsPasswordFormState(state);
}

const authSlice = createSlice({
  name: 'auth',
  initialState: authInitialState,
  reducers: {
    setLoginField: (
      state,
      action: PayloadAction<{
        field: keyof typeof state.loginForm;
        value: string;
      }>,
    ) => {
      state.loginForm[action.payload.field] = action.payload.value;
    },

    setRegisterField: (
      state,
      action: PayloadAction<{
        field: keyof typeof state.registerForm;
        value: string;
      }>,
    ) => {
      state.registerForm[action.payload.field] = action.payload.value;
    },

    setSettingsProfileField: (
      state,
      action: PayloadAction<{
        field: keyof typeof state.settingsProfileForm;
        value: string;
      }>,
    ) => {
      state.settingsProfileForm[action.payload.field] = action.payload.value;
    },

    setSettingsPasswordField: (
      state,
      action: PayloadAction<{
        field: keyof typeof state.settingsPasswordForm;
        value: string;
      }>,
    ) => {
      state.settingsPasswordForm[action.payload.field] = action.payload.value;
    },

    hydrateSettingsProfileFormFromUser: (state) => {
      resetSettingsProfileForm(state, state.user);
    },

    resetSettingsPasswordForm: (state) => {
      resetSettingsPasswordFormState(state);
    },

    setAuthError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },

    clearAuthError: (state) => {
      state.error = null;
    },

    clearSuccessMessage: (state) => {
      state.successMessage = null;
    },

    clearRegisterSuccessMessage: (state) => {
      state.successMessage = null;
    },

    logout: (state) => {
      localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);

      clearSession(state);
      resetAllForms(state);

      state.isLoading = false;
      state.error = null;
      state.successMessage = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.isAuthenticated = true;
        state.error = null;
        state.successMessage = null;

        resetLoginForm(state);
        resetSettingsProfileForm(state, action.payload.user);
      })
      .addCase(loginUser.rejected, (state, action: PayloadAction<string | undefined>) => {
        state.isLoading = false;
        state.error = action.payload ?? 'auth.backend.unknownError';
      })

      .addCase(registerUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.error = null;
        state.successMessage = action.payload.message;

        resetRegisterForm(state);
      })
      .addCase(
        registerUser.rejected,
        (state, action: PayloadAction<string | undefined>) => {
          state.isLoading = false;
          state.error = action.payload ?? 'auth.backend.unknownError';
        },
      )

      .addCase(restoreSession.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(restoreSession.fulfilled, (state, action) => {
        state.isLoading = false;
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.isAuthenticated = true;
        state.error = null;

        resetSettingsProfileForm(state, action.payload.user);
      })
      .addCase(restoreSession.rejected, (state, action) => {
        clearSession(state);
        state.isLoading = false;

        if (
          action.payload !== 'auth.session.noStoredSession' &&
          action.payload !== 'auth.session.restoreFailed'
        ) {
          state.error = action.payload ?? 'auth.backend.unknownError';
        }
      })

      .addCase(updateAuthenticatedUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(updateAuthenticatedUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.successMessage = action.payload.successMessage;

        resetSettingsProfileForm(state, action.payload.user);
      })
      .addCase(
        updateAuthenticatedUser.rejected,
        (state, action: PayloadAction<string | undefined>) => {
          state.isLoading = false;
          state.error = action.payload ?? 'auth.backend.unknownError';
        },
      )

      .addCase(changeAuthenticatedUserPassword.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(changeAuthenticatedUserPassword.fulfilled, (state, action) => {
        state.isLoading = false;
        state.successMessage = action.payload.successMessage;

        resetSettingsPasswordFormState(state);
      })
      .addCase(
        changeAuthenticatedUserPassword.rejected,
        (state, action: PayloadAction<string | undefined>) => {
          state.isLoading = false;
          state.error = action.payload ?? 'auth.backend.unknownError';
        },
      )

      .addCase(deleteAuthenticatedAccount.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(deleteAuthenticatedAccount.fulfilled, (state) => {
        clearSession(state);
        resetAllForms(state);

        state.isLoading = false;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(
        deleteAuthenticatedAccount.rejected,
        (state, action: PayloadAction<string | undefined>) => {
          state.isLoading = false;
          state.error = action.payload ?? 'auth.backend.unknownError';
        },
      );
  },
});

export const {
  setLoginField,
  setRegisterField,
  setSettingsProfileField,
  setSettingsPasswordField,
  hydrateSettingsProfileFormFromUser,
  resetSettingsPasswordForm,
  setAuthError,
  clearAuthError,
  clearSuccessMessage,
  clearRegisterSuccessMessage,
  logout,
} = authSlice.actions;

export const authReducer = authSlice.reducer;
