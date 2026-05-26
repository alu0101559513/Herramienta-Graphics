import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageDropdown from './LanguageDropdown';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { selectAuthUser } from '../features/auth/auth.selectors';

export default function PrivateNavbar() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const user = useAppSelector(selectAuthUser);

  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const storedTheme = localStorage.getItem('theme');

    if (storedTheme === 'light' || storedTheme === 'dark') {
      return storedTheme;
    }

    if (document.documentElement.classList.contains('dark')) {
      return 'dark';
    }

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    document.documentElement.style.colorScheme = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!menuRef.current) return;

      if (!menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    window.addEventListener('mousedown', handleClickOutside);
    return () => window.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleLogout = () => {
    dispatch({ type: 'auth/logout' });
    navigate('/auth', { replace: true });
  };

  const handleGoToSettings = () => {
    setIsMenuOpen(false);
    navigate('/settings');
  };

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    [
      'private-navbar-nav-link',
      isActive ? 'private-navbar-nav-link-active' : 'private-navbar-nav-link-inactive',
    ].join(' ');

  const themeAriaLabel =
    theme === 'dark'
      ? t('navigation.theme.switchToLight')
      : t('navigation.theme.switchToDark');

  return (
    <header className="private-navbar-theme theme-transition app-navbar">
      <div className="app-navbar-container">
        <Link to="/" className="app-brand-link">
          <div className="app-brand-icon-wrap">
            <span className="material-symbols-outlined app-brand-icon">bar_chart</span>
          </div>

          <span className="app-brand-text theme-transition">{t('navigation.brand')}</span>
        </Link>

        <div className="app-navbar-actions">
          <nav className="private-navbar-nav">
            <NavLink to="/analysis" className={navLinkClass}>
              {t('navigation.analysis')}
            </NavLink>
          </nav>

          <div className="app-navbar-divider-group theme-transition">
            <button
              type="button"
              onClick={toggleTheme}
              className="app-icon-btn no-border"
              aria-label={themeAriaLabel}
              title={themeAriaLabel}
            >
              <span className="material-symbols-outlined app-icon-btn-symbol">
                {theme === 'dark' ? 'light_mode' : 'dark_mode'}
              </span>
            </button>

            <LanguageDropdown />

            <div ref={menuRef} className="private-navbar-profile-wrap">
              <button
                type="button"
                onClick={() => setIsMenuOpen((prev) => !prev)}
                className="private-navbar-profile-btn"
                aria-label={t('navigation.profileMenu')}
              >
                <div className="private-navbar-profile-text">
                  <p className="private-navbar-profile-name">
                    {user?.username ?? t('navigation.profile')}
                  </p>
                  <p className="private-navbar-profile-email">{user?.email ?? ''}</p>
                </div>

                <span className="material-symbols-outlined private-navbar-profile-caret">
                  expand_more
                </span>
              </button>

              {isMenuOpen ? (
                <div className="app-dropdown private-navbar-menu">
                  <button
                    type="button"
                    onClick={handleGoToSettings}
                    className="private-navbar-menu-btn private-navbar-menu-btn-default"
                  >
                    <span className="material-symbols-outlined private-navbar-menu-icon">
                      settings
                    </span>
                    <span>{t('navigation.settings')}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="private-navbar-menu-btn private-navbar-menu-btn-danger"
                  >
                    <span className="material-symbols-outlined private-navbar-menu-icon-danger">
                      logout
                    </span>
                    <span>{t('navigation.logout')}</span>
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
