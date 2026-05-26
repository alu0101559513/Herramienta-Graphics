import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import analysisEs from './es/analysis.json';
import authEs from './es/auth.json';
import commonEs from './es/common.json';
import settingsEs from './es/settings.json';

import analysisEn from './en/analysis.json';
import authEn from './en/auth.json';
import commonEn from './en/common.json';
import settingsEn from './en/settings.json';

const resources = {
  es: {
    translation: {
      ...commonEs,
      ...authEs,
      ...analysisEs,
      ...settingsEs,
    },
  },
  en: {
    translation: {
      ...commonEn,
      ...authEn,
      ...analysisEn,
      ...settingsEn,
    },
  },
};

void i18n.use(initReactI18next).init({
  resources,
  lng: 'es',
  fallbackLng: 'es',
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
