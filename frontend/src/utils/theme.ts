export type ThemeId = 'blaze' | 'race-red' | 'volt' | 'ice'

export interface ThemeDefinition {
  id: ThemeId
  name: string
  label: string
  color: string
  gradient: string
}

export const AVAILABLE_THEMES: ThemeDefinition[] = [
  { id: 'blaze', name: 'Blaze', label: 'Blaze Orange', color: '#ff5a1f', gradient: '#ff5a1f' },
  { id: 'race-red', name: 'Race Red', label: 'Race Red', color: '#e8112d', gradient: '#e8112d' },
  { id: 'volt', name: 'Volt', label: 'Volt Green', color: '#c6f432', gradient: '#c6f432' },
  { id: 'ice', name: 'Ice', label: 'Ice Blue', color: '#4cc3ff', gradient: '#4cc3ff' },
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
  return 'blaze'
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
