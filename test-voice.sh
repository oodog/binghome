#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python -c "
import speech_recognition as sr
import pyttsx3

# Test TTS
engine = pyttsx3.init()
engine.say('Hello, BingHome Hub voice system is working')
engine.runAndWait()

# Test microphone
r = sr.Recognizer()
m = sr.Microphone()
with m as source:
    r.adjust_for_ambient_noise(source)
    print('Say something!')
    audio = r.listen(source, timeout=5)
    try:
        text = r.recognize_google(audio)
        print(f'You said: {text}')
    except:
        print('Could not understand audio')
"
