from autobahn.twisted.util import sleep
from autobahn.wamp.types import SessionDetails
from autobahn.twisted.wamp import Session
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.component import Component, run as run_component
import time
import os

from src.action import Action
from src.ai import Ai, AiResponse
from src.gui import Gui


class RobotController:
    def __init__(self, stt_certainty_threshold: float, max_wamp_retries: int = 0):
        self.robot = Robot(stt_certainty_threshold, max_wamp_retries)
        self.gui = Gui(self.robot)

    def start(self):
        self.robot.start()
        self.gui.start()

class Robot:
    def __init__(self, stt_certainty_threshold: float, max_wamp_retries: int = 0) -> None:
        self.ai = Ai()
        self.ai_response = AiResponse()
        
        self.current_action = Action.Idle

        self.stt_certainty_threshold = stt_certainty_threshold
        
        self.in_conversation = False
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

    def _on_stt_result(self, frame: dict):
        user_input: str = frame["data"]["body"]["text"]
        is_final: bool = frame["data"]["body"]["final"]
        stt_certainty: float = frame["data"]["body"]["certainty"]

        if not is_final: return
        
        if stt_certainty < self.stt_certainty_threshold:
            self.unclear_user_input = True
            return
        
        if not user_input.strip(): return

        if (response := self.ai.conversate(user_input)) is None:
            self.ai_response.failed = True
            return
        
        self.ai_response.text = response
        self.ai_response.responded = True

        print(f"user: {user_input}")
        print(f"ai: {self.ai_response.text}")


    @inlineCallbacks
    def _wait_for_user_input_timeout(
        self, session: Session, max_wait_time_sec: float = 30.0
    ) -> bool:
        # subscribe to and call stt stream
        yield session.subscribe(self._on_stt_result, "rie.dialogue.stt.stream")
        yield session.call("rie.dialogue.stt.stream")

        max_end_time_sec = time.time() + max_wait_time_sec

        # wait for user input
        while max_end_time_sec >= time.time():
            if self.in_conversation:
                return True
            
            yield sleep(.5)

        # close stt stream
        yield session.call("rie.dialogue.stt.close")
        
        return False
    
    @inlineCallbacks
    def _conversate(self, session: Session, max_wait_time_sec: float = 30) -> None:
        max_end_time_sec = time.time() + max_wait_time_sec
        
        while self.in_conversation and max_end_time_sec >= time.time():
            # ask user to repeat if input was unclear
            if self.unclear_user_input:
                # reset unclear_user_input flag
                self.unclear_user_input = False 
                
                yield session.call(
                    "rie.dialogue.say", text="Kun je dat herhalen?"
                )
                continue
            
            # stop if ai failed
            if self.ai_response.failed:
                yield session.call(
                    "rie.dialogue.say", text="Er is iets misgegaan, sorry!"
                )
                break
            
            # still waiting for reply from ai
            if not self.ai_response.responded:
                yield sleep(.1)
                continue
            
            # make sure stt stream is closed before robot speaks
            yield session.call("rie.dialogue.stt.close")
            
            # robot speaks
            yield session.call("rie.dialogue.say", text=self.ai_response.text)
            
            # reset ai response before opening stt stream again
            self.ai_response.reset()
            
            # subscribe to and call stt stream again
            yield session.subscribe(self._on_stt_result, "rie.dialogue.stt.stream")
            yield session.call("rie.dialogue.stt.stream")

        
        # make sure stt stream is closed
        yield session.call("rie.dialogue.stt.close")
        
        # reset flags
        self.in_conversation = False
        self.unclear_user_input = False
        
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
                        frames=[{"time": 1, "data": {"body.head.eyes": [173, 216, 230]}}],
                    )
                    
                    # find face
                    yield session.call("rie.vision.face.find")
                    
                    # change eye colour to purple after face found
                    yield session.call(
                        "rom.actuator.light.write",
                        mode="linear",
                        frames=[{"time": 1, "data": {"body.head.eyes": [173, 216, 230]}}],
                    )
                    # track face
                    yield session.call("rie.vision.face.track")
                    
                    # wave right arm
                    session.call("rom.optional.behavior.play", name="BlocklyWaveRightArm")
                case Action.Verbal:
                    print("Verbal")

                    # change initial eye colour
                    yield session.call(
                        "rom.actuator.light.write",
                        mode="linear",
                        frames=[{"time": 1, "data": {"body.head.eyes": [173, 216, 230]}}],
                    )
                        # Enter default text
                    yield session.call(
                        "rie.dialogue.say", text="Hallo, wat heb jij een mooie uitstraling!"
                    )

                    # ask user to ask a question
                    yield session.call(
                        "rie.dialogue.say", text="Stel mij een vraag!"
                    )

                    # wait for user to ask a question
                    if not self._wait_for_initial_user_input(): return
                    
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
                        frames=[{"time": 1, "data": {"body.head.eyes": [173, 216, 230]}}],
                    )

                    # try and find a face
                    yield session.call("rie.vision.face.find")

                    # change eye colour after face found
                    yield session.call(
                        "rom.actuator.light.write",
                        mode="linear",
                        frames=[{"time": 1, "data": {"body.head.eyes": [255, 105, 180]}}],
                    )

                    # make robot look up
                    yield session.call(
                        "rom.actuator.motor.write",
                        frames=[
                            {"time": 400, "data": {"body.head.pitch": 0.1}},
                        ],
                        force=True,
                    )

                    # wave to user
                    yield session.call(
                        "rom.optional.behavior.play", name="BlocklyWaveRightArm"
                    )

                    # ask user to ask a question
                    yield session.call("rie.dialogue.say", text="Stel mij een vraag!")

                    # wait for user to ask a question
                    if not self._wait_for_initial_user_input(): return
                    
                    # start conversation with user
                    yield self._conversate(session)

                    # say goodbye to user
                    yield session.call("rie.dialogue.say", text="Tot ziens!")

                    # # track face while in vision
                    # yield session.call("rie.vision.face.track")

                    # # listen to face stream
                    # yield session.subscribe(self.__on_face, "rie.vision.face.stream")
                    # yield session.call("rie.vision.face.stream")

    @inlineCallbacks
    @staticmethod
    def _setup(session: Session) -> None:
        # change language to nl
        yield session.call("rie.dialogue.config.language", lang="nl")
        # change talking speed
        yield session.call("rie.dialogue.config.speed", speed="100")
    
    @inlineCallbacks
    def _loop(self, session: Session, details: SessionDetails) -> None:
        self._setup(session)

        while self.current_action != Action.Quit:
            # make robot stand by default
            yield session.call("rom.optional.behavior.play", name="BlocklyStand")
            
            # execute current action
            yield self._execute(session, self.current_action)
            yield sleep(.5)

        # leave session
        yield session.leave()
