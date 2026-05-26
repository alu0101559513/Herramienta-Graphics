import type { ReactNode } from 'react';
import AppFooter from './AppFooter';
import PrivateNavbar from './PrivateNavbar';

type PrivateLayoutProps = {
  children: ReactNode;
};

export default function PrivateLayout({ children }: PrivateLayoutProps) {
  return (
    <div className="app-layout-root theme-transition">
      <PrivateNavbar />
      <div className="app-layout-content">{children}</div>
      <AppFooter />
    </div>
  );
}
