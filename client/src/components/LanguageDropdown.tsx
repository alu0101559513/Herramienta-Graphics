import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

type LanguageOption = {
  code: 'es' | 'en';
  label: string;
  flag: string;
};

const LANGUAGE_OPTIONS: LanguageOption[] = [
  {
    code: 'es',
    label: 'Español',
    flag: '🇪🇸',
  },
  {
    code: 'en',
    label: 'English',
    flag: '🇬🇧',
  },
];

export default function LanguageDropdown() {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const currentLanguage =
    LANGUAGE_OPTIONS.find((option) => option.code === i18n.language) ??
    LANGUAGE_OPTIONS[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!containerRef.current) {
        return;
      }

      if (!containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    window.addEventListener('mousedown', handleClickOutside);

    return () => {
      window.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSelectLanguage = (languageCode: 'es' | 'en') => {
    void i18n.changeLanguage(languageCode);
    setIsOpen(false);
  };

  return (
    <div ref={containerRef} className="lang-dropdown-wrap">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="app-select-trigger theme-transition lang-dropdown-trigger"
      >
        <span className="lang-flag">{currentLanguage.flag}</span>
        <span className="lang-label">{currentLanguage.label}</span>
        <span className="material-symbols-outlined lang-caret">expand_more</span>
      </button>

      {isOpen ? (
        <div className="app-dropdown theme-transition lang-dropdown-menu">
          {LANGUAGE_OPTIONS.map((option) => {
            const isActive = option.code === currentLanguage.code;

            return (
              <button
                key={option.code}
                type="button"
                onClick={() => handleSelectLanguage(option.code)}
                className={`lang-dropdown-item ${
                  isActive ? 'lang-dropdown-item-active' : 'lang-dropdown-item-inactive'
                }`}
              >
                <span className="lang-dropdown-item-left">
                  <span className="lang-flag">{option.flag}</span>
                  <span>{option.label}</span>
                </span>

                {isActive ? (
                  <span className="material-symbols-outlined lang-dropdown-check">
                    check
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
