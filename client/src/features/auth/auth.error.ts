function normalizeMessage(message: string): string {
  return message.replace(/^Value error,\s*/i, '').trim();
}

export function mapBackendErrorToI18nKey(message: string): string {
  const normalized = normalizeMessage(message);

  switch (normalized) {
    case 'Username already exists':
      return 'auth.backend.usernameAlreadyExists';

    case 'Email already exists':
      return 'auth.backend.emailAlreadyExists';

    case 'Invalid credentials':
      return 'auth.backend.invalidCredentials';

    case 'Current password incorrect':
      return 'auth.backend.currentPasswordIncorrect';

    case 'Password must be at least 8 characters':
      return 'auth.validation.passwordMinLength';

    case 'Password must contain an uppercase letter':
      return 'auth.validation.passwordUppercase';

    case 'Password must contain a lowercase letter':
      return 'auth.validation.passwordLowercase';

    case 'Password must contain a number':
      return 'auth.validation.passwordNumber';

    default:
      return 'auth.backend.unknownError';
  }
}
