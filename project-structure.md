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
│   │   │   │   └── prescription.py
│   │   │   │   ├── sessions.py
│   │   │   ├── schemas/         # Pydantic models
│   │   │   │   ├── __init__.py
│   │   │   │   └── diagnosis.py
│   │   │   │   ├── patient.py
│   │   │   │   ├── session.py
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── error_handler.py
│   │   │       └── logging.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── monitoring.py
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
│   │       ├── __init__.py
│   │       ├── consts.py
│   │       ├── exceptions.py
│   │       └── file_handler.py
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
│
├── frontend/                     # React TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/              # Reusable UI components
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   └── index.ts
│   │   │   ├── consultation/
│   │   │   │   ├── PatientForm.tsx
│   │   │   │   ├── ComplaintInput.tsx
│   │   │   │   ├── QuestionAnswer.tsx
│   │   │   │   ├── DiagnosisView.tsx
│   │   │   │   └── PrescriptionCard.tsx
│   │   │   ├── speech/
│   │   │   │   ├── VoiceInput.tsx
│   │   │   │   └── SpeechControls.tsx
│   │   │   └── layout/
│   │   │       ├── Header.tsx
│   │   │       ├── Footer.tsx
│   │   │       └── ProgressSteps.tsx
│   │   ├── hooks/
│   │   │   ├── useConsultation.ts
│   │   │   ├── useSpeechRecognition.ts
│   │   │   ├── useSpeechSynthesis.ts
│   │   │   └── useStreamingResponse.ts
│   │   ├── api/
│   │   │   ├── client.ts        # API client
│   │   │   └── types.ts         # TypeScript types
│   │   ├── store/               # State management
│   │   │   ├── consultationStore.ts
│   │   │   └── settingsStore.ts
│   │   ├── utils/
│   │   │   ├── constants.ts
│   │   │   └── helpers.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── docker-compose.yml
├── otel-config.yml
├── .pylintrc
├── package.json
├── package-lock.json
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
└── README.md
```