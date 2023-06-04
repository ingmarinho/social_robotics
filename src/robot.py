from autobahn.twisted.util import sleep
from autobahn.wamp.types import SessionDetails
from autobahn.twisted.wamp import Session
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.component import Component, run as run_component
import time
import os
import random

from action import Action
from ai import Ai, AiResponse
from config import Config


class Robot:
    def __init__(self, config: Config, stt_certainty_threshold: float, max_wamp_retries: int = 0) -> None:
        self.config = config

        self.ai = Ai(config)
        self.ai_response = AiResponse()

        self.current_action = Action.Idle

        self.stt_certainty_threshold = stt_certainty_threshold

        self.in_conversation = False
        self.is_robot_speaking = False
        self.is_listening = False
        self.unclear_user_input = False

        self.wamp = Component(
            transports=[
                {
                    "url": "ws://wamp.robotsindeklas.nl",
                    "serializers": ["msgpack"],
                    "max_retries": max_wamp_retries,
                }
            ],
            realm=os.environ["WAMP_REALM"],
        )
        self.wamp.on_join(self._loop)

    def start(self) -> None:
        run_component([self.wamp])

    def set_action(self, action: Action) -> None:
        self.current_action = action

    def _get_random_compliment(self) -> str:
        return random.choice(self.config.Compliments)

    @inlineCallbacks
    def _speak(self, session: Session, text: str, delay_per_word_sec: float = 0.3) -> None:
        # set is_robot_speaking flag to True
        self.is_robot_speaking = True

        # set is_listening flag to False
        self.is_listening = False

        # robot speaks
        yield session.call("rie.dialogue.say", text=text)

        # wait for robot to finish speaking
        yield sleep(delay_per_word_sec * len(text.split(" ")))

        # set is_listening flag to True
        self.is_listening = True

        # set is_robot_speaking flag to False
        self.is_robot_speaking = False

    def _on_stt_result(self, frame: dict):
        if self.is_robot_speaking or not self.is_listening:
            return

        user_input: str = frame["data"]["body"]["text"]
        is_final: bool = frame["data"]["body"]["final"]
        stt_certainty: float = frame["data"]["body"]["certainty"]

        if not is_final:
            return

        if stt_certainty < self.stt_certainty_threshold:
            self.unclear_user_input = True
            return

        if not user_input.strip():
            return

        if (response := self.ai.conversate(user_input)) is None:
            self.ai_response.failed = True
            return

        self.in_conversation = True
        self.ai_response.text = response
        self.ai_response.responded = True

        print(f"user: {user_input}")
        print(f"ai: {self.ai_response.text}")

    @inlineCallbacks
    def _wait_for_user_input_timeout(
        self, session: Session, max_wait_time_sec: float = 30.0
    ) -> bool:
        self.is_listening = True

        max_end_time_sec = time.time() + max_wait_time_sec

        # wait for user input
        while max_end_time_sec >= time.time():
            if self.in_conversation:
                return True

            yield sleep(.5)

        self.is_listening = False

        return False

    @inlineCallbacks
    def _conversate(self, session: Session, max_wait_time_sec: float = 30) -> None:
        max_end_time_sec = time.time() + max_wait_time_sec

        # set flag to True
        self.is_listening = True

        while self.in_conversation and max_end_time_sec >= time.time():
            # ask user to repeat if input was unclear
            if self.unclear_user_input:
                # reset max_end_time_sec
                max_end_time_sec = time.time() + max_wait_time_sec

                # reset unclear_user_input flag
                self.unclear_user_input = False

                # reset ai response
                self.ai_response.reset()

                yield self._speak(session, "Kun je dat herhalen?")

                continue

            # stop if ai failed
            if self.ai_response.failed:
                # reset max_end_time_sec
                max_end_time_sec = time.time() + max_wait_time_sec

                yield self._speak(session, "Er is iets misgegaan, sorry!")
                break

            # still waiting for reply from ai
            if not self.ai_response.responded:
                yield sleep(.5)
                continue

            # robot speaks
            yield self._speak(session, self.ai_response.text)

            # reset ai response before opening stt stream again
            self.ai_response.reset()

            # reset max_end_time_sec
            max_end_time_sec = time.time() + max_wait_time_sec

        # reset flags
        self.in_conversation = False
        self.unclear_user_input = False
        self.is_listening = False

        # reset ai response
        self.ai_response.reset()

    @inlineCallbacks
    def _execute(self, session: Session, action: Action) -> None:
        match action:
            case Action.Idle:
                # print current action
                print("Idle")
            case Action.Gaze:
                # print current action
                print("Gaze")

                # change eye colour to light blue
                yield session.call(
                    "rom.actuator.light.write",
                    mode="linear",
                    frames=[{"time": 1, "data": {
                        "body.head.eyes": [173, 216, 230]}}],
                )

                # find face
                yield session.call("rie.vision.face.find")

                # change eye colour to purple after face found
                yield session.call(
                    "rom.actuator.light.write",
                    mode="linear",
                    frames=[{"time": 1, "data": {
                        "body.head.eyes": [173, 216, 230]}}],
                )
                # track face
                yield session.call("rie.vision.face.track")

                # wave right arm
                session.call("rom.optional.behavior.play",
                             name="BlocklyWaveRightArm")
            case Action.Verbal:
                print("Verbal")

                # change initial eye colour
                yield session.call(
                    "rom.actuator.light.write",
                    mode="linear",
                    frames=[{"time": 1, "data": {
                        "body.head.eyes": [173, 216, 230]}}],
                )

                compliment = self._get_random_compliment()

                # Enter default text
                yield self._speak(session, compliment)

                # ask user to ask a question
                yield self._speak(session, "Stel mij een vraag!")

                # wait for user to ask a question
                has_input = yield self._wait_for_user_input_timeout(session)
                if not has_input:
                    return

                # start conversation with user
                yield self._conversate(session)

                # say goodbye to user
                yield session.call("rie.dialogue.say", text="Tot ziens!")

            case Action.GazeVerbal:
                # print current action
                print("GazeVerbal")

                # change initial eye colour
                yield session.call(
                    "rom.actuator.light.write",
                    mode="linear",
                    frames=[{"time": 1, "data": {
                        "body.head.eyes": [173, 216, 230]}}],
                )

                # try and find a face
                yield session.call("rie.vision.face.find")

                # change eye colour after face found
                session.call(
                    "rom.actuator.light.write",
                    mode="linear",
                    frames=[{"time": 1, "data": {
                        "body.head.eyes": [255, 105, 180]}}],
                )

                # make robot look up
                # session.call(
                #     "rom.actuator.motor.write",
                #     frames=[
                #         {"time": 400, "data": {"body.head.pitch": 0.1}},
                #     ],
                #     force=True,
                # )

                # wave to user
                yield session.call(
                    "rom.optional.behavior.play", name="BlocklyWaveRightArm"
                )

                # ask user to ask a question
                yield self._speak(session, "Stel mij een vraag!")

                # wait for user to ask a question
                has_input = yield self._wait_for_user_input_timeout(session)
                if not has_input:
                    return

                # start conversation with user
                yield self._conversate(session)

                # say goodbye to user
                yield self._speak(session, "Tot ziens!")

    @inlineCallbacks
    def _setup(self, session: Session) -> None:
        # change language to nl
        yield session.call("rie.dialogue.config.language", lang="nl")
        # change talking speed
        yield session.call("rie.dialogue.config.speed", speed="100")

        # subscribe to and call stt stream
        yield session.subscribe(self._on_stt_result, "rie.dialogue.stt.stream")
        yield session.call("rie.dialogue.stt.stream")

    @inlineCallbacks
    def _loop(self, session: Session, details: SessionDetails) -> None:
        yield self._setup(session)

        while self.current_action != Action.Quit:
            # make robot stand by default
            yield session.call("rom.optional.behavior.play", name="BlocklyStand")

            # execute current action
            yield self._execute(session, self.current_action)
            yield sleep(.5)

        # leave session
        yield session.leave()
