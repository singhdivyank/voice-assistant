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
│   │   │   ├── schemas.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── diagnosis.py
│   │   │   │   ├── health_checks.py
│   │   │   │   ├── helpers.py
│   │   │   │   ├── monitoring.py
│   │   │   │   ├── prescription.py
│   │   │   │   ├── sessions.py
│   │   │   │   ├── workflow_routes.py
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
│   │   │   ├── llm_manager.py
│   │   │   ├── mcp_client.py
│   │   │   ├── prescription.py
│   │   │   ├── crew_ai/
│   │   │   │   ├── tools/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── gmail_mcp_tools.py
│   │   │   │   │   ├── medical_tools.py
│   │   │   │   ├── workflows/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── mcp_workflow.py
│   │   │   │   │   └── session_workflow.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── medical_agents.py
│   │   │   │   └── medical_crew.py
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
│   │   │   ├── backstories.py
│   │   │   ├── consts.py
│   │   │   ├── exceptions.py
│   │   │   ├── file_handler.py
│   │   │   ├── helpers.py
│   │   │   └── task_descriptions.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── integration/
│   │   └── unit/
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
