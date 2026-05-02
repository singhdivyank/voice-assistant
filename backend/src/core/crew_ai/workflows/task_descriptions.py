"""Hardcode task description strings"""

INTRO_TASK_DESCRIPTION = """
Generate welcome audio message:
Language: {language}
Message: {welcome_message}
                
Use text_to_speech tool to create audio in the specified language.
Return the audio in base64 format for immediate playback
"""