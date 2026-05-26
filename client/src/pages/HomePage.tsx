import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import PrivateLayout from '../components/PrivateLayout';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import {
  selectAnalyses,
  selectAnalysisIsLoading,
} from '../features/analysis/analysis.selectors';
import { listAnalyses } from '../features/analysis/analysis.thunks';
import '../styles/pages.css';

const HERO_IMAGE_SRC = '/images/logo.PNG';

function formatDate(value?: string, locale = 'es-ES') {
  if (!value) return '';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return '';

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
  }).format(date);
}
function HeroVisual() {
  return (
    <div className="home-hero-visual relative flex items-center justify-center overflow-visible">
      <div className="absolute inset-0 flex items-center justify-center">
        <svg className="h-[132%] w-[132%]" viewBox="0 0 460 460" aria-hidden="true">
          <circle
            cx="230"
            cy="230"
            r="214"
            fill="none"
            stroke="#ffffff"
            strokeWidth="8"
            strokeDasharray="34 24"
            strokeLinecap="round"
            opacity="0.85"
          >
            <animate
              attributeName="stroke-dashoffset"
              from="0"
              to="-116"
              dur="1.35s"
              repeatCount="indefinite"
            />
          </circle>
        </svg>
      </div>

      <div className="relative z-10 w-full max-w-[760px]">
        <div className="absolute inset-0 rounded-[34px] bg-blue-500/20 opacity-60 blur-3xl" />

        <img
          src={HERO_IMAGE_SRC}
          alt=""
          className="relative z-10 w-full rounded-[28px] object-contain drop-shadow-[0_28px_65px_rgba(15,23,42,0.32)]"
          draggable={false}
        />
      </div>
    </div>
  );
}
export default function HomePage() {
  const { t, i18n } = useTranslation();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const analyses = useAppSelector(selectAnalyses);
  const isLoading = useAppSelector(selectAnalysisIsLoading);

  useEffect(() => {
    void dispatch(listAnalyses());
  }, [dispatch]);

  const locale = i18n.language || 'es-ES';
  const totalAnalyses = analyses.length;

  const recentAnalyses = [...analyses]
    .sort(
      (a, b) =>
        (b.created_at ? new Date(b.created_at).getTime() : 0) -
        (a.created_at ? new Date(a.created_at).getTime() : 0),
    )
    .slice(0, 4);

  const latestAnalysis = [...analyses].sort(
    (a, b) =>
      (b.created_at ? new Date(b.created_at).getTime() : 0) -
      (a.created_at ? new Date(a.created_at).getTime() : 0),
  )[0];

  const latestAnalysisDate = latestAnalysis?.created_at
    ? formatDate(latestAnalysis.created_at, locale)
    : t('home.stats.latestAnalysis.empty');

  return (
    <PrivateLayout>
      <main className="dashboard-page home-page-main">
        <section className="dashboard-card-muted theme-transition home-hero">
          <div className="home-hero-glow" />

          <div className="home-hero-layout">
            <div className="home-hero-content">
              <span className="home-hero-badge">{t('home.hero.badge')}</span>

              <h1 className="home-hero-title">
                {t('home.hero.titlePrefix')}{' '}
                <span className="home-hero-title-accent">
                  {t('home.hero.titleAccent')}
                </span>
              </h1>

              <p className="home-hero-description">{t('home.hero.description')}</p>

              <div className="home-hero-actions">
                <button
                  type="button"
                  onClick={() => navigate('/analysis')}
                  className="home-primary-btn"
                >
                  <span className="material-symbols-outlined">add_circle</span>
                  {t('home.hero.primaryButton')}
                </button>
              </div>
            </div>

            <HeroVisual />
          </div>
        </section>

        <section className="home-stats-grid">
          <div className="dashboard-card theme-transition home-stat-card">
            <div className="home-stat-icon home-stat-icon-blue">
              <span className="material-symbols-outlined home-stat-icon-symbol">
                folder_open
              </span>
            </div>

            <div>
              <p className="home-stat-label">{t('home.stats.totalProjects.label')}</p>
              <h3 className="home-stat-value">{isLoading ? '-' : totalAnalyses}</h3>
            </div>
          </div>

          <div className="dashboard-card theme-transition home-stat-card">
            <div className="home-stat-icon home-stat-icon-violet">
              <span className="material-symbols-outlined home-stat-icon-symbol">
                history
              </span>
            </div>

            <div>
              <p className="home-stat-label">{t('home.stats.recentProjects.label')}</p>
              <h3 className="home-stat-value">
                {isLoading ? '-' : recentAnalyses.length}
              </h3>
            </div>
          </div>

          <div className="dashboard-card theme-transition home-stat-card">
            <div className="home-stat-icon home-stat-icon-amber">
              <span className="material-symbols-outlined home-stat-icon-symbol">
                event
              </span>
            </div>

            <div>
              <p className="home-stat-label">{t('home.stats.latestAnalysis.label')}</p>
              <h3 className="home-stat-value-date">
                {isLoading ? '-' : latestAnalysisDate}
              </h3>
              <p className="home-stat-subtext">
                {isLoading
                  ? ''
                  : latestAnalysis?.name || t('home.stats.latestAnalysis.empty')}
              </p>
            </div>
          </div>
        </section>

        <section>
          <h2 className="home-recent-title">
            <span className="material-symbols-outlined">history</span>
            {t('home.recentSection.title')}
          </h2>

          {totalAnalyses === 0 && !isLoading ? (
            <div className="dashboard-empty theme-transition home-empty-card">
              <span className="material-symbols-outlined home-empty-icon">
                inventory_2
              </span>
              <h3 className="home-empty-title">{t('home.empty.title')}</h3>
              <p className="home-empty-description">{t('home.empty.description')}</p>
            </div>
          ) : (
            <div className="home-recent-grid">
              {recentAnalyses.map((analysis) => (
                <button
                  key={analysis.id}
                  type="button"
                  onClick={() => navigate(`/analysis/${analysis.id}`)}
                  className="dashboard-card theme-transition home-recent-card text-left"
                >
                  <div className="home-recent-card-header">
                    <span className="material-symbols-outlined home-recent-card-icon">
                      analytics
                    </span>

                    <span className="home-recent-card-date">
                      {analysis.created_at
                        ? formatDate(analysis.created_at, locale)
                        : t('home.recentSection.noDate')}
                    </span>
                  </div>

                  <h3 className="home-recent-card-title">{analysis.name}</h3>

                  <p className="home-recent-card-desc">
                    {analysis.description || t('home.recentSection.noDescription')}
                  </p>
                </button>
              ))}
            </div>
          )}
        </section>
      </main>
    </PrivateLayout>
  );
}
