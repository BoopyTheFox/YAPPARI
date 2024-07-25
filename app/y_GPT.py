import os
import re
import base64
import openai
from openai import AsyncOpenAI
import tiktoken
import json

from youtube_transcript_api import ( 
    YouTubeTranscriptApi, 
    NoTranscriptFound, 
    TranscriptsDisabled, 
    NoTranscriptAvailable
)

from y_DB import (
    history_get,
    history_update,
    key_get
)

from dotenv import load_dotenv
load_dotenv("y_secrets.env")

openai.api_key = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI()

DEFAULT_MODEL              = "gpt-4o-mini"
DEFAULT_TEMPERATURE        = "0.7"
DEFAULT_PROMPT             = "You are a helpful assistant"
DEFAULT_MAX_TOKENS         = "3000"
DEFAULT_MAX_HISTORY_TOKENS = "4096"


######################
## HELPER_FUNCTIONS ##
######################


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def extract_video_id(url):
    # "...youtube.com/watch?v=..." or "...youtu.be/..."
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else url


# Combine the transcript into a single string
async def get_video_transcript(video_id, lang='en'):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
    except (NoTranscriptFound, TranscriptsDisabled, NoTranscriptAvailable):
        # Fetch list of available transcripts and try the first available language
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcripts:
            if transcript.is_generated:  # Check if the transcript is auto-generated
                return " ".join([t['text'] for t in transcript.fetch()])
        raise
    return " ".join([t['text'] for t in transcript])

## generate_video_summary() bypasses GPT_history, because transcripts can get really large
## this makes them effectively clear history when limit_history() kicks in 
async def generate_video_summary(
        transcript, questions,
        model, prompt, temperature, max_tokens):
    if questions == "":
        messages=[
            {"role": "system", "content": prompt},
            {"role": "system", "content": f"Summarize the following video based on it's transcript:\n\n{transcript}"}
        ]
    else:
        messages=[
            {"role": "system", "content": prompt},
            {"role": "system", "content": f"Summarize the following video based on it's transcript:\n\n{transcript}"},
            {"role": "user", "content": questions}
        ]

    completion = await openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    #max_tokens=150  # Adjust the number of tokens based on your needs)
    #temperature=0
    response = completion.choices[0].message.content.strip()
    return response


## If > MAX_HISTORY_TOKENS, cut oldest messsage and check again until < MAX_HISTORY_TOKENS
## This check is no longer necessary, as gpt-4o and gpt-4o-mini context window can get as huge as 128k
## I still left it in place if user wants to spend less on input tokens
async def limit_history(history, model, max_history_tokens):
    encoding = tiktoken.encoding_for_model(model)
    history_json = json.dumps(history, ensure_ascii=False)      # Convert history to text
    num_tokens = len(encoding.encode(history_json))             # Calculate number of tokens in the history
    if num_tokens <= max_history_tokens:
        return history
    while num_tokens > max_history_tokens:
        history.pop(0)                                          # Remove the first item from the history
        history_json = json.dumps(history, ensure_ascii=False)  # Convert updated history to text
        num_tokens = len(encoding.encode(history_json))         # Count tokens
    return history


def load_settings(chat_id):
    model = key_get(chat_id, 'model') or DEFAULT_MODEL
    prompt = key_get(chat_id, 'prompt') or DEFAULT_PROMPT
    temperature = float(key_get(chat_id, 'temperature') or DEFAULT_TEMPERATURE)
    max_tokens = int(key_get(chat_id, 'max_tokens') or DEFAULT_MAX_TOKENS)
    max_history_tokens = int(key_get(chat_id, 'max_history_tokens') or DEFAULT_MAX_HISTORY_TOKENS)
    return {
        'model': model,
        'prompt': prompt,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'max_history_tokens': max_history_tokens
    }


######################
## ACTUAL_FUNCTIONS ##
######################


async def GPT_query(chat_id, query):
    history = history_get(chat_id)
    settings = load_settings(chat_id)

    model = settings['model']
    prompt = settings['prompt']
    temperature = settings['temperature']
    max_tokens = settings['max_tokens']
    max_history_tokens = settings['max_history_tokens']

    if not history:
        history.append({"role": "system", "content": prompt})
        history_update(chat_id, history)

    history.append({"role": "user", "content": query})
    history = await limit_history(history, model, max_history_tokens)
    
    completion = await openai_client.chat.completions.create(
        model=model, 
        temperature=temperature,
        messages=history,
        max_tokens=max_tokens
    )
    response = completion.choices[0].message.content

    history.append({"role": "assistant", "content": response})
    history_update(chat_id, history)
    return response


async def GPT_summarize(chat_id, video_link, questions):
    history = history_get(chat_id)
    settings = load_settings(chat_id)

    model = settings['model']
    prompt = settings['prompt']
    temperature = settings['temperature']
    max_tokens = settings['max_tokens']
    max_history_tokens = settings['max_history_tokens']

    if not history:
        history.append({"role": "system", "content": prompt})
        history_update(chat_id, history)

    try:
        video_id = extract_video_id(video_link)
        transcript_text = await get_video_transcript(video_id)
        summary = await generate_video_summary(
            transcript_text, questions, 
            model, prompt, temperature, max_tokens,
        )
    except NoTranscriptFound:
        error_msg = f"No transcript found for video ID {video_id}."
        return error_msg
    except TranscriptsDisabled:
        error_msg = f"Transcripts are disabled for video ID {video_id}."
        return error_msg
    except NoTranscriptAvailable:
        error_msg = f"No transcript is available for video ID {video_id}."
        return error_msg
    except Exception as e:
        error_msg = f"An error occurred: {e}"
        return error_msg

    history.append({"role": "user", "content": video_link + " " + questions})
    history.append({"role": "system", "content": "[FULL_VIDEO_TRANSCRIPT,OMITTED_IN_CHAT_HISTORY]"})
    history.append({"role": "system", "content": "[YOUR_SUMMARY_OF_A_VIDEO_TRANSCRIPT]:"})
    history.append({"role": "assistant", "content": summary})

    history = await limit_history(history, model, max_history_tokens)
    history_update(chat_id, history)

    return summary


async def GPT_recognize(chat_id, base64_image, caption):
    # Get the current history and settings
    history = history_get(chat_id)
    settings = load_settings(chat_id)

    model = settings['model']
    prompt = settings['prompt']
    temperature = settings['temperature']
    max_tokens = settings['max_tokens']
    max_history_tokens = settings['max_history_tokens']

    if not history: 
        history.append({"role": "system", "content": prompt})
        history_update(chat_id, history)

    completion = await openai_client.chat.completions.create(
      model=model,
      temperature=temperature,
      max_tokens=max_tokens,
      messages=history + [
        {
          "role": "user",
          "content": [
            {"type": "text", "text": f"{caption}"},
            {
              "type": "image_url",
              "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
              },
            },
          ],
        }
      ],
    ) 
    
    response = completion.choices[0]
    response_message = response.message.content

    history.append({"role": "system", "content": "[PICTURE,OMITTED_IN_CHAT_HISTORY]"})
    history.append({"role": "user", "content": caption})
    history.append({"role": "system", "content": "[YOUR_DESCRIPTION_OF_AN_IMAGE]:"})
    history.append({"role": "assistant", "content": response_message})
    history = await limit_history(history, model, max_history_tokens)
    history_update(chat_id, history)

    return response
