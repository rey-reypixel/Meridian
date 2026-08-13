import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { setToken } from '@/api/client'

// Backend's /auth/callback redirects here with ?token=<jwt> once Google
// auth completes - this page just stores it and hands off to the app.
export function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  useEffect(() => {
    const token = searchParams.get('token')
    if (token) {
      setToken(token)
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
      navigate('/', { replace: true })
    } else {
      navigate('/login', { replace: true })
    }
  }, [searchParams, navigate, queryClient])

  return (
    <div className="flex min-h-screen items-center justify-center bg-app">
      <span className="font-mono text-xs text-ink-muted">SIGNING IN...</span>
    </div>
  )
}
