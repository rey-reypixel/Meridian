import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'

export function Login() {
  const { login, isAuthenticated } = useAuth()
  const [isRedirecting, setIsRedirecting] = useState(false)

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const handleLogin = async () => {
    setIsRedirecting(true)
    try {
      await login()
    } catch {
      setIsRedirecting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      <Card className="w-full max-w-sm p-8 text-center">
        <h1 className="font-mono-heading text-xl text-ink-primary tracking-widest">MERIDIAN</h1>
        <p className="text-xs text-ink-muted mt-1.5 font-mono">LLM COST OPTIMIZATION ENGINE</p>
        <Button
          variant="primary"
          size="md"
          onClick={handleLogin}
          disabled={isRedirecting}
          className="w-full mt-8"
        >
          {isRedirecting ? 'Redirecting…' : 'Sign in with Google'}
        </Button>
      </Card>
    </div>
  )
}
