import json
import os
import sys
import textwrap

from openai import OpenAI
from openai.types import ChatModel
from typing_extensions import get_args

KEY = os.getenv("OPENAI_HOWTO_TOKEN")

if KEY is None:
    raise ValueError("No token found in environment variables.")

CLIENT = OpenAI(api_key=KEY)

HISTORY_FILE = os.path.expanduser("~/.howto_history")

model = "gpt-4o"

def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def save_history(history) -> None:
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def print_help() -> None:
    print(
"""
Usage: howto [question] [--setmodel <model>] [--clearhistory] [--help]


Query's Openai's api for information about any given question.

--setmodel      Sets the model used by howto. Use without arguments to
                query the model.

--clearhistory  Clears the local history (located in ~/.howto_history).

--help, -h      Prints this message.
"""
    )

def main() -> None:
    global model
    arg1 = sys.argv[1] if len(sys.argv) > 1 else None
    arg2 = sys.argv[2] if len(sys.argv) > 2 else None
    if arg1 == "--help" or arg1 == "-h":
        print_help()
        sys.exit(1)
    elif arg1 == "--clearhistory":
        save_history([])
        print("Cleared history.")
        sys.exit(1)
    elif arg1 == "--setmodel":
        if arg2 is None:
            print(f"Current model is: '{model}'")
            sys.exit(1)

        if arg2 not in get_args(ChatModel):
            print(f"Invalid model: '{arg2}'")
            sys.exit(1)

        model = arg2
        print(f"Model set to: '{model}'")
        sys.exit(1)

    question = " ".join(sys.argv[1:]).strip()

    if not question:
        print_help()
        sys.exit(1)

    history = load_history() + [{"role":"user", "content": question}]

    response = CLIENT.chat.completions.create(
        model=model,
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

    save_history(history[-10:])

if __name__ == "__main__":
    main()