import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';

import { useAuthStore } from '@/store/authStore';

interface AdminRouteProps {
  children: ReactNode;
}

/** 管理员守卫：非 admin 用户访问管理页面时重定向到项目列表。 */
export function AdminRoute({ children }: AdminRouteProps) {
  const user = useAuthStore((state) => state.user);

  if (user?.role !== 'admin') {
    return <Navigate to="/projects" replace />;
  }
  return <>{children}</>;
}
