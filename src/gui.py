from tkinter import *
from twisted.internet import tksupport
from twisted.internet import reactor

from robot import Robot
from action import Action


class Gui:
    def __init__(self, robot: Robot) -> None:
        self.robot = robot

        root = Tk()

        # for twisted compatibility
        tksupport.install(root)
        
        # for closing the window
        root.protocol("WM_DELETE_WINDOW", self.quit)

        # set window title
        root.title("Robot Control Panel")
        
        # set window background color
        root.configure(background="white")

        # set window size
        root.geometry("900x160")

        button_frame = Frame(root, bg="white")
        button_frame.pack(pady=20)

        button_width = 12
        button_height = 4
        button_fg_color = "white"
        button_font = ("Arial", 14)
        borderwidth = 5

        actions = [
            ("Idle", Action.Idle, "#000000"),
            ("Gaze", Action.Gaze, "#ff0000"),
            ("Verbal", Action.Verbal, "#0000ff"),
            ("GazeVerbal", Action.GazeVerbal, "#008000"),
            ("Quit", Action.Quit, "#ff8000"),
        ]
        
        # create buttons
        for i, (text, action, bg_color) in enumerate(actions):
            button = Button(
                button_frame,
                text=text,
                command=lambda action=action: self.robot.set_action(action),
                width=button_width,
                height=button_height,
                bg=bg_color,
                fg=button_fg_color,
                font=button_font,
                borderwidth=borderwidth,
            )
            button.grid(row=0, column=i, padx=10, pady=10)

    @staticmethod
    def start() -> None:
        reactor.run()

    def quit(self) -> None:
        self.robot.set_action(Action.Quit)
        reactor.stop()
