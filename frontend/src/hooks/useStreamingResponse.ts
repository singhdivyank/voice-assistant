import { useState, useCallback, useRef } from 'react';

interface StreamingOptions {
    onChunk?: (chunk: string) => void;
    onComplete?: (fullResponse: string) => void;
    onError?: (error: Error) => void;
}

interface StreamingHook {
    isStreaming: boolean;
    response: string;
    startStream: (url: string, options?: RequestInit) => Promise<void>;
    stopStream: () => void;
    reset: () => void;
}

export const useStreamingResponse = (options: StreamingOptions = {}) : StreamingHook => {
    const { onChunk, onComplete, onError } = options;
    const [ isStreaming, setIsStreaming ] = useState(false);
    const [ response, setResponse ] = useState('');
    const abortControllerRef = useRef<AbortController | null>(null);

    const startStream = useCallback(async (url: string, fetchOptions: RequestInit = {}) => {
        abortControllerRef.current?.abort();
        abortControllerRef.current = new AbortController();
        setIsStreaming(true);
        setResponse('');

        try {
            const result = await fetch(url, {
                ...fetchOptions,
                signal: abortControllerRef.current.signal,
            });

            if (!result.ok) {
                throw new Error(`HTTP error! status: ${result.status}`);
            }

            const reader = result.body?.getReader();
            if (!reader) {
                throw new Error('No response body');
            }

            const decoder = new TextDecoder();
            let fullResponse = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value);
                const lines = text.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);

                        if (data === '[DONE]') {
                            setIsStreaming(false);
                            onComplete?.(fullResponse);
                            return;
                        }

                        fullResponse = fullResponse + data;
                        setResponse(fullResponse);
                        onChunk?.(data);
                    }
                }
            }

            setIsStreaming(false);
            onComplete?.(fullResponse);
        } catch (error) {
            if ((error as Error).name == 'AbortError') {
                return;
            }

            setIsStreaming(false);
            onError?.(error as Error);
        }
    }, [onChunk, onComplete, onError]);

    const stopStream = useCallback(() => {
        abortControllerRef.current?.abort();
        setIsStreaming(false);
    }, []);

    const reset = useCallback(() => {
        stopStream();
        setResponse('');
    }, [stopStream]);

    return {
        isStreaming,
        response,
        startStream,
        stopStream,
        reset
    };
};