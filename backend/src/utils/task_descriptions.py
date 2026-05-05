"""Hardcode task description strings"""

STT_TASK_DESCRIPTION = """
Transcribe audio file to extract patient's initial symptom:
Audio file path: {audio_file_path}
Patient language: {patient_language}
                    
Use speech_to_text tool to accurately transcribe the audio content.
Focus on medical terminology and ensure clarity
"""

TRANSLATION_TASK_DESCRIPTION = """
Translate patient's complaint to English for medical analysis:
Source language: {source_langauage}
Patient complaint: {initial_complaint}
                    
Use translate_text tool to convert to English while preserving medical context.
Maintain accuracy of symptoms and medical terms.
"""

QUESTION_TASK_DESCRIPTION = """
Generate exactly 3 focused diagnostic questions:
Patient age: {patient_age} year old
Patient gender: {patient_gender}
Initial complaint: {initial_complaint}
                
Use generate_medical_questions tool to create questions that will:
1. Help narrow differential diagnosis
2. Be appropriate for patient age and gender
3. Follow evidence-based medical interview protocols
                
Return exactly 3 questions in JSON format
"""

TRANSLATION_DESCRIPTION = """
Translate text accurately:
Source language: {source_lang}
Target language: {target_lang}
Text to translate: {text}
Use translate_text tool to provide accurate translation while maintaining medical context.
"""

DIAGNOSIS_TASK_DESCRIPTION = """
Perform comprehensive medical diagnosis analysis:
Patient Information:
- Age: {age}
- Gender: {gender}
- Initial complaint: {initial_complaint}

Q&A Summary:
{qa_summary}

Use medical_diagnosis tool to provide:
1. Detailed symptom analysis
2. Differential diagnosis with rationale
3. Most likely primary diagnosis

Consider patient demographics and follow evidence-based guidelines.
"""

MEDICATION_TASK_DESCRIPTION = """
Generate evidence-based medication recommendations:
Patient Information:
- Age: {age}
- Gender: {gender}
                
Based on the diagnosis from the previous task, use medication_recommendation tool to provide:
1. Primary medication recommendations with specific dosages
2. Alternative treatment options if applicable
3. Important safety instructions and contraindications
4. When to seek emergency medical care
5. Follow-up recommendations and monitoring requirements
                
Ensure age-appropriate dosing and consider gender-specific factors.
"""

RECOMMENDATIONS_TASK_DESCRIPTION = """
Convert medication recommendations to clear audio:
Target language: {lang}
Recommendations text: {recommendations}
                
Use text_to_speech tool to generate patient-friendly audio with:
1. Clear pronunciation of medical terms
2. Appropriate pace for patient understanding
3. Professional but reassuring tone

Return audio in base64 format for immediate playback.
"""

PROCESS_RESPONSE_TASK_DESCRIPTION = """
Process doctor's Gmail MCP response:
Review ID: {review_id}
Email Content: {email_content}
                
Use gmail_mcp_read tool to parse the doctor's response and:
1. Identify the action (APPROVE/MODIFY/REJECT)
2. Extract any modifications or rejection reasons
3. Take appropriate follow-up action
4. Update prescription status accordingly

Return structured response indicating next steps.
"""
