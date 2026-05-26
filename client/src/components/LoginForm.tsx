import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

type LoginFormProps = {
  username: string;
  password: string;
  isLoading: boolean;
  error: string | null;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: () => void;
};

export default function LoginForm({
  username,
  password,
  isLoading,
  error,
  onUsernameChange,
  onPasswordChange,
  onSubmit,
}: LoginFormProps) {
  const { t } = useTranslation();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div>
        <label className="auth-form-label">{t('auth.login.usernameLabel')}</label>
        <input
          value={username}
          onChange={(event) => onUsernameChange(event.target.value)}
          className="app-input auth-form-input"
          placeholder={t('auth.login.usernamePlaceholder')}
          autoComplete="username"
        />
      </div>

      <div>
        <label className="auth-form-label">{t('auth.login.passwordLabel')}</label>
        <input
          type="password"
          value={password}
          onChange={(event) => onPasswordChange(event.target.value)}
          className="app-input auth-form-input"
          placeholder={t('auth.login.passwordPlaceholder')}
          autoComplete="current-password"
        />
      </div>

      {error ? <div className="app-error auth-form-feedback">{t(error)}</div> : null}

      <button type="submit" disabled={isLoading} className="auth-form-submit">
        {isLoading ? t('auth.login.loading') : t('auth.login.submit')}
      </button>
    </form>
  );
}
