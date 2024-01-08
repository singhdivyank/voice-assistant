import os

import google.generativeai as genai

from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ChatMessageHistory
from langchain.prompts import ChatPromptTemplate

from consts import (
    LLM_MODEL, 
    LLM_NAME,
    DIAGNOSIS_TEMPLATE, 
    MEDICATION_TEMPLATE
)

genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))


class DocJarvis:
    def __init__(self, age: int, gender: str):
        self.age = age
        self.gender = gender
        self.history = ChatMessageHistory()
        self.llm = ChatGoogleGenerativeAI(
            name=LLM_NAME, 
            temperature=0,
            model=LLM_MODEL,
            convert_system_message_to_human=True
        )
        self.medication_prompt = ChatPromptTemplate.from_messages(
            messages=[
                ("human", MEDICATION_TEMPLATE)
            ]
        )
        self.diagnosis_prompt = ChatPromptTemplate.from_messages(
            messages=[
                ("system", DIAGNOSIS_TEMPLATE),
                ("human", "{input}")
            ]
        )

    def call_doc(self, conversation: list) -> str:
        """
        function to prescribe medication using Gemini-Pro

        Params:
            conversation (list): initial diagnosis results
        
        Returns:
            response (str): generated medication
        """

        for _, conv in enumerate(conversation):
            self.history.add_ai_message(conv[0])
            self.history.add_user_message(conv[1])

        chain = self.medication_prompt | self.llm
        response = chain.invoke(
            input={
                "age": self.age, 
                "gender": self.gender, 
                "conversation": conversation
            }
        ).content
        print(response)
        return response

    def perform_diagnosis(self, usr_msg: str) -> List[str]:
        """
        using Gemini-Pro ask further questions to the patient

        Params:
            usr_msg (str): patient's input
        
        Returns:
            diag_ques (List): further questions generated from LLM
        """

        chain = self.diagnosis_prompt | self.llm
        response = chain.invoke(input={"input": usr_msg}).content
        diag_ques = response.split("\n")
        print("diagnosis results:: ", diag_ques)
        return diag_ques
