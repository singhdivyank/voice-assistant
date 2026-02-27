interface ImportMeta {
  readonly env: Record<string, string | undefined>;
}

declare module 'react-mic-recorder' {
  import { Component } from 'react';
  interface ReactMicProps {
    record: boolean;
    className?: string;
    onStop?: (blob: { blobURL: string }) => void;
    onData?: (blob: Blob) => void;
    strokeColor?: string;
    backgroundColor?: string;
  }
  export class ReactMic extends Component<ReactMicProps> {}
}
