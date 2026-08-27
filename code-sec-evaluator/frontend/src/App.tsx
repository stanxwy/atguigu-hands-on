import { useEffect } from 'react';
import {
  Navigate,
  Outlet,
  RouterProvider,
  createBrowserRouter,
  useNavigate,
} from 'react-router-dom';

import { AUTH_UNAUTHORIZED_EVENT } from '@/api/client';
import { AdminRoute } from '@/components/layout/AdminRoute';
import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { Login } from '@/pages/Login';
import { ProjectList } from '@/pages/ProjectList';
import { SystemConfig } from '@/pages/SystemConfig';
import { useAuthStore } from '@/store/authStore';

/** 登录失效监听：Axios 拦截器触发 1002/401 时清理会话并回到登录页。 */
function AuthSessionListener() {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);

  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
      navigate('/login', { replace: true });
    };
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
  }, [logout, navigate]);

  return <Outlet />;
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <AuthSessionListener />,
    children: [
      {
        path: 'login',
        element: <Login />,
      },
      {
        element: (
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        ),
        children: [
          {
            index: true,
            element: <Navigate to="/projects" replace />,
          },
          {
            path: 'projects',
            element: <ProjectList />,
          },
          {
            path: 'system/config',
            element: (
              <AdminRoute>
                <SystemConfig />
              </AdminRoute>
            ),
          },
          {
            path: '*',
            element: <Navigate to="/projects" replace />,
          },
        ],
      },
    ],
  },
]);

/** 应用根组件：初始化认证会话后挂载路由。 */
export function App() {
  const initAuth = useAuthStore((state) => state.init);

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  return <RouterProvider router={router} />;
}
