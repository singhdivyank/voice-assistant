import React from 'react';
import { Volume2, VolumeX, Play, Pause} from 'lucide-react';
import { useSpeechSynthesis } from '@/hooks/';
import { Button } from '../ui/';
import { SpeechControlProps } from '@/utils/';

export const SpeechControls: React.FC<SpeechControlProps> = ({
    text,
    language = 'en-US',
    autoPlay = false,
    onStart,
    onEnd,
}) => {
    const {
        isSupported,
        isSpeaking,
        isPaused,
        speak,
        pause,
        resume,
        cancel
    } = useSpeechSynthesis({
        language,
        onStart,
        onEnd
    });

    React.useEffect(() => {
        if (autoPlay && text && isSupported) {
            speak(text);
        }
    }, [autoPlay, text, isSupported, speak]);

    if (!isSupported) {
        return null;
    }

    const handlePlayPause = () => {
        if (isSpeaking && !isPaused) {
            pause();
        } else if (isPaused) {
            resume();
        } else {
            speak(text);
        }
    };

    const handleStop = () => {
        cancel();
    };

    return (
        <div className="flex items-center gap-2">
            <Button
                onClick={handlePlayPause}
                variant="ghost"
                size="sm"
                disabled={!text}
                aria-label={isSpeaking ? 'Pause' : 'Play'}
            >
                {isSpeaking && !isPaused ? (
                <Pause className="w-4 h-4" />
                ) : (
                <Play className="w-4 h-4" />
                )}
            </Button>

            {isSpeaking && (
                <Button
                onClick={handleStop}
                variant="ghost"
                size="sm"
                aria-label="Stop"
                >
                <VolumeX className="w-4 h-4" />
                </Button>
            )}

            {!isSpeaking && (
                <Volume2 className="w-4 h-4 text-gray-400" />
            )}
        </div>
    );
};