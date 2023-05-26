import openai
import os
from dataclasses import dataclass


class Ai:
    def __init__(self):
        openai.api_key = os.environ["OPENAI_API_KEY"]

        self.SYSTEM_MESSAGE = "Je bent een Sociale Robot genaamd Pepper. Je maakt conversatie met mensen. Hou je antwoorden kort. Gedraag je als een mens."

        self.reset_conversation()

    def reset_conversation(self) -> None:
        self.messages = [{"role": "system", "content": self.SYSTEM_MESSAGE}]

    def conversate(self, text: str) -> None | str:
        self.messages.append(
            {"role": "user", "content": text + " | Hou je antwoord kort."}
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
