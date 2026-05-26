import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useEffect, useState } from 'react';
import LanguageDropdown from './LanguageDropdown';

export default function PublicNavbar() {
  const { t } = useTranslation();
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

  return (
    <header className="public-navbar-theme theme-transition app-navbar">
      <div className="app-navbar-container">
        <Link to="/auth" className="app-brand-link">
          <div className="app-brand-icon-wrap">
            <span className="material-symbols-outlined app-brand-icon">monitoring</span>
          </div>

          <span className="app-brand-text theme-transition">Graphics</span>
        </Link>

        <div className="app-navbar-divider-group theme-transition">
          <button
            onClick={() => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))}
            className="app-icon-btn"
            aria-label={
              theme === 'dark'
                ? t('navigation.theme.switchToLight')
                : t('navigation.theme.switchToDark')
            }
            title={
              theme === 'dark'
                ? t('navigation.theme.switchToLight')
                : t('navigation.theme.switchToDark')
            }
          >
            <span className="material-symbols-outlined app-icon-btn-symbol">
              {theme === 'dark' ? 'light_mode' : 'dark_mode'}
            </span>
          </button>

          <LanguageDropdown />
        </div>
      </div>
    </header>
  );
}
