import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutGrid,
  Zap,
  Route as RouteIcon,
  ScrollText,
  Layers,
  Boxes,
  ListChecks,
  PieChart,
  DollarSign,
  Cpu,
  Star,
  Settings as SettingsIcon,
  ChevronDown,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/cn'

interface NavItem {
  label: string
  to: string
  icon: LucideIcon
}

interface NavGroup {
  label: string
  icon: LucideIcon
  children: NavItem[]
}

const optimizationsGroup: NavGroup = {
  label: 'OPTIMIZATIONS',
  icon: Zap,
  children: [
    { label: 'ROUTING', to: '/optimizations/routing', icon: RouteIcon },
    { label: 'CONTEXT', to: '/optimizations/context', icon: ScrollText },
    { label: 'CACHE', to: '/optimizations/cache', icon: Layers },
    { label: 'BATCHING', to: '/optimizations/batching', icon: Boxes },
  ],
}

const analyticsGroup: NavGroup = {
  label: 'ANALYTICS',
  icon: PieChart,
  children: [
    { label: 'COST', to: '/analytics/cost', icon: DollarSign },
    { label: 'MODELS', to: '/analytics/models', icon: Cpu },
    { label: 'QUALITY', to: '/analytics/quality', icon: Star },
  ],
}

function NavLinkItem({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2.5 rounded px-3 py-2 text-xs font-mono transition-colors',
          isActive
            ? 'bg-accent-blue/10 text-accent-blue border-l-2 border-accent-blue -ml-px'
            : 'text-ink-secondary hover:text-ink-primary hover:bg-surface-2 border-l-2 border-transparent',
        )
      }
    >
      <Icon size={14} />
      {item.label}
    </NavLink>
  )
}

function NavGroupItem({ group }: { group: NavGroup }) {
  const location = useLocation()
  const hasActiveChild = group.children.some((c) => location.pathname.startsWith(c.to))
  const [expanded, setExpanded] = useState(hasActiveChild)
  const Icon = group.icon

  return (
    <div>
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center justify-between rounded px-3 py-2 text-xs font-mono text-ink-secondary hover:text-ink-primary hover:bg-surface-2 transition-colors"
      >
        <span className="flex items-center gap-2.5">
          <Icon size={14} />
          {group.label}
        </span>
        <ChevronDown
          size={12}
          className={cn('transition-transform', expanded ? 'rotate-0' : '-rotate-90')}
        />
      </button>
      {expanded && (
        <div className="ml-[18px] mt-0.5 border-l border-line pl-2.5 flex flex-col gap-0.5">
          {group.children.map((child) => (
            <NavLinkItem key={child.to} item={child} />
          ))}
        </div>
      )}
    </div>
  )
}

interface SidebarProps {
  user?: { name: string; email: string } | null
}

export function Sidebar({ user }: SidebarProps) {
  return (
    <aside className="w-[220px] shrink-0 h-screen sticky top-0 flex flex-col border-r border-line bg-surface">
      <div className="px-5 py-5 border-b border-line">
        <h1 className="font-mono-heading text-lg text-ink-primary tracking-widest">MERIDIAN</h1>
        <p className="text-[10px] text-ink-muted mt-1 font-mono">LLM COST OPTIMIZATION ENGINE</p>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 flex flex-col gap-0.5">
        <NavLinkItem item={{ label: 'OVERVIEW', to: '/', icon: LayoutGrid }} />
        <NavGroupItem group={optimizationsGroup} />
        <NavLinkItem item={{ label: 'REQUESTS', to: '/requests', icon: ListChecks }} />
        <NavGroupItem group={analyticsGroup} />
        <NavLinkItem item={{ label: 'SETTINGS', to: '/settings', icon: SettingsIcon }} />
      </nav>

      {user && (
        <div className="px-4 py-4 border-t border-line flex items-center gap-2.5">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-2 border border-line text-xs font-mono text-ink-secondary">
            {user.name.slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-xs text-ink-primary truncate">{user.name}</p>
            <p className="text-[10px] text-ink-muted truncate">{user.email}</p>
          </div>
        </div>
      )}
    </aside>
  )
}
