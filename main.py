import os

import gradio as gr

from dotenv import (
    load_dotenv, 
    find_dotenv
)
from typing import List

from consts import LANGUAGES
from create_prescription import Prescription
from speechOps import (
    Transcribe, 
    ToAudio
)
from perform_translation import Translate
from diagnosis import DocJarvis

load_dotenv(dotenv_path=find_dotenv())

def main(language: str, gender: List, age: str) -> str:
    """
    user profile/dashboard
    """

    symptoms = []
    translated_symptoms = []
    translated_diag_res = []
    
    print("chosen language:: ", language)
    # get language code
    lan_code = LANGUAGES.get(language, 'en')

    # create class objects
    translate_ob = Translate(lan_code=lan_code)
    audio_ob = ToAudio(language=lan_code)
    prescription_ob = Prescription(
        age=age,
        gender=gender[0] if gender[0] in ["Male", "Female"] else "Others"
    )
    transcribe_ob = Transcribe(language=lan_code)
    doc_ob = DocJarvis(
        age=age, 
        gender=gender
    )
    
    # get all static messages
    all_msgs = translate_ob.get_msgs()

    # send introduction message to user
    audio_ob.text_to_speech(txt_msg=all_msgs[0])
    # send instruction message to user
    audio_ob.text_to_speech(txt_msg=all_msgs[1])

    # get user message
    user_text = transcribe_ob.get_text()
    if user_text == "NO INTERNET CONNECTION":
        return "please connect to the internet"
    # translate to English for LLM model
    for_doc = translate_ob.translation(
        for_usr=user_text, 
        llm_flag=True
    ) if not lan_code == 'en' else user_text
    print("initial words::", for_doc)
    # call LLM and find medication
    diagnosis_res = doc_ob.perform_diagnosis(usr_msg=for_doc)

    # perform conversation
    for _, diag_ques in enumerate(diagnosis_res):

        if not diag_ques:
            continue

        # translate results to user language
        doc_notes = translate_ob.translation(
            for_usr=diag_ques, 
            llm_flag=False
        ) if not lan_code == 'en' else diag_ques
        translated_diag_res.append(doc_notes)
        # generate audio message
        audio_ob.text_to_speech(txt_msg=doc_notes)
        
        # receive input from user
        symptom = transcribe_ob.get_text()
        if not symptom == "NO INTERNET CONNECTION":
            translated_symptoms.append(symptom)
            # translate to English for LLM
            symptom = translate_ob.translation(
                for_usr=symptom,
                llm_flag=True
            ) if not lan_code == 'en' else symptom
            print(symptom)
            symptoms.append(symptom)
    conversation = list(zip(diagnosis_res, symptoms))
    translated_conversation = list(zip(translated_diag_res, translated_symptoms))
    
    # get medication using LLM
    medication = doc_ob.call_doc(conversation=conversation)
    medication = translate_ob.translation(
        for_usr=medication,
        llm_flag=False
    ) if not lan_code == 'en' else medication
    
    # create prescription
    prescription_ob.create_prescription(
        inital_msg = user_text,
        conversation = translated_conversation,
        medication = medication
    )
    # generate audio
    audio_ob.text_to_speech(txt_msg=medication)
    
    return prescription_ob.prescription_file


if __name__ == '__main__':
    # create UI
    ui=gr.Interface(
        fn=main,
        inputs=[
            gr.Dropdown(
                choices=list(LANGUAGES.keys()),
                multiselect=False,
                label="language selection",
                show_label=True,
                interactive=True
            ),
            gr.CheckboxGroup(
                choices=["Male", "Female", "Prefer not to disclose"],
                label="gender selection",
                show_label=True,
                interactive=True,
            ),
            gr.Slider(
                minimum=10,
                maximum=50,
                step=2,
                label="age selection",
                show_label=True,
                interactive=True
            )
        ],
        outputs=["text"]
    )
    # launch the UI
    ui.launch(
        server_name=os.getenv(key='GRADIO_SERVER_NAME'), 
        server_port=int(os.getenv(key='GRADIO_SERVER_PORT')), 
        share=False
    )
