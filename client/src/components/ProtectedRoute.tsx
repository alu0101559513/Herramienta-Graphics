import { Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAppSelector } from '../app/hooks';
import {
  selectIsAuthenticated,
  selectAuthIsLoading,
} from '../features/auth/auth.selectors';
import type { JSX } from 'react/jsx-runtime';

type ProtectedRouteProps = {
  children: JSX.Element;
};

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { t } = useTranslation();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const isLoading = useAppSelector(selectAuthIsLoading);

  if (isLoading) {
    return (
      <div className="protected-loading">
        <div className="protected-loading-content">
          <div className="protected-loading-spinner" />
          <p className="protected-loading-text">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return children;
}
