import json
import os
import sys
import textwrap
from configparser import ConfigParser

from openai import OpenAI
from openai.types import ChatModel
from typing_extensions import get_args

KEY = os.getenv("OPENAI_HOWTO_TOKEN")

if KEY is None:
    raise ValueError("No token found in environment variables.")

CLIENT = OpenAI(api_key=KEY)

HISTORY_FILE = os.path.expanduser("~/.howto_history")
CONFIG_FILE = os.path.expanduser("~/.howto_config")

def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def save_history(history) -> None:
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def load_config() -> ConfigParser:
    config = ConfigParser()
    config.read(CONFIG_FILE)

    if not config.has_section("ai model"):
        config.add_section("ai model")
    if not config.has_option("ai model", "model"):
        config["ai model"]["model"] = "gpt-4o-mini"
    if not config.has_option("ai model", "history"):
        config["ai model"]["history"] = "6"

    return config

def save_config(config: ConfigParser) -> None:
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

def print_help() -> None:
    print(
"""
Usage: howto [question] [OPTIONS] [--help]


Query's Openai's api for information about any given question.

--setmodel              Sets the model used by howto (located in ~/.howto_config).
                        Use without arguments to query the model.
                
--sethistory            Sets the length of howto's history. Use without arguments
                        to query the history length.

--printhistory, -ph     Formats and prints the history.          

--clearhistory          Clears the local history (located in ~/.howto_history).

--help, -h              Prints this message.
"""
    )
    sys.exit(1)

def main() -> None:
    config = load_config()
    arg1 = sys.argv[1] if len(sys.argv) > 1 else None
    arg2 = sys.argv[2] if len(sys.argv) > 2 else None
    if arg1 is not None and arg1.startswith('-'):
        if arg1 in ["--help", "-h"]:
            print_help()
            sys.exit(1)
        elif arg1 == "--clearhistory":
            save_history([])
            print("Cleared history.")
            sys.exit(1)
        elif arg1 == "--setmodel":
            if arg2 is None:
                print(f"Current model is: '{config["ai model"]["model"]}'")
                sys.exit(1)

            if arg2 not in get_args(ChatModel):
                print(f"Invalid model: '{arg2}'")
                sys.exit(1)

            config["ai model"]["model"] = arg2
            save_config(config)
            print(f"Model set to: '{config["ai model"]["model"]}'")
            sys.exit(1)
        elif arg1 == "--sethistory":
            if arg2 is None:
                print(f"History length is: {config["ai model"]["history"]}")
                sys.exit(1)

            if not arg2.isdigit():
                print(f"History length must be a number.")
                sys.exit(1)

            config["ai model"]["history"] = str(arg2)
            save_config(config)
            print(f"History length set to: {config["ai model"]["history"]}")
            sys.exit(1)
        elif arg1 in ["--printhistory", "-ph"]:
            wrapper = textwrap.TextWrapper(width=os.get_terminal_size().columns - 6, drop_whitespace=False)
            for entry in load_history():
                if entry["role"] != "assistant":
                    for line in wrapper.wrap(entry["content"]):
                        print(f"# {line}")
                else:
                    for line in entry["content"].split("\n"):
                        for line2 in wrapper.wrap(line):
                            print(f"   # {line2}")
            sys.exit(1)
        print_help()

    question = " ".join(sys.argv[1:]).strip()

    if not question:
        print_help()
        sys.exit(1)

    history = load_history() + [{"role":"user", "content": question}]

    response = CLIENT.chat.completions.create(
        model=config["ai model"]["model"],
        messages=[{"role":"system", "content": "You are an assistant contacted via a 'howto' CLI command. Questions may be formatted weirdly. If so, assume each question is preceded with 'how to' or similar. If the question can be answered in one or two sentences without immediately important information, keep responses short."}] + history
    )

    answer = response.choices[0].message.content
    lines = answer.split("\n")
    print(f'#')
    wrapper = textwrap.TextWrapper(width=os.get_terminal_size().columns - 6, drop_whitespace=False)
    for line in lines:
        for line2 in wrapper.wrap(line):
            print(f'# {line2}')
    print('#')

    history.append({"role": "assistant", "content": answer})

    save_history(history[-int(config["ai model"]["history"]):])
    save_config(config)

if __name__ == "__main__":
    main()
