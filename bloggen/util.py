from typing import Any, List, Union
import re
import os
import yaml


def title_file_string(titles: str) -> str:
    "Return string which will be used to generate titles from json"
    return f"""const titles = {titles};
const index = Math.floor(Math.random() * titles.length);
const title = titles[index];
document.title = title;
document.getElementById("header").children[0].textContent = title;"""


def snippet_string(snippet: Any, path: str, date: str,
                   tags: List[str] = None) -> str:
    "Return string which will be used to generate snippets"
    return f"""
<div class="main parent content snippet">
    <span><a href="{path}">
            <h4>{snippet.heading}</h4>
            {snippet.text}...
          </a>
    </span>
<p></p><br>
<p>Posted on: {date}""" + (f", tags: {tags}</p></div>" if tags else "</p></div>")


def snippet_string_with_category(snippet: Any, path: str, date: str,
                                 category: str, tags: List[str] = None,
                                 cat_path_prefix: str = "") -> str:
    """Return string which will be used to generate snippets with categories beneath it.
    Used for posts"""
    return f"""
<div class="main parent content snippet">
    <span><a href="{path}">
            <h4>{snippet.heading}</h4>
            {snippet.text}...
          </a>
    </span>
<p></p><br>
<p>Posted on: {date}, in Category: <a href="{cat_path_prefix}{category}.html">{category}</a>""" +\
        (f", tags: {tags}</p></div>" if tags else "</p></div>")


def extract_metadata(filename):
    with open(filename) as f:
        doc = yaml.load_all(f, Loader=yaml.FullLoader)
        yaml_metadata = doc.__next__()
    if "date" in yaml_metadata:
        yaml_metadata["date"] = str(yaml_metadata["date"])
    return yaml_metadata


def find_bibliographies(bib_files: Union[str, List[str]], bib_dirs: List[str]):
    retval = []
    if isinstance(bib_files, str):
        bib_files = [bib_files]
    for d in bib_dirs:
        for b in bib_files:
            if os.path.exists(os.path.join(d, b)):
                retval.append(os.path.join(d, b))
    return retval


def replace_metadata(post, metadata):
    return re.sub(r'---[\S\n ]+---', f'---\n{yaml.dump(metadata)}---', post)
