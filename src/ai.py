import openai
import os
from dataclasses import dataclass

from config import Config


class Ai:
    def __init__(self, config: Config) -> None:
        self.config = config

        openai.api_key = os.environ["OPENAI_API_KEY"]

        self.reset_conversation()

    def reset_conversation(self) -> None:
        self.messages = [
            {"role": "system", "content": self.config.SystemMessage}]

    def conversate(self, text: str) -> None | str:
        self.messages.append(
            {"role": "user", "content": text}
        )

        try:
            chat_completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=self.messages, timeout=10
            )

            response_text = chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(e)
            return None

        if not response_text:
            return None

        self.messages.append({"role": "system", "content": response_text})

        return response_text


@dataclass
class AiResponse:
    failed: bool = False
    responded: bool = False
    text: str = ""

    def reset(self) -> None:
        self.failed = False
        self.responded = False
        self.text = ""
