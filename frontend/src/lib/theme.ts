// src/lib/theme.ts
// Theme management for dark/light/system mode

export type ThemeMode = 'light' | 'dark' | 'system';

function applyTheme(mode: ThemeMode) {
    if (typeof window === 'undefined') return;

    const root = document.documentElement;
    
    let actualTheme: 'light' | 'dark';
    
    if (mode === 'system') {
        actualTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    } else {
        actualTheme = mode;
    }
    
    // Set data attribute for CSS to target
    root.setAttribute('data-theme', actualTheme);
    
    // Also set a class for compatibility
    root.classList.remove('light', 'dark');
    root.classList.add(actualTheme);
}

export function getTheme(): ThemeMode {
    if (typeof window === 'undefined') {
        return 'system';
    }
    
    const stored = localStorage.getItem('theme');
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
        return stored;
    }
    return 'system';
}

export function setTheme(mode: ThemeMode): void {
    if (typeof window === 'undefined') {
        return;
    }
    
    localStorage.setItem('theme', mode);
    applyTheme(mode);
}

export function initTheme(): void {
    if (typeof window === 'undefined') return;
    
    const mode = getTheme();
    applyTheme(mode);
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (getTheme() === 'system') {
            applyTheme('system');
        }
    });
}
