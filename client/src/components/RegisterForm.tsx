import type { FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

type RegisterFormProps = {
  username: string;
  email: string;
  password: string;
  isLoading: boolean;
  error: string | null;
  successMessage: string | null;
  onUsernameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: () => void;
};

export default function RegisterForm({
  username,
  email,
  password,
  isLoading,
  error,
  successMessage,
  onUsernameChange,
  onEmailChange,
  onPasswordChange,
  onSubmit,
}: RegisterFormProps) {
  const { t } = useTranslation();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div>
        <label className="auth-form-label">{t('auth.register.usernameLabel')}</label>
        <input
          value={username}
          onChange={(event) => onUsernameChange(event.target.value)}
          className="app-input auth-form-input"
          placeholder={t('auth.register.usernamePlaceholder')}
          autoComplete="username"
        />
      </div>

      <div>
        <label className="auth-form-label">{t('auth.register.emailLabel')}</label>
        <input
          type="email"
          value={email}
          onChange={(event) => onEmailChange(event.target.value)}
          className="app-input auth-form-input"
          placeholder={t('auth.register.emailPlaceholder')}
          autoComplete="email"
        />
      </div>

      <div>
        <label className="auth-form-label">{t('auth.register.passwordLabel')}</label>
        <input
          type="password"
          value={password}
          onChange={(event) => onPasswordChange(event.target.value)}
          className="app-input auth-form-input"
          placeholder={t('auth.register.passwordPlaceholder')}
          autoComplete="new-password"
        />
      </div>

      {error ? <div className="app-error auth-form-feedback">{t(error)}</div> : null}

      {successMessage ? (
        <div className="app-success auth-form-feedback">{t(successMessage)}</div>
      ) : null}

      <button type="submit" disabled={isLoading} className="auth-form-submit">
        {isLoading ? t('auth.register.loading') : t('auth.register.submit')}
      </button>
    </form>
  );
}
