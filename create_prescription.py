import os

from consts import PRESCRIPTION_NAME


class Prescription:
    def __init__(self, age: int, gender: str):
        self.age = age,
        self.gender = gender
        self.delete_file()
    
    def delete_file(self) -> None:
        """
        delete txt file
        """
        
        if os.path.exists(path=PRESCRIPTION_NAME):
            os.remove(path=PRESCRIPTION_NAME)
    
    def create_prescription(self, inital_msg: str, conversation: list, medication: str) -> None:
        """
        create a txt file summarizing patient's visit

        Params:
            initial_msg (str): message given by user at the start
            conversation (list): conversation between patient and doctor
            medication (str): medication prescribed by doctor
        """
        
        # create the conversation
        dialog = f"YOU: {inital_msg}\n"
        for _, conv in enumerate(conversation):
            dialog += f"JARVIS: {conv[0]}\nYOU: {conv[1]}\n"
        dialog += f"JARVIS: {medication}"

        # write to txt file
        if not os.path.exists(PRESCRIPTION_NAME):
            content = f"AGE: {self.age}\nGENDER: {self.gender}\n\n{dialog}"
            with open(file=PRESCRIPTION_NAME, mode='w', encoding='utf8') as f:
                f.write(content)
                f.close()
        
        print("created prescription...")
    