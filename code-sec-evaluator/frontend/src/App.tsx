import { Suspense, lazy, useEffect } from 'react';
import {
  Navigate,
  Outlet,
  RouterProvider,
  createBrowserRouter,
  useNavigate,
} from 'react-router-dom';

import { AUTH_UNAUTHORIZED_EVENT } from '@/api/client';
import { LoadingState } from '@/components/common/LoadingState';
import { AdminRoute } from '@/components/layout/AdminRoute';
import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { useAuthStore } from '@/store/authStore';

/** 页面按路由懒加载，配合 manualChunks 拆分依赖，降低首屏体积。 */
const Login = lazy(() => import('@/pages/Login').then((module) => ({ default: module.Login })));
const ProjectList = lazy(() =>
  import('@/pages/ProjectList').then((module) => ({ default: module.ProjectList })),
);
const ProjectCreate = lazy(() =>
  import('@/pages/ProjectCreate').then((module) => ({ default: module.ProjectCreate })),
);
const ProjectDetail = lazy(() =>
  import('@/pages/ProjectDetail').then((module) => ({ default: module.ProjectDetail })),
);
const ProjectOverview = lazy(() =>
  import('@/pages/ProjectDetail').then((module) => ({ default: module.ProjectOverview })),
);
const Monitor = lazy(() =>
  import('@/pages/Monitor').then((module) => ({ default: module.Monitor })),
);
const VulnerabilityList = lazy(() =>
  import('@/pages/VulnerabilityList').then((module) => ({ default: module.VulnerabilityList })),
);
const VulnerabilityDetail = lazy(() =>
  import('@/pages/VulnerabilityDetail').then((module) => ({
    default: module.VulnerabilityDetail,
  })),
);
const AttackPathList = lazy(() =>
  import('@/pages/AttackPathList').then((module) => ({ default: module.AttackPathList })),
);
const AttackPathDetail = lazy(() =>
  import('@/pages/AttackPathDetail').then((module) => ({ default: module.AttackPathDetail })),
);
const Report = lazy(() => import('@/pages/Report').then((module) => ({ default: module.Report })));
const SystemConfig = lazy(() =>
  import('@/pages/SystemConfig').then((module) => ({ default: module.SystemConfig })),
);

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

/** 路由根布局：懒加载页面统一挂载 Suspense 兜底。 */
function RootLayout() {
  return (
    <Suspense fallback={<LoadingState label="页面加载中..." />}>
      <AuthSessionListener />
    </Suspense>
  );
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
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
            children: [
              {
                index: true,
                element: <ProjectList />,
              },
              {
                path: 'new',
                element: <ProjectCreate />,
              },
              {
                path: ':projectId',
                element: <ProjectDetail />,
                children: [
                  {
                    index: true,
                    element: <ProjectOverview />,
                  },
                  {
                    path: 'monitor',
                    element: <Monitor />,
                  },
                  {
                    path: 'vulnerabilities',
                    element: <VulnerabilityList />,
                  },
                  {
                    path: 'vulnerabilities/:vulnId',
                    element: <VulnerabilityDetail />,
                  },
                  {
                    path: 'attack-paths',
                    element: <AttackPathList />,
                  },
                  {
                    path: 'attack-paths/:pathId',
                    element: <AttackPathDetail />,
                  },
                  {
                    path: 'report',
                    element: <Report />,
                  },
                ],
              },
            ],
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
