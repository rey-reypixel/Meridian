import { type ReactNode } from 'react'
import { Sidebar } from './Sidebar'

interface AppShellProps {
  children: ReactNode
  user?: { name: string; email: string } | null
}

export function AppShell({ children, user }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-app">
      <Sidebar user={user} />
      <main className="flex-1 min-w-0 p-6">{children}</main>
    </div>
  )
}
