from robot import Robot
from gui import Gui


class RobotController:
    def __init__(self, stt_certainty_threshold: float, max_wamp_retries: int = 0):
        self.robot = Robot(stt_certainty_threshold, max_wamp_retries)
        self.gui = Gui(self.robot)

    def start(self):
        self.robot.start()
        self.gui.start()