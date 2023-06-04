from robotcontroller import RobotController
import config
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env.keys")


if __name__ == "__main__":
    cfg = config.load(Path("config.yml"))

    robot_controller = RobotController(cfg, stt_certainty_threshold=0.7)

    robot_controller.start()
