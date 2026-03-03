# DocJarvis- AI Medical Assistant

An AI-powered multilingual medical consultation assistant that conducts preliminary diagnosis and medication recommendations based on patient symptoms.

> **Disclaimer:** This is an AI-assisted tool for **educational (informational) purposes only**. Always consult qualified healthcare professionals for medical advice.

## Project Structure

```
docjarvis/
├── backend/                      # Python FastAPI backend
│   ├── src/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py          # FastAPI app (artifact above)
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── diagnosis.py
│   │   │   │   ├── sessions.py
│   │   │   │   ├── prescription.py
│   │   │   ├── schemas/         # Pydantic models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── diagnosis.py
│   │   │   │   ├── patient.py
│   │   │   │   ├── session.py
│   │   │   └── middleware/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── error_handler.py
│   │   │   │   └── logging.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── monitoring.py
│   │   │   ├── settings.py
│   │   ├── core/                
│   │   │   ├── __init__.py
│   │   │   ├── diagnosis.py
│   │   │   ├── prescription.py
│   │   │   ├── multi_agent/
│   │   │   │   ├── agents/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base_agent.py
│   │   │   │   │   ├── diagnosis_agent.py
│   │   │   │   │   ├── medication_agent.py
│   │   │   │   │   ├── prescription_agent.py
│   │   │   │   │   ├── qa_agent.py
│   │   │   │   │   ├── stt_agent.py
│   │   │   │   │   ├── translation_agent.py
│   │   │   │   │   ├── tts_agent.py
│   │   │   │   ├── workflow/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── graph_builder.py
│   │   │   │   │   └── state_manager.py
│   │   │   │   ├── __init__.py
│   │   │   │   └── llm_manager.py
│   │   ├── monitoring/
│   │   │   ├── __init__.py
│   │   │   ├── cache_manager.py
│   │   │   ├── dashboard.py
│   │   │   ├── load_balancer.py
│   │   │   ├── performance_monitor.py
│   │   ├── services/      
│   │   │   ├── __init__.py
│   │   │   ├── session_store.py      
│   │   │   ├── speech.py
│   │   │   ├── translation.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── consts.py
│   │   │   ├── exceptions.py
│   │   │   └── file_handler.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_diagnosis.py
│   │   │   └── test_translation.py
│   │   ├── integration/
│   │   │   └── test_api.py
│   │   └── e2e/
│   │       └── test_consultation_flow.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     # React TypeScript frontend
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts        # API client
│   │   ├── components/
│   │   │   ├── consultation/
│   │   │   │   ├── index.ts
│   │   │   │   ├── ConversationDisplay.tsx
│   │   │   │   ├── ConversationPane.tsx
│   │   │   │   ├── PatientForm.tsx
│   │   │   │   ├── PrescriptionPane.tsx
│   │   │   │   ├── VoiceConsultation.tsx
│   │   │   ├── layout/
│   │   │   │   ├── index.ts
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Footer.tsx
│   │   │   ├── speech/
│   │   │   │   ├── index.ts
│   │   │   │   ├── SpeechControls.tsx
│   │   │   │   ├── VoiceInput.tsx
│   │   │   └── ui/ # Reusable UI components
│   │   │   │   ├── Alert.tsx
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── index.ts
│   │   │   │   ├── ProgressBar.tsx
│   │   │   │   ├── Select.tsx
│   │   │   │   ├── Spinner.tsx
│   │   │   │   └── TextArea.tsx
│   │   ├── hooks/
│   │   │   ├── index.ts
│   │   │   ├── useAudioRecording.ts
│   │   │   ├── useLocalStorage.ts
│   │   │   ├── useSpeechRecognition.ts
│   │   │   ├── useSpeechSynthesis.ts
│   │   ├── utils/
│   │   │   ├── index.ts
│   │   │   ├── constants.ts
│   │   │   └── consultation.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── public/
│   ├── Dockerfile
│   ├── env.d.ts
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
|   ├── package-lock.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── .gitignore
├── .pylintrc
├── docker-compose.yml
├── otel-config.yml
├── package.json
└── README.md
```
