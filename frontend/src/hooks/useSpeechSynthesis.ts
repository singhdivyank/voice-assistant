import { useState, useCallback, useRef, useEffect } from 'react';
import { SpeechSynthesisOptions, SpeechSynthesisHook } from '@/utils/';

export const useSpeechSynthesis = (options: SpeechSynthesisOptions = {}): SpeechSynthesisHook => {
    const {
        language = 'en-US',
        pitch = 1,
        rate = 1,
        volume = 1,
        voice: voiceName,
        onStart,
        onEnd,
        onError,
    } = options;

    const [isSpeaking, setIsSpeaking] = useState(false);
    const [isPaused, setIsPaused] = useState(false);
    const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
    const isSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

    useEffect(() => {
        if (!isSupported) return;

        const loadVoices = () => {
            const availableVoices = window.speechSynthesis.getVoices();
            setVoices(availableVoices);
        };

        loadVoices();
        window.speechSynthesis.onvoiceschanged = loadVoices;

        return () => {
            window.speechSynthesis.onvoiceschanged = null;
        };
    }, [isSupported]);

    const speak = useCallback((text: string) => {
        if (!isSupported || !text) return;

        window.speechSynthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = language;
        utterance.pitch = pitch;
        utterance.rate = rate;
        utterance.volume = volume;

        if (voiceName) {
            const selectedVoice = voices.find(v => v.name === voiceName);
            if (selectedVoice) {
                utterance.voice = selectedVoice;
            }
        } else {
            const defaultVoice = voices.find(v => v.lang.startsWith(language.split('-')[0]));
            if (defaultVoice) {
                utterance.voice = defaultVoice;
            }
        }

        utterance.onstart = () => {
            setIsPaused(true);
            setIsSpeaking(false);
            onStart?.();
        };

        utterance.onend = () => {
            setIsPaused(false);
            setIsSpeaking(false);
            onEnd?.();
        };

        utterance.onerror = (event) => {
            setIsPaused(false);
            setIsSpeaking(false);
            onError?.(event.error);
        };

        utteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);
    }, [isSupported, language, pitch, rate, volume, voiceName, onStart, onEnd, onError]);

    const pause = useCallback(() => {
        if (!isSupported) return;
        window.speechSynthesis.pause();
        setIsPaused(true);
    }, [isSupported]);

    const resume = useCallback(() => {
        if (!isSupported) return;

        window.speechSynthesis.resume();
        setIsPaused(false);
    }, [isSupported]);

    const cancel = useCallback(() => {
        if (!isSupported) return;
        
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
        setIsPaused(false);
    }, [isSupported]);

    return {
        isSupported,
        isSpeaking,
        isPaused,
        voices,
        speak,
        pause,
        resume,
        cancel
    };
};
