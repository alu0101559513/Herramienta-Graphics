export type ValidationErrorKey =
  | 'auth.validation.requiredUsername'
  | 'auth.validation.requiredEmail'
  | 'auth.validation.invalidEmail'
  | 'auth.validation.requiredPassword'
  | 'auth.validation.passwordMinLength'
  | 'auth.validation.passwordUppercase'
  | 'auth.validation.passwordLowercase'
  | 'auth.validation.passwordNumber';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
/**
 * Validates the login form data.
 * @param data Form data to validate.
 * @returns Validation error key if validation fails, or null if validation passes.
 */
export function validateLoginForm(data: {
  username: string;
  password: string;
}): ValidationErrorKey | null {
  if (!data.username.trim()) {
    return 'auth.validation.requiredUsername';
  }

  if (!data.password) {
    return 'auth.validation.requiredPassword';
  }

  return null;
}
/**
 * Validates the registration form data.
 * @param data Form data to validate.
 * @returns Validation error key if validation fails, or null if validation passes.
 */
export function validateRegisterForm(data: {
  username: string;
  email: string;
  password: string;
}): ValidationErrorKey | null {
  if (!data.username.trim()) {
    return 'auth.validation.requiredUsername';
  }

  if (!data.email.trim()) {
    return 'auth.validation.requiredEmail';
  }

  if (!EMAIL_REGEX.test(data.email.trim())) {
    return 'auth.validation.invalidEmail';
  }

  if (!data.password) {
    return 'auth.validation.requiredPassword';
  }

  if (data.password.length < 8) {
    return 'auth.validation.passwordMinLength';
  }

  if (!/[A-Z]/.test(data.password)) {
    return 'auth.validation.passwordUppercase';
  }

  if (!/[a-z]/.test(data.password)) {
    return 'auth.validation.passwordLowercase';
  }

  if (!/\d/.test(data.password)) {
    return 'auth.validation.passwordNumber';
  }

  return null;
}
