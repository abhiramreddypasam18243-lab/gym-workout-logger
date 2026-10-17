export type ThemeId = 'cyber-cyan' | 'hyper-violet' | 'volt-lime' | 'solar-amber'

export interface ThemeDefinition {
  id: ThemeId
  name: string
  label: string
  color: string
  gradient: string
}

export const AVAILABLE_THEMES: ThemeDefinition[] = [
  {
    id: 'cyber-cyan',
    name: 'Cyber Cyan',
    label: 'Laser Cyan',
    color: '#38bdf8',
    gradient: 'linear-gradient(135deg, #38bdf8, #0284c7)',
  },
  {
    id: 'hyper-violet',
    name: 'Hyper Violet',
    label: 'Electric Violet',
    color: '#a855f7',
    gradient: 'linear-gradient(135deg, #c084fc, #ec4899)',
  },
  {
    id: 'volt-lime',
    name: 'Volt Lime',
    label: 'High-Voltage Green',
    color: '#10b981',
    gradient: 'linear-gradient(135deg, #34d399, #059669)',
  },
  {
    id: 'solar-amber',
    name: 'Solar Amber',
    label: 'Olympic Gold',
    color: '#f59e0b',
    gradient: 'linear-gradient(135deg, #fbbf24, #ea580c)',
  },
]

const STORAGE_KEY = 'titan_theme_id'

export function getStoredTheme(): ThemeId {
  try {
    const val = localStorage.getItem(STORAGE_KEY)
    if (val && AVAILABLE_THEMES.some((t) => t.id === val)) {
      return val as ThemeId
    }
  } catch (e) {
    console.warn('Could not read theme from storage', e)
  }
  return 'cyber-cyan'
}

export function applyTheme(themeId: ThemeId): void {
  try {
    localStorage.setItem(STORAGE_KEY, themeId)
  } catch (e) {
    console.warn('Could not save theme to storage', e)
  }

  // Apply to document element
  document.documentElement.setAttribute('data-theme', themeId)
}

export function initTheme(): ThemeId {
  const current = getStoredTheme()
  applyTheme(current)
  return current
}
