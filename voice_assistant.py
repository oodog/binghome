import azure.cognitiveservices.speech as speechsdk
import webbrowser
import os
import sys
import time
import requests

# Replace with your Azure Speech service key and region
speech_key = "YOUR_AZURE_SPEECH_KEY"
service_region = "YOUR_AZURE_SERVICE_REGION"

# Flask server URL
flask_url = "http://localhost:5000/update_url"

# Define commands and their corresponding actions
commands = {
    "open xbox live": "https://www.xbox.com/en-US/live",
    "load youtube": "https://www.youtube.com"
}

def recognize_speech_once():
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language = "en-US"

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print("Listening for wake word 'Hey Bing'...")

    result = speech_recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"Recognized: {result.text}")
        return result.text.lower()
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Speech Recognition canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")
    return ""

def synthesize_speech(text):
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_synthesis_language = "en-US"
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    speech_synthesizer.speak_text_async(text).get()

def execute_command(command):
    if command in commands:
        url = commands[command]
        try:
            response = requests.post(flask_url, json={"url": url})
            if response.status_code == 200:
                response_text = f"Opening {command}."
            else:
                response_text = "Failed to execute the command."
        except Exception as e:
            response_text = f"An error occurred: {e}"
    else:
        response_text = "I'm sorry, I didn't understand that command."
    print(response_text)
    synthesize_speech(response_text)

def main():
    while True:
        text = recognize_speech_once()
        if "hey bing" in text:
            synthesize_speech("Yes?")
            command = recognize_speech_once()
            if command:
                execute_command(command)
        # Short delay to prevent rapid looping
        time.sleep(1)

if __name__ == "__main__":
    main()
