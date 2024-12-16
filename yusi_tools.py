from ast import literal_eval
import requests
import time
import importlib
import random
from yusi_utils import retrieve

OPENROUTER_API_KEY = retrieve("OpenRouter")
RAINBOWEYE_API_KEY = retrieve("RainbowEye")
EXCELLENCE2_API_KEY = retrieve("Excellence2Key")
EXCELLENCE2_ENDPOINT = retrieve("Excellence2Endpoint")


def execute(tool_calls):
    try:
        results = {
            f"{name}({arguments})": globals().get(name)(**literal_eval(arguments))
            for tool_call in tool_calls
            if (function := tool_call.get("function"))
            if (name := function.get("name")) and (arguments := function.get("arguments"))
            if name in globals()
        }
        return results
    except Exception as e:
        print(f"Failed to execute tool calls: {e}")
        return None


def request_llm(url, headers, data, delay=1):
    for attempt in range(3):
        try:
            print(f"Sending request to {url} with {data}")
            response = requests.post(url, headers=headers, json=data, timeout=180).json()
            print(response)
            if (message := response.get("choices", [{}])[0].get("message", {})):
                if (tool_calls := message.get("tool_calls")):
                    if (results := execute(tool_calls)):
                        return f"The following dictionary contains the results:\n{results}"
                elif (content := message.get("content")):
                    return content
            raise Exception("Invalid response structure or execution failed")
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(delay)
                delay *= 2
    print("Failed to get a valid response after maximum retries")
    return None


class LLM:
    def __init__(self, url, api_key):
        self.url = url
        self.api_keys = [api_key] if isinstance(api_key, str) else api_key

    def __call__(self, messages, model, temperature, top_p, response_format=None, tools=None):
        headers = {
            "Authorization": f"Bearer {random.choice(self.api_keys)}"
        }
        data = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "top_p": top_p,
            **({"response_format": response_format} if response_format else {}),
            **({"tools": tools} if tools else {})
        }
        return request_llm(self.url, headers, data)


class Azure:
    def __init__(self, endpoint, api_key):
        self.endpoint = endpoint
        self.api_key = api_key

    def __call__(self, messages, model, temperature, top_p, response_format=None, tools=None):
        url = f"{self.endpoint}openai/deployments/{model}/chat/completions?api-version=2024-05-01-preview"
        headers = {
            "api-key": self.api_key
        }
        data = {
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            **({"response_format": response_format} if response_format else {}),
            **({"tools": tools} if tools else {})
        }
        return request_llm(url, headers, data)


openrouter = LLM("https://openrouter.ai/api/v1/chat/completions", OPENROUTER_API_KEY)
rainboweye = LLM("https://gitaigc.com/v1/chat/completions", RAINBOWEYE_API_KEY)
excellence2 = Azure(EXCELLENCE2_ENDPOINT, EXCELLENCE2_API_KEY)


def get_prompt(prompt, **arguments):
    if arguments:
        return getattr(importlib.import_module(f"aife_prompts.{prompt}"), prompt).format(**arguments)
    else:
        return getattr(importlib.import_module(f"aife_prompts.{prompt}"), prompt)


def get_response_format(response_format):
    if response_format:
        return getattr(importlib.import_module(f"aife_response_formats.{response_format}"), response_format)
    return None


def get_tools(tools):
    if tools:
        return [getattr(importlib.import_module("aife_tools"), tool) for tool in tools]
    return None


class Chat:
    def __call__(self, llms, messages, response_format=None, tools=None):
        for llm in llms:
            try:
                results = globals()[llm_dict[llm]["name"]](messages, **llm_dict[llm]["arguments"], response_format=response_format, tools=tools)
                if results:
                    return results
            except Exception:
                continue
        return None

chat = Chat()

def internal_text_chat(ai, system_message, user_message, response_format=None, tools=None):
    llms = ai_dict[ai]["llms"]
    messages = [{"role": "system", "content": system_message}, {"role": "user", "content": user_message}]
    return chat(llms, messages, response_format, tools)


ai_dict = {
    "GPT for article processing": {
        "llms": ["gpt4o_mini_rainboweye", "gpt4o_mini_openrouter", "gpt4o_mini_excellence2"],
        "system_message": "summarise_an_article",
        "response_format": None,
        "tools": None
    }
}

llm_dict = {
    "gpt4o_mini_rainboweye": {
        "name": "rainboweye",
        "arguments": {
            "model": "gpt-4o-mini-2024-07-18",
            "temperature": 0.3,
            "top_p": 0.9
        }
    },
    "gpt4o_mini_openrouter": {
        "name": "openrouter",
        "arguments": {
            "model": "openai/gpt-4o-mini-2024-07-18",
            "temperature": 0.3,
            "top_p": 0.9
        }
    },
    "gpt4o_mini_excellence2": {
        "name": "excellence2",
        "arguments": {
            "model": "yusi-mini",
            "temperature": 0.3,
            "top_p": 0.9
        }
    }
}


def filter_words(text, words):
    for word in words:
        text = text.replace(word, '')
    return text
