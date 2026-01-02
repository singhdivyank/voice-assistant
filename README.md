# DocJarvis- AI Medical Assistant

An AI-powered multilingual voice assistant for medical consultations. DocJarvis conducts initial patient assessments through voice interaction, supports 10 Indian languages, and generates consultation summaries.

> **Disclaimer:** This is an AI-assisted tool for educational purpose only. Always consult qualified healthcare professionals for medical advice.

## Features

* **Voice-based interaction**: Speech-to-text and text-to-spech capabilities

* **Multilingual support**: English +9 regional Indian languages

* **AI-powered diagnosis**: Uses Google's Gemini Pro for intellignet questioning

* **Prescription generation**: Automated consultation summary documents

* **User-friendly interface**: Gradio-based web UI

## Supported Languages

| Language | Code | Language | Code |
| -------- | ---- | -------- | ---- |
| English | en | Malayalam | ml |
| Bengali | bn | Marathi | mr |
| Gujarati | gu | Tamil | ta |
| Hindi | hi | Telugu | te |
| Kannada | kn | Urdu | ur |

## Quick Start

**Prerequisites**

* Python 3.10+
* Working microphone
* Internet connection
* Google AI Studio API key

**Installation**

1. **Clone the repository**

```bash
git clone https://github.com/singhdivyank/voice-assistant.git

cd docjarvis
```

2. **Create virtual environment**

```bash
python -m venv venv

source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run the application**

```bash
python -m src.app
```

**PyAudio installation on Mac**:

```bash
brew install portaudio

python3 -m pip install pyaudio
```

**PyAudio installation on Linux**:

```bash
sudo apt-get install python3-pyaudio portaudio19-dev

pip install pyaudio
```

## Configuration

Create a `.env` file with the following variables:

```bash
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional (defaults shown)
GRADIO_SERVER_NAME=0.0.0.0
GRADIO_SERVER_PORT=7860
```

## Usage

1. Open the web interface (default: http://localhost:7860)
2. Select your preferred language
3. Enter your gender and age
4. Click Submit to start the consultation
5. Speak your symptoms when prompted
6. Answer follow-up questions verbally
7. Receive your consultation summary

## Project Structure

```

voice-assistant/
├── src/
│   ├── config/          # Configuration and settings
│   │   └── settings.py  # App config, prompts, enums
│   ├── core/            # Core business logic
│   │   ├── diagnosis.py # LLM-powered diagnosis
│   │   └── prescription.py
│   ├── services/        # External service integrations
│   │   ├── speech.py    # STT/TTS services
│   │   └── translation.py
│   ├── utils/           # Utilities and helpers
│   │   ├── exceptions.py
│   │   └── file_handler.py
│   └── app.py           # Main application
├── requirements.txt
└── README.md

```

## API Reference

### DiagnosisService

```
from src.core.diagnosis import DiagnosisService, PatientInfo
from src.config.settings import Gender

service = DiagnosisService()
patient = PatientInfo(age=30, gender=Gender.MALE)

# Create session with diagnostic questions
session = service.create_session(patient, "I have a headache")

# Add patient responses
service.add_response(session, 0, "It started yesterday")

# Get recommendations
recommendations = service.complete_session(session)
```

### TranslationService

```
from src.services.translation import TranslationService
from src.config.settings import Language

translator = TranslationService(Language.HINDI)

# Translate for LLM (to English)
english_text = translator.to_english("सिरदर्द है")

# Translate for user
hindi_text = translator.to_user_language("Take rest")
```
