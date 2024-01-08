from googletrans import Translator

from typing import List


class Translate:
    def __init__(self, lan_code: str):
        self.lan_code = lan_code
        self.translator = Translator()
        self.msgs = self.get_msgs()
    
    def translation(self, for_usr: str, llm_flag: bool) -> str:
        """
        translate from one language to another using Google Translate
        
        Params:
            for_usr (str): input text
            llm_flag (bool): if message is intended for LLM model
        
        Returns:
            translation (str): translated text
        """
        
        translated_txt = self.translator.translate(
            text=for_usr, 
            dest=self.lan_code if not llm_flag else 'en'
        )
        return translated_txt.text
    
    def get_msgs(self) -> List[str]:
        """
        obtain translated messages for the user
        
        Returns:
            List: all messages
        """
        
        # introduction message
        MAIN_MSG = "send message from microphone. To stop, say 'thanks'"
        # instruction message
        INSTR_MSG = "please begin"
        # diagnosis message
        DIAG_MSG = "performing diagnosis"

        # perform message translation
        main_message = self.translation(for_usr=MAIN_MSG, llm_flag=False) if not self.lan_code == 'en' else MAIN_MSG
        instr_message = self.translation(for_usr=INSTR_MSG, llm_flag=False) if not self.lan_code == 'en' else INSTR_MSG
        diag_message = self.translation(for_usr=DIAG_MSG, llm_flag=False) if not self.lan_code == 'en' else DIAG_MSG
        return [main_message, instr_message, diag_message]
