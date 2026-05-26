import { useTranslation } from 'react-i18next';

export default function AppFooter() {
  const { t } = useTranslation();

  return (
    <footer className="app-footer-theme app-footer-base theme-transition">
      <div className="app-footer-inner">
        <p className="app-footer-text">{t('footer.copyright')}</p>
      </div>
    </footer>
  );
}
