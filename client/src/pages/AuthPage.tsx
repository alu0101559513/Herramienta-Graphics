import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import PublicLayout from '../components/PublicLayout';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import {
  clearAuthError,
  clearRegisterSuccessMessage,
  setAuthError,
  setLoginField,
  setRegisterField,
} from '../features/auth/auth.slice';
import {
  selectAuthError,
  selectAuthIsLoading,
  selectIsAuthenticated,
  selectLoginForm,
  selectRegisterForm,
  selectAuthSuccessMessage,
} from '../features/auth/auth.selectors';
import { loginUser, registerUser, restoreSession } from '../features/auth/auth.thunks';
import {
  validateLoginForm,
  validateRegisterForm,
} from '../features/auth/auth.validation';
import LoginForm from '../components/LoginForm';
import RegisterForm from '../components/RegisterForm';
import '../styles/pages.css';

type AuthMode = 'login' | 'register';

export default function AuthPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const loginForm = useAppSelector(selectLoginForm);
  const registerForm = useAppSelector(selectRegisterForm);
  const isLoading = useAppSelector(selectAuthIsLoading);
  const error = useAppSelector(selectAuthError);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const successMessage = useAppSelector(selectAuthSuccessMessage);

  const [mode, setMode] = useState<AuthMode>('login');

  useEffect(() => {
    void dispatch(restoreSession());
  }, [dispatch]);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleModeChange = (nextMode: AuthMode) => {
    setMode(nextMode);
    dispatch(clearAuthError());
    dispatch(clearRegisterSuccessMessage());
  };

  const handleLoginSubmit = async () => {
    dispatch(clearRegisterSuccessMessage());

    const validationError = validateLoginForm({
      username: loginForm.username,
      password: loginForm.password,
    });

    if (validationError) {
      dispatch(setAuthError(validationError));
      return;
    }

    try {
      await dispatch(
        loginUser({
          username: loginForm.username.trim(),
          password: loginForm.password,
        }),
      ).unwrap();

      navigate('/', { replace: true });
    } catch {}
  };

  const handleRegisterSubmit = async () => {
    dispatch(clearRegisterSuccessMessage());

    const validationError = validateRegisterForm({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
    });

    if (validationError) {
      dispatch(setAuthError(validationError));
      return;
    }

    try {
      await dispatch(
        registerUser({
          username: registerForm.username.trim(),
          email: registerForm.email.trim(),
          password: registerForm.password,
        }),
      ).unwrap();

      setMode('login');
    } catch {}
  };

  return (
    <PublicLayout>
      <main className="auth-page-main">
        <div className="auth-page-grid">
          <section className="auth-hero">
            <span className="auth-hero-badge">{t('auth.hero.badge')}</span>

            <h1 className="auth-hero-title">{t('auth.hero.title')}</h1>

            <p className="auth-hero-description">{t('auth.hero.description')}</p>
          </section>

          <section className="auth-form-wrap">
            <div className="app-panel auth-form-panel">
              <div className="auth-tabs">
                <button
                  type="button"
                  onClick={() => handleModeChange('login')}
                  className={`auth-tab ${
                    mode === 'login' ? 'auth-tab-active' : 'auth-tab-inactive'
                  }`}
                >
                  {t('auth.tabs.login')}
                </button>

                <button
                  type="button"
                  onClick={() => handleModeChange('register')}
                  className={`auth-tab ${
                    mode === 'register' ? 'auth-tab-active' : 'auth-tab-inactive'
                  }`}
                >
                  {t('auth.tabs.register')}
                </button>
              </div>

              <div className="auth-form-head">
                <h2 className="auth-form-title">
                  {mode === 'login' ? t('auth.login.title') : t('auth.register.title')}
                </h2>
                <p className="auth-form-subtitle">
                  {mode === 'login'
                    ? t('auth.login.subtitle')
                    : t('auth.register.subtitle')}
                </p>
              </div>

              {mode === 'login' ? (
                <LoginForm
                  username={loginForm.username}
                  password={loginForm.password}
                  isLoading={isLoading}
                  error={error}
                  onUsernameChange={(value) =>
                    dispatch(setLoginField({ field: 'username', value }))
                  }
                  onPasswordChange={(value) =>
                    dispatch(setLoginField({ field: 'password', value }))
                  }
                  onSubmit={handleLoginSubmit}
                />
              ) : (
                <RegisterForm
                  username={registerForm.username}
                  email={registerForm.email}
                  password={registerForm.password}
                  isLoading={isLoading}
                  error={error}
                  successMessage={successMessage}
                  onUsernameChange={(value) =>
                    dispatch(setRegisterField({ field: 'username', value }))
                  }
                  onEmailChange={(value) =>
                    dispatch(setRegisterField({ field: 'email', value }))
                  }
                  onPasswordChange={(value) =>
                    dispatch(setRegisterField({ field: 'password', value }))
                  }
                  onSubmit={handleRegisterSubmit}
                />
              )}
            </div>
          </section>
        </div>
      </main>
    </PublicLayout>
  );
}
