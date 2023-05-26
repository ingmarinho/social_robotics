from src.robot import RobotController

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    robot_controller = RobotController(stt_certainty_threshold=0.7)

    robot_controller.start()
