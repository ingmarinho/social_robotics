from dataclasses import dataclass
from dacite import from_dict
from pathlib import Path
import yaml


@dataclass
class Config:
    SystemMessage: str
    Compliments: list[str]


def _snake_to_pascal(s: str) -> str:
    return "".join([w.capitalize() for w in s.split("_")])


def load(path: Path) -> Config:
    yaml_dict_converted = {}
    
    with open(path, "r") as f:
        yaml_dict: dict = yaml.safe_load(f)

        for k in yaml_dict.keys():
            yaml_dict_converted[_snake_to_pascal(k)] = yaml_dict[k]

        return from_dict(data_class=Config, data=yaml_dict_converted)
