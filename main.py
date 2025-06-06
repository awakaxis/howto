import json
import os
import sys
import textwrap
from configparser import ConfigParser
from typing import Optional

from openai import OpenAI
from openai.types import ChatModel
from typing_extensions import get_args

KEY = os.getenv("OPENAI_HOWTO_TOKEN")

if KEY is None:
    raise ValueError("No token found in environment variables.")

CLIENT = OpenAI(api_key=KEY)

HOWTO_DIR = os.path.expanduser("~/.howto/")
HISTORY_FILE = HOWTO_DIR + "history.json"
CONFIG_FILE = HOWTO_DIR + "config.ini"
USERINFO_FILE = HOWTO_DIR + "userinfo.txt"

os.makedirs(HOWTO_DIR, exist_ok=True)


def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
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

    if not config.has_section("user info"):
        config.add_section("user info")
    if not config.has_option("user info", "globalcontext"):
        config["user info"]["globalcontext"] = "[User has not set any userinfo]"

    if not config.has_section("project context"):
        config.add_section("project context")

    return config


def save_config(config: ConfigParser) -> None:
    with open(CONFIG_FILE, "w") as f:
        config.write(f)


def set_userinfo(config: ConfigParser, userinfo: str) -> None:
    config["user info"]["globalcontext"] = userinfo


def get_userinfo(config: ConfigParser) -> str:
    return config["user info"]["globalcontext"]


def set_history_length(config: ConfigParser, length: str) -> None:
    config["ai model"]["history"] = length


def get_history_length(config: ConfigParser) -> str:
    return config["ai model"]["history"]


def set_model(config: ConfigParser, model: str) -> None:
    config["ai model"]["model"] = model


def get_model(config: ConfigParser) -> str:
    return config["ai model"]["model"]


def set_project_context(
    config: ConfigParser, directory: str, context: Optional[str]
) -> None:
    if context is None:
        config.remove_option("project context", directory)
    else:
        config["project context"][directory] = context


def get_project_context(config: ConfigParser, directory: str) -> str:
    return config["project context"].get(directory, "[The user has not set context]")


def print_help() -> None:
    print(
        f"""
Usage: howto [question] [OPTIONS] [--help, -h]


Query's Openai's api for information about any given question.

--setmodel                  Sets the model used by howto (located in ~/.howto_config).
                            Use without arguments to query the model.
                
--sethistory                Sets the length of howto's history. Use without arguments
                            to query the history length.

--printhistory, -ph         Formats and prints the history.          

--clearhistory, -ch         Clears the local history (located in {HISTORY_FILE}).

--setuserinfo, -su          Sets the userinfo--information that is always prepended
                            to the bot's memory.

--clearuserinfo, -cu        Clears userinfo.

--setprojectcontext, -sp    Sets the project context for the CWD.

--clearprojectcontext, -cp  Clears project context for the CWD.

--continuous, -c            Enters continuous mode--keeps the dialogue open until
                            'quit' is entered.

--help, -h                  Prints this message.
"""
    )
    sys.exit(1)


def main() -> None:
    config = load_config()
    arg1 = sys.argv[1] if len(sys.argv) > 1 else None
    arg2 = sys.argv[2] if len(sys.argv) > 2 else None
    if arg1 is not None and arg1.startswith("-"):
        if arg1 in ["--help", "-h"]:
            print_help()
        elif arg1 in ["--clearhistory", "-ch"]:
            save_history([])
            print("Cleared history.")
            sys.exit(1)
        elif arg1 == "--setmodel":
            if arg2 is None:
                print(f"Current model is: '{get_model(config)}'")
                sys.exit(1)

            valid_models = get_args(ChatModel)
            if arg2 not in valid_models:
                print(f"Invalid model: '{arg2}'")
                print(f"Must be one of:\n{'\n'.join(valid_models)}")
                sys.exit(1)

            set_model(config, arg2)
            save_config(config)
            print(f"Model set to: '{get_model(config)}'")
            sys.exit(1)
        elif arg1 == "--sethistory":
            if arg2 is None:
                print(f"History length is: {get_history_length(config)}")
                sys.exit(1)

            if not arg2.isdigit():
                print(f"History length must be a number.")
                sys.exit(1)

            set_history_length(config, arg2)
            save_config(config)
            print(f"History length set to: {get_history_length(config)}")
            sys.exit(1)
        elif arg1 in ["--printhistory", "-ph"]:
            wrapper = textwrap.TextWrapper(
                width=os.get_terminal_size().columns - 6, drop_whitespace=False
            )
            for entry in load_history():
                if entry["role"] != "assistant":
                    for line in wrapper.wrap(entry["content"]):
                        print(f"# {line}")
                else:
                    for line in entry["content"].split("\n"):
                        for line2 in wrapper.wrap(line):
                            print(f"   # {line2}")
            sys.exit(1)
        elif arg1 in ["--setuserinfo", "-su"]:
            userinfo = " ".join(sys.argv[2:]).strip()
            if userinfo == "":
                print(f"Current userinfo is:\n{get_userinfo(config)}")
            else:
                set_userinfo(config, userinfo)
                save_config(config)
                print(f"Set userinfo to:\n{get_userinfo(config)}")
            sys.exit(1)
        elif arg1 in ["--clearuserinfo", "-cu"]:
            set_userinfo(config, "[User has not set any userinfo]")
            save_config(config)
            print("Cleared userinfo.")
            sys.exit(1)
        elif arg1 in ["--continuous", "-c"]:
            while True:
                PROMPT = f"Ask {get_model(config)} >> "

                query = input(PROMPT)
                if query == "quit":
                    print("Goodbye.")
                    sys.exit(1)
                else:
                    run_query(query, config)
        elif arg1 in ["--setprojectcontext", "-sp"]:
            context = " ".join(sys.argv[2:]).strip()

            if context == "":
                print(f"CWD context is:\n{get_project_context(config, os.getcwd())}")
            else:
                set_project_context(config, os.getcwd(), context)
                save_config(config)
                print(
                    f"Set CWD context to:\n{get_project_context(config, os.getcwd())}"
                )
            sys.exit(1)
        elif arg1 in ["--clearprojectcontext", "-cp"]:
            set_project_context(config, os.getcwd(), None)
            save_config(config)
            print("Cleared project context.")
            sys.exit(1)

    run_query(" ".join(sys.argv[1:]).strip(), config)


def run_query(query, config) -> None:
    if not query:
        print_help()

    history = load_history() + [{"role": "user", "content": query}]
    userinfo = get_userinfo(config)
    project_context = get_project_context(config, os.getcwd())

    response = CLIENT.chat.completions.create(
        model=get_model(config),
        messages=[
            {
                "role": "system",
                "content": "You are an assistant contacted via a 'howto' CLI command. Questions may be formatted weirdly. If so, assume each question is preceded with 'how to' or similar. If the question can be answered in one or two sentences without immediately important information, keep responses short.",
            },
            {
                "role": "system",
                "content": f'The user provided the following information about themself or their system or platform for context: "{userinfo}"',
            },
            {
                "role": "system",
                "content": f'The user provided the following information about the current project / working directory for context: "{project_context}"',
            },
        ]
        + history,
    )

    answer = response.choices[0].message.content
    if not answer:
        raise ValueError("OpenAI response is empty")
    lines = answer.split("\n")
    print(f"#")
    wrapper = textwrap.TextWrapper(
        width=os.get_terminal_size().columns - 6, drop_whitespace=False
    )
    for line in lines:
        for line2 in wrapper.wrap(line):
            print(f"# {line2}")
    print("#")

    history.append({"role": "assistant", "content": answer})

    save_history(history[-int(config["ai model"]["history"]) :])
    save_config(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt as e:
        # gotta do this otherwise shell prompt looks ugly upon KeyboardInterrupt
        print("")
        sys.exit(1)
