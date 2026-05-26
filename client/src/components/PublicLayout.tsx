import type { ReactNode } from 'react';
import AppFooter from './AppFooter';
import PublicNavbar from './PublicNavbar';

type PublicLayoutProps = {
  children: ReactNode;
};

export default function PublicLayout({ children }: PublicLayoutProps) {
  return (
    <div className="app-layout-root theme-transition">
      <PublicNavbar />
      <div className="app-layout-content">{children}</div>
      <AppFooter />
    </div>
  );
}
