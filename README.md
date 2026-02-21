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
│   │   │   │   └── prescription.py
│   │   │   ├── schemas/         # Pydantic models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── diagnosis.py
│   │   │   │   ├── patient.py
│   │   │   │   └── session.py
│   │   │   └── middleware/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── error_handler.py
│   │   │   │   └── logging.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── monitoring.py
│   │   │   └── settings.py
│   │   ├── core/                
│   │   │   ├── __init__.py
│   │   │   ├── diagnosis.py
│   │   │   └── prescription.py
│   │   ├── services/      
│   │   │   ├── __init__.py
│   │   │   ├── session_store.py      
│   │   │   ├── speech.py
│   │   │   └── translation.py
│   │   └── utils/
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
│   └── app.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     # React TypeScript frontend
│   ├── src/
│   │   ├── api/
│   │   │   ├── index.ts
│   │   │   ├── client.ts        # API client
│   │   │   └── types.ts         # TypeScript types
│   │   ├── components/
│   │   │   ├── consultation/
│   │   │   │   ├── index.ts
│   │   │   │   ├── PatientForm.tsx
│   │   │   │   ├── ComplaintInput.tsx
│   │   │   │   ├── QuestionAnswer.tsx
│   │   │   │   ├── DiagnosisView.tsx
│   │   │   |   └── PrescriptionCard.tsx
│   │   │   ├── layout/
│   │   │   │   ├── index.ts
│   │   │   │   ├── Container.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Footer.tsx
│   │   │   |   └── ProgressSteps.tsx
│   │   │   ├── speech/
│   │   │   │   ├── index.ts
│   │   │   │   ├── SpeechControls.tsx
│   │   │   |   └── VoiceInput.tsx              
│   │   │   └── ui/ # Reusable UI components
│   │   │       ├── Alert.tsx
│   │   │       ├── Button.tsx
│   │   │       ├── Card.tsx
│   │   │       ├── Input.tsx
│   │   │       ├── index.ts
│   │   │       ├── ProgressBar.tsx
│   │   │       ├── Select.tsx
│   │   │       ├── Spinner.tsx
│   │   │       └── TextArea.tsx
│   │   ├── hooks/
│   │   │   ├── index.ts
│   │   │   ├── useConsultation.ts
│   │   │   ├── useLocalStorage.ts
│   │   │   ├── useSpeechRecognition.ts
│   │   │   ├── useSpeechSynthesis.ts
│   │   │   └── useStreamingResponse.ts
│   │   ├── store/               # State management
│   │   │   ├── index.ts
│   │   │   ├── consultationStore.ts
│   │   │   └── settingsStore.ts
│   │   ├── utils/
│   │   │   ├── index.ts
│   │   │   ├── constants.ts
│   │   │   └── helpers.ts
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
