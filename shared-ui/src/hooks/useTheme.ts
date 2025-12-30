import { useState, useEffect, useCallback } from 'react';

// Legacy type for compatibility during refactor
export type ThemeName = 'oatmeal';

export const THEMES: { name: ThemeName; label: string }[] = [
  { name: 'oatmeal', label: 'Default' },
];

const DARK_MODE_COOKIE = 'lmsilo-theme';
const COOKIE_MAX_AGE = 31536000; // 1 year

function getCookie(name: string): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift();
  return undefined;
}

function setCookie(name: string, value: string): void {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=${value}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`;
}

/**
 * Shared theme hook for LMSilo services.
 * Simplified to only handle Dark Mode.
 */
export function useTheme() {
  const [isDark, setIsDark] = useState<boolean>(false);

  // Initialize from cookie or system preference
  useEffect(() => {
    const darkModeCookie = getCookie(DARK_MODE_COOKIE);
    
    if (darkModeCookie) {
      setIsDark(darkModeCookie === 'dark');
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setIsDark(true);
    }
  }, []);

  // Update DOM and Cookie when isDark changes
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
      setCookie(DARK_MODE_COOKIE, 'dark');
    } else {
      root.classList.remove('dark');
      setCookie(DARK_MODE_COOKIE, 'light');
    }
    
    // Clean up any lingering theme classes
    const classes = Array.from(root.classList);
    classes.forEach(c => {
      if (c.startsWith('theme-')) root.classList.remove(c);
    });
  }, [isDark]);

  const toggle = useCallback(() => {
    setIsDark(prev => !prev);
  }, []);

  return {
    theme: 'oatmeal' as ThemeName,
    setTheme: () => {}, // No-op
    themes: THEMES,
    isDark,
    toggle
  };
}
