from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1", api_key="not-needed"
)

# with client.audio.speech.with_streaming_response.create(
#     model="kokoro",
#     voice="af_bella", #single or multiple voicepack combo
#     input="Hello world!"
#   ) as response:
#     #   response.stream_to_file("output.mp3")
#     response.

response = client.audio.speech.create(
    model="kokoro",           # Or "tts-1-hd" / "gpt-4o-mini-tts"
    voice="af_heart",         # Pass the name of the voice directly
    input="Hello! This is a demonstration of the selected OpenAI TTS voice."
)

# Save the audio file
response.stream_to_file("output_shimmer.mp3")