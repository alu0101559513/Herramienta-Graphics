import { defineConfig } from 'vitepress';

export default defineConfig({
  title: 'Manual de usuario',
  description: 'Guía de uso de la aplicación',
  base: '/Herramienta-Graphics/',

  locales: {
    root: {
      label: 'Español',
      lang: 'es',
      title: 'Manual de usuario',
      description: 'Guía de uso de la aplicación',

      themeConfig: {
        nav: [{ text: 'Inicio', link: '/' }],

        sidebar: [
          {
            text: 'Manual de usuario',
            items: [
              { text: 'Autenticación y configuración', link: '/autenticacion-configuracion' },
              { text: 'Pantalla de inicio', link: '/inicio' },
              { text: 'Análisis', link: '/analisis' },
              { text: 'Detalle del análisis', link: '/analisis-detalle' },
              { text: 'Gráficas', link: '/graficas' },
              { text: 'Reportes', link: '/reportes' },
            ],
          },
        ],

        outline: { label: 'En esta página' },
        docFooter: { prev: 'Página anterior', next: 'Página siguiente' },
        darkModeSwitchLabel: 'Cambiar tema',
        sidebarMenuLabel: 'Menú',
        returnToTopLabel: 'Volver arriba',
      },
    },

    en: {
      label: 'English',
      lang: 'en',
      title: 'User manual',
      description: 'Application user guide',

      themeConfig: {
        nav: [{ text: 'Home', link: '/en/' }],

        sidebar: [
          {
            text: 'User manual',
            items: [
              { text: 'Authentication and settings', link: '/en/autenticacion-configuracion' },
              { text: 'Home screen', link: '/en/inicio' },
              { text: 'Analysis', link: '/en/analisis' },
              { text: 'Analysis detail', link: '/en/analisis-detalle' },
              { text: 'Plots', link: '/en/graficas' },
              { text: 'Reports', link: '/en/reportes' },
            ],
          },
        ],

        outline: { label: 'On this page' },
        docFooter: { prev: 'Previous page', next: 'Next page' },
        darkModeSwitchLabel: 'Switch theme',
        sidebarMenuLabel: 'Menu',
        returnToTopLabel: 'Back to top',
      },
    },
  },

  themeConfig: {
    search: {
      provider: 'local',
    },
  },
});