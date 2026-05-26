import { createAsyncThunk } from '@reduxjs/toolkit';
import { mapBackendErrorToI18nKey } from './auth.error';
import type {
  ApiMessageResponse,
  AuthUser,
  ChangePasswordRequest,
  LoginRequest,
  RegisterRequest,
  RegisterResponse,
  TokenResponse,
  UpdateUserRequest,
} from './auth.types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

export const AUTH_TOKEN_STORAGE_KEY = 'auth_token';

/**
 * Returns the configured API base URL.
 *
 * @returns Backend base URL.
 */
function getApiBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new Error('Missing VITE_API_BASE_URL environment variable');
  }

  return API_BASE_URL;
}

/**
 * Reads the persisted auth token from local storage.
 *
 * @returns Stored bearer token.
 */
function getStoredToken(): string {
  const token = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);

  if (!token) {
    throw new Error('No stored session');
  }

  return token;
}

/**
 * Builds JSON request headers with an optional bearer token.
 *
 * @param token Optional bearer token.
 * @returns Fetch headers for JSON requests.
 */
function buildJsonHeaders(token?: string): HeadersInit {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

/**
 * Checks whether a value is a plain object-like record.
 *
 * @param value Candidate value.
 * @returns True when the value is an object record.
 */
function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/**
 * Extracts a human-readable backend error message from a failed response.
 *
 * @param response Failed fetch response.
 * @returns Error message suitable for the UI.
 */
async function extractBackendErrorMessage(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json();

    if (isObject(data) && 'detail' in data) {
      const detail = data.detail;

      if (typeof detail === 'string') {
        return detail;
      }

      if (Array.isArray(detail) && detail.length > 0) {
        const firstError = detail[0];

        if (isObject(firstError) && typeof firstError.msg === 'string') {
          return firstError.msg;
        }
      }
    }

    if (isObject(data) && typeof data.message === 'string') {
      return data.message;
    }

    return 'Unknown error';
  } catch {
    return 'Unknown error';
  }
}

/**
 * Performs a JSON request and throws a normalized error when it fails.
 *
 * @typeParam TResponse Expected JSON response shape.
 * @param path Relative API path.
 * @param options Fetch options.
 * @returns Parsed JSON payload.
 */
async function requestJson<TResponse>(
  path: string,
  options: RequestInit = {},
): Promise<TResponse> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, options);

  if (!response.ok) {
    throw new Error(await extractBackendErrorMessage(response));
  }

  return (await response.json()) as TResponse;
}

/**
 * Maps a thrown auth error to the thunk rejection payload.
 *
 * @param error Thrown error value.
 * @param thunkApi Redux thunk API.
 * @returns Rejection payload for the thunk.
 */
function handleAuthThunkError(
  error: unknown,
  thunkApi: { rejectWithValue: (value: string) => unknown },
): unknown {
  const message = error instanceof Error ? error.message : 'Unknown error';
  return thunkApi.rejectWithValue(mapBackendErrorToI18nKey(message));
}

/**
 * Sends the login request to the backend.
 *
 * @param payload Login credentials.
 * @returns Token response from the backend.
 */
async function loginRequest(payload: LoginRequest): Promise<TokenResponse> {
  return requestJson<TokenResponse>('/auth/login', {
    method: 'POST',
    headers: buildJsonHeaders(),
    body: JSON.stringify(payload),
  });
}

/**
 * Sends the register request to the backend.
 *
 * @param payload Registration payload.
 * @returns Registration response.
 */
async function registerRequest(payload: RegisterRequest): Promise<RegisterResponse> {
  return requestJson<RegisterResponse>('/auth/register', {
    method: 'POST',
    headers: buildJsonHeaders(),
    body: JSON.stringify(payload),
  });
}

/**
 * Fetches the current authenticated user.
 *
 * @param token Bearer token.
 * @returns Authenticated user profile.
 */
async function meRequest(token: string): Promise<AuthUser> {
  return requestJson<AuthUser>('/auth/me', {
    method: 'GET',
    headers: buildJsonHeaders(token),
  });
}

/**
 * Updates the authenticated user profile.
 *
 * @param token Bearer token.
 * @param payload Profile update payload.
 * @returns Backend message response.
 */
async function updateUserRequest(
  token: string,
  payload: UpdateUserRequest,
): Promise<ApiMessageResponse> {
  return requestJson<ApiMessageResponse>('/auth/me', {
    method: 'PATCH',
    headers: buildJsonHeaders(token),
    body: JSON.stringify(payload),
  });
}

/**
 * Updates the authenticated user password.
 *
 * @param token Bearer token.
 * @param payload Password change payload.
 * @returns Backend message response.
 */
async function changePasswordRequest(
  token: string,
  payload: ChangePasswordRequest,
): Promise<ApiMessageResponse> {
  return requestJson<ApiMessageResponse>('/auth/password', {
    method: 'PATCH',
    headers: buildJsonHeaders(token),
    body: JSON.stringify(payload),
  });
}

/**
 * Deletes the authenticated account.
 *
 * @param token Bearer token.
 * @returns Backend message response.
 */
async function deleteAccountRequest(token: string): Promise<ApiMessageResponse> {
  return requestJson<ApiMessageResponse>('/auth/me', {
    method: 'DELETE',
    headers: buildJsonHeaders(token),
  });
}

export const loginUser = createAsyncThunk<
  { token: string; user: AuthUser },
  LoginRequest,
  { rejectValue: string }
>(
  'auth/loginUser',
  async (
    payload,
    thunkApi,
  ): Promise<
    { token: string; user: AuthUser } | ReturnType<typeof thunkApi.rejectWithValue>
  > => {
    try {
      const tokenResponse = await loginRequest(payload);
      const user = await meRequest(tokenResponse.access_token);

      localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, tokenResponse.access_token);

      return {
        token: tokenResponse.access_token,
        user,
      };
    } catch (error: unknown) {
      return handleAuthThunkError(error, thunkApi) as any;
    }
  },
);

export const registerUser = createAsyncThunk<
  RegisterResponse,
  RegisterRequest,
  { rejectValue: string }
>(
  'auth/registerUser',
  async (
    payload,
    thunkApi,
  ): Promise<RegisterResponse | ReturnType<typeof thunkApi.rejectWithValue>> => {
    try {
      await registerRequest(payload);

      return {
        message: 'auth.register.success',
      };
    } catch (error: unknown) {
      return handleAuthThunkError(error, thunkApi) as any;
    }
  },
);

export const restoreSession = createAsyncThunk<
  { token: string; user: AuthUser },
  void,
  { rejectValue: string }
>('auth/restoreSession', async (_, thunkApi) => {
  const token = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);

  if (!token) {
    return thunkApi.rejectWithValue('auth.session.noStoredSession');
  }

  try {
    const user = await meRequest(token);

    return {
      token,
      user,
    };
  } catch {
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    return thunkApi.rejectWithValue('auth.session.restoreFailed');
  }
});

export const updateAuthenticatedUser = createAsyncThunk<
  { user: AuthUser; successMessage: string },
  UpdateUserRequest,
  { rejectValue: string }
>(
  'auth/updateAuthenticatedUser',
  async (
    payload,
    thunkApi,
  ): Promise<
    | { user: AuthUser; successMessage: string }
    | ReturnType<typeof thunkApi.rejectWithValue>
  > => {
    try {
      const token = getStoredToken();

      await updateUserRequest(token, payload);
      const user = await meRequest(token);

      return {
        user,
        successMessage: 'settings.profile.updateSuccess',
      };
    } catch (error: unknown) {
      return handleAuthThunkError(error, thunkApi) as any;
    }
  },
);

export const changeAuthenticatedUserPassword = createAsyncThunk<
  { successMessage: string },
  ChangePasswordRequest,
  { rejectValue: string }
>(
  'auth/changeAuthenticatedUserPassword',
  async (
    payload,
    thunkApi,
  ): Promise<
    { successMessage: string } | ReturnType<typeof thunkApi.rejectWithValue>
  > => {
    try {
      const token = getStoredToken();

      await changePasswordRequest(token, payload);

      return {
        successMessage: 'settings.password.updateSuccess',
      };
    } catch (error: unknown) {
      return handleAuthThunkError(error, thunkApi) as any;
    }
  },
);

export const deleteAuthenticatedAccount = createAsyncThunk<
  { successMessage: string },
  void,
  { rejectValue: string }
>(
  'auth/deleteAuthenticatedAccount',
  async (
    _,
    thunkApi,
  ): Promise<
    { successMessage: string } | ReturnType<typeof thunkApi.rejectWithValue>
  > => {
    try {
      const token = getStoredToken();

      await deleteAccountRequest(token);
      localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);

      return {
        successMessage: 'settings.account.deleteSuccess',
      };
    } catch (error: unknown) {
      return handleAuthThunkError(error, thunkApi) as any;
    }
  },
);
