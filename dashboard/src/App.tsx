import { type ReactNode } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/hooks/useAuth'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AppShell } from '@/components/layout/AppShell'
import { Login } from '@/pages/Login'
import { AuthCallback } from '@/pages/AuthCallback'
import { Overview } from '@/pages/Overview'
import { Requests } from '@/pages/Requests'
import { RequestDetail } from '@/pages/RequestDetail'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Placeholder for sidebar-linked pages not built in this pass (see the
// implementation plan's "core first" scope decision) - keeps the nav
// structure matching the design brief without 404s.
function ComingSoon({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <h2 className="font-mono-heading text-sm text-ink-secondary mb-1.5">{title}</h2>
      <p className="text-xs text-ink-muted">Not built yet.</p>
    </div>
  )
}

function AuthedShell({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  return <AppShell user={user}>{children}</AppShell>
}

function AuthedRoutes() {
  return (
    <AuthedShell>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/requests" element={<Requests />} />
        <Route path="/requests/:id" element={<RequestDetail />} />
        <Route path="/optimizations/routing" element={<ComingSoon title="ROUTING" />} />
        <Route path="/optimizations/context" element={<ComingSoon title="CONTEXT" />} />
        <Route path="/optimizations/cache" element={<ComingSoon title="CACHE" />} />
        <Route path="/optimizations/batching" element={<ComingSoon title="BATCHING" />} />
        <Route path="/analytics/cost" element={<ComingSoon title="COST" />} />
        <Route path="/analytics/models" element={<ComingSoon title="MODELS" />} />
        <Route path="/analytics/quality" element={<ComingSoon title="QUALITY" />} />
        <Route path="/settings" element={<ComingSoon title="SETTINGS" />} />
      </Routes>
    </AuthedShell>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AuthedRoutes />
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
