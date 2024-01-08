import os

import playsound
import speech_recognition as sr

from gtts import gTTS

from consts import AUDIO_FILE


class Transcribe:
    def __init__(self, language: str):
        self.language=language
        # initialise recogniser
        self.recognizer = sr.Recognizer()
        # initialise microphone
        self.mic = sr.Microphone()
    
    def get_text(self) -> None:
        """
        convert audio from microphone to text 
        """

        with self.mic as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source=source)
                audio = self.recognizer.listen(source=source)
                transcribed_txt = self.recognizer.recognize_google(
                    audio_data=audio, 
                    language=self.language
                )
                print("received audio")
                return transcribed_txt
            except sr.RequestError:
                return "NO INTERNET CONNECTION"


class ToAudio:
    def __init__(self, language: str):
        self.language = language
        self.delete_file()
    
    def delete_file(self) -> None:
        """
        delete audio file
        """

        if os.path.exists(path=AUDIO_FILE):
            with open(file=AUDIO_FILE, mode='rb') as f:
                f.close()
            os.remove(path=AUDIO_FILE)
    
    def text_to_speech(self, txt_msg: str) -> None:
        """
        using Google Text to Speech module, 
        recite a text in a given language

        Params:
            txt_msg (str): text message
        """
        
        audio = gTTS(text=txt_msg, lang=self.language)
        audio.save(savefile=AUDIO_FILE)
        audio.timeout = 5
        audio.speed = 'medium'
        playsound.playsound(sound=AUDIO_FILE)
        self.delete_file()   
