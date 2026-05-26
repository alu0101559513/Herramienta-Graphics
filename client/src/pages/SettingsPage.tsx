import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import PrivateLayout from '../components/PrivateLayout';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import {
  clearAuthError,
  clearSuccessMessage,
  hydrateSettingsProfileFormFromUser,
  setSettingsPasswordField,
  setSettingsProfileField,
} from '../features/auth/auth.slice';
import {
  selectAuthError,
  selectAuthIsLoading,
  selectAuthUser,
  selectIsAuthenticated,
} from '../features/auth/auth.selectors';
import {
  changeAuthenticatedUserPassword,
  deleteAuthenticatedAccount,
  updateAuthenticatedUser,
} from '../features/auth/auth.thunks';
import '../styles/pages.css';

export default function SettingsPage() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const authState = useAppSelector((state) => state.auth);
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const user = useAppSelector(selectAuthUser);
  const isLoading = useAppSelector(selectAuthIsLoading);
  const error = useAppSelector(selectAuthError);

  useEffect(() => {
    dispatch(hydrateSettingsProfileFormFromUser());
  }, [dispatch, user]);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/auth', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleProfileSubmit = async () => {
    dispatch(clearAuthError());
    dispatch(clearSuccessMessage());

    await dispatch(
      updateAuthenticatedUser({
        username: authState.settingsProfileForm.username.trim(),
        email: authState.settingsProfileForm.email.trim(),
      }),
    );
  };

  const handlePasswordSubmit = async () => {
    dispatch(clearAuthError());
    dispatch(clearSuccessMessage());

    await dispatch(
      changeAuthenticatedUserPassword({
        current_password: authState.settingsPasswordForm.currentPassword,
        new_password: authState.settingsPasswordForm.newPassword,
      }),
    );
  };

  const openDeleteModal = () => {
    dispatch(clearAuthError());
    dispatch(clearSuccessMessage());
    setIsDeleteModalOpen(true);
  };

  const closeDeleteModal = () => {
    if (isLoading) {
      return;
    }

    setIsDeleteModalOpen(false);
  };

  const handleDeleteAccount = async () => {
    dispatch(clearAuthError());
    dispatch(clearSuccessMessage());

    const result = await dispatch(deleteAuthenticatedAccount());

    if (deleteAuthenticatedAccount.fulfilled.match(result)) {
      setIsDeleteModalOpen(false);
      navigate('/auth', { replace: true });
    }
  };

  return (
    <PrivateLayout>
      <main className="settings-page-main">
        <div className="settings-header">
          <h1 className="settings-title">{t('settings.title')}</h1>
          <p className="settings-subtitle">{t('settings.subtitle')}</p>
        </div>

        {error ? <div className="app-error settings-feedback">{t(error)}</div> : null}

        {authState.successMessage ? (
          <div className="app-success settings-feedback">
            {t(authState.successMessage)}
          </div>
        ) : null}

        <div className="settings-grid">
          <section className="app-panel settings-panel">
            <h2 className="settings-panel-title">{t('settings.profile.title')}</h2>
            <p className="settings-panel-subtitle">{t('settings.profile.subtitle')}</p>

            <div className="settings-form-stack">
              <div>
                <label className="settings-field-label">
                  {t('settings.profile.usernameLabel')}
                </label>
                <input
                  value={authState.settingsProfileForm.username}
                  onChange={(event) =>
                    dispatch(
                      setSettingsProfileField({
                        field: 'username',
                        value: event.target.value,
                      }),
                    )
                  }
                  className="app-input settings-input"
                />
              </div>

              <div>
                <label className="settings-field-label">
                  {t('settings.profile.emailLabel')}
                </label>
                <input
                  type="email"
                  value={authState.settingsProfileForm.email}
                  onChange={(event) =>
                    dispatch(
                      setSettingsProfileField({
                        field: 'email',
                        value: event.target.value,
                      }),
                    )
                  }
                  className="app-input settings-input"
                />
              </div>

              <button
                type="button"
                onClick={handleProfileSubmit}
                disabled={isLoading}
                className="settings-btn-primary"
              >
                {isLoading ? t('settings.profile.saving') : t('settings.profile.submit')}
              </button>
            </div>
          </section>

          <section className="app-panel settings-panel">
            <h2 className="settings-panel-title">{t('settings.password.title')}</h2>
            <p className="settings-panel-subtitle">{t('settings.password.subtitle')}</p>

            <div className="settings-form-stack">
              <div>
                <label className="settings-field-label">
                  {t('settings.password.currentLabel')}
                </label>
                <input
                  type="password"
                  value={authState.settingsPasswordForm.currentPassword}
                  onChange={(event) =>
                    dispatch(
                      setSettingsPasswordField({
                        field: 'currentPassword',
                        value: event.target.value,
                      }),
                    )
                  }
                  className="app-input settings-input"
                />
              </div>

              <div>
                <label className="settings-field-label">
                  {t('settings.password.newLabel')}
                </label>
                <input
                  type="password"
                  value={authState.settingsPasswordForm.newPassword}
                  onChange={(event) =>
                    dispatch(
                      setSettingsPasswordField({
                        field: 'newPassword',
                        value: event.target.value,
                      }),
                    )
                  }
                  className="app-input settings-input"
                />
              </div>

              <button
                type="button"
                onClick={handlePasswordSubmit}
                disabled={isLoading}
                className="settings-btn-primary"
              >
                {isLoading
                  ? t('settings.password.saving')
                  : t('settings.password.submit')}
              </button>
            </div>
          </section>
        </div>

        <section className="settings-danger">
          <h2 className="settings-danger-title">{t('settings.account.title')}</h2>

          <p className="settings-danger-subtitle">{t('settings.account.subtitle')}</p>

          <div className="settings-danger-box">
            <p className="settings-danger-box-title">
              {t('settings.account.whatWillBeDeletedTitle')}
            </p>
            <ul className="settings-danger-list">
              <li>{t('settings.account.whatWillBeDeletedUser')}</li>
              <li>{t('settings.account.whatWillBeDeletedRuns')}</li>
              <li>{t('settings.account.whatWillBeDeletedFiles')}</li>
              <li>{t('settings.account.whatWillBeDeletedResults')}</li>
            </ul>
          </div>

          <button
            type="button"
            onClick={openDeleteModal}
            disabled={isLoading}
            className="settings-btn-danger"
          >
            {t('settings.account.deleteButton')}
          </button>
        </section>

        {isDeleteModalOpen ? (
          <div className="settings-modal-overlay">
            <div className="settings-modal">
              <h3 className="settings-modal-title">
                {t('settings.account.modal.title')}
              </h3>

              <p className="settings-modal-text">
                {t('settings.account.modal.description')}
              </p>

              <div className="settings-modal-warning">
                <p className="settings-modal-warning-title">
                  {t('settings.account.modal.warningTitle')}
                </p>

                <ul className="settings-danger-list">
                  <li>{t('settings.account.whatWillBeDeletedUser')}</li>
                  <li>{t('settings.account.whatWillBeDeletedRuns')}</li>
                  <li>{t('settings.account.whatWillBeDeletedFiles')}</li>
                  <li>{t('settings.account.whatWillBeDeletedResults')}</li>
                </ul>
              </div>

              <div className="settings-modal-actions">
                <button
                  type="button"
                  onClick={closeDeleteModal}
                  disabled={isLoading}
                  className="settings-btn-cancel"
                >
                  {t('settings.account.modal.cancel')}
                </button>

                <button
                  type="button"
                  onClick={handleDeleteAccount}
                  disabled={isLoading}
                  className="settings-btn-danger"
                >
                  {isLoading
                    ? t('settings.account.modal.deleting')
                    : t('settings.account.modal.confirm')}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </PrivateLayout>
  );
}
