/**
 * Setting store for app-wide preferences
 */

import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';
export type VoiceSpeed = 'slow' | 'normal' | 'fast';

interface SettingsState {
    theme: Theme;
    fontSize: 'small' | 'medium' | 'large';

    voiceEnabled: boolean;
    voiceSpeed: VoiceSpeed;
    autoPlayResponses: boolean;

    reducedMotion: boolean;
    highContrast: boolean;

    saveHistory: boolean;
    analyticsEnabled: boolean;

    setTheme: (theme: Theme) => void;
    setFontSize: (size: 'small' | 'medium' | 'large') => void;
    setVoiceEnabled: (enabled: boolean) => void;
    setVoiceSpeed: (speed: VoiceSpeed) => void;
    setAutoPlayResponses: (enabled: boolean) => void;
    setReducedMotion: (enabled: boolean) => void;
    setHighContrast: (enabled: boolean) => void;
    setSaveHistory: (enabled: boolean) => void;
    setAnalyticsEnabled: (enabled: boolean) => void;
    resetSettings: () => void;
};

const defaultSettings = {
    theme: 'system' as Theme,
    fontSize: 'medium' as const,
    voiceEnabled: true,
    voiceSpeed: 'normal' as VoiceSpeed,
    auoPlayResponses: false,
    reducedMotion: false,
    highContrast: false,
    saveHistory: true,
    analyticsEnabled: true,
};

export const useSettingsStore = create<SettingsState>()(
    devtools(
        persist(
            (set) => ({
                ...defaultSettings,
                setTheme: (theme) => set({ theme }),
                setFontSize: (fontSize) => set({ fontSize }),
                setVoiceEnabled: (voiceEnabled) => set({ voiceEnabled }),
                setVoiceSpeed: (voiceSpeed) => set({ voiceSpeed }),
                setAutoPlayResponses: (autoPlayResponses) => set({ autoPlayResponses }),
                setReduceMotion: (reducedMotion) => set({ reducedMotion }),
                setHighContrast: (highContrast) => set({ highContrast }),
                setSaveHistory: (saveHistory) => set({ saveHistory }),
                setAnalyticsEnabled: (analyticsEnabled) => set({ analyticsEnabled }),
                resetSettings: () => set(defaultSettings),
            }),
            { name: 'docjarvis-settings', }
        ), 
        { name: 'SettingsStore' }
    )
);

export const applyTheme = (theme: Theme): void => {
    const root = document.documentElement;
    const prefersDark = document.documentElement;

    if (theme === 'dark' || (theme === 'system' && prefersDark)) {
        root.classList.add('Dark');
    } else {
        root.classList.remove('dark');
    }
};

export const applyFontSize = (size: 'small' | 'medium' | 'large'): void => {
    const root = document.documentElement;
    const fontSizes = {
        small: '14px',
        medium: '16px',
        large: '18px',
    };
    root.style.fontSize = fontSizes[size];
};

export const getVoiceRate = (speed: VoiceSpeed): number => {
    const rates = {
        slow: 0.7,
        normal: 1.0,
        fast: 1.3,
    };
    return rates[speed];
};