from typing import List, Union, Dict, Tuple
import re
import os
import yaml
from pathlib import Path
from configparser import ConfigParser
from functools import partial
from subprocess import Popen, PIPE
import sass


def print_w_prefix(msg: str, prefix: str = "") -> None:
    print(f"{prefix}{msg}")


print_ = print_w_prefix
print_1 = partial(print_w_prefix, prefix="\t")
print_2 = partial(print_w_prefix, prefix="\t\t")


def extract_metadata(filename: str) -> Dict:
    with open(filename) as f:
        doc = yaml.load_all(f, Loader=yaml.FullLoader)
        yaml_metadata = doc.__next__()
    if "date" in yaml_metadata:
        yaml_metadata["date"] = str(yaml_metadata["date"])
    return yaml_metadata


def find_bibliographies(bib_files: Union[str, List[str]], bib_dirs: List[str]) -> List[str]:
    retval = []
    if isinstance(bib_files, str):
        bib_files = [bib_files]
    for d in bib_dirs:
        for b in bib_files:
            if os.path.exists(os.path.join(d, b)):
                retval.append(os.path.join(d, b))
    return retval


def replace_metadata(post: str, metadata: str) -> str:
    return re.sub(r'---[\S\n ]+---', f'---\n{yaml.dump(metadata)}---', post)


def shell_command_to_string(cmd: str) -> Tuple[str, str]:
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    return out.decode("utf-8"), err.decode("utf-8")

# def check_files_data(input_dir: Path, files_data_file: Path, files_data_hash: str) -> str:
#     hash = ""
#     def new_files_not_drafts(input_dir):
#         return False
#     def changed_files(input_dir):
#         return False
#     if files_data_file.exists():
#         with open(files_data_file) as f:
#             hash = hashlib.md5(f.read().encode("utf-8")).hexdigest()
#         if files_data_hash and files_data_hash == hash:
#             # print("\tNo files have changed")
#             return ""
#     else:
#         # print("\tNo files data found.")
#         pass
#     return hash


def update_config_file(config: ConfigParser, keys: str, values: str,
                       config_file: Path) -> None:
    for k, v in zip(keys, values):
        config["default"][k] = v
    with open(config_file, "w") as f:
        config.write(f)


def compile_sass(assets_dir: Path) -> None:
    cur_dir = Path(os.curdir).absolute()
    css_dir = assets_dir.joinpath("css").absolute()
    scss_dir = assets_dir.joinpath("css", "scss").absolute()
    if scss_dir.exists() and scss_dir.is_dir():
        in_file = scss_dir.joinpath("main.scss")
        if in_file.exists():
            print(f"Compiling {in_file}")
            out_file = css_dir.joinpath("main.css")
            os.chdir(scss_dir)
            with open(in_file) as f:
                temp: str = sass.compile(string=f.read())
            with open(out_file, "w") as f:
                f.write(temp)
        else:
            print(f"main.scss not in {scss_dir}")
    else:
        print(f"No Sass to compile")
    os.chdir(cur_dir)
