from robot import Robot
from gui import Gui
from config import Config


class RobotController:
    def __init__(self, config: Config, stt_certainty_threshold: float, max_wamp_retries: int = 0):
        self.robot = Robot(config, stt_certainty_threshold, max_wamp_retries)
        self.gui = Gui(self.robot)

    def start(self):
        self.robot.start()
        self.gui.start()
