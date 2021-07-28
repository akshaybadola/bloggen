from typing import Any, List, Dict
from datetime import datetime


def title_file_string(titles: List[str]) -> str:
    "Return string which will be used to generate titles from json"
    return "function change_title(){" + f"""
  const titles = {titles};
  const index = Math.floor(Math.random() * titles.length);
  const title = titles[index];
  document.title = title;
  document.getElementById("header").children[0].textContent = title;
""" + "}"


def about_string(abouts: List[str]) -> str:
    "Return string which will be used to generate titles from json"
    return "function change_about(){" + f"""
  const abouts = {abouts};
  const index = Math.floor(Math.random() * abouts.length);
  const about = abouts[index];
  const element = (document.querySelector("body > div.wrapper > div.about > header > div.author-description")
    || document.querySelector("body > div.about.shadow > header > div.author-description")).textContent = about;
""" + "}"


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
<p>Posted on: {date}, in Category: <a class="category" href="{cat_path_prefix}{category}.html">{category}</a>""" +\
        (f", tags: {tags}</p></div>" if tags else "</p></div>")


def article_snippet_with_category(snippet: Any, path: str, date: str,
                                  category: str, tags: List[str] = None,
                                  cat_path_prefix: str = "") -> str:
    """Return string which will be used to generate snippets with categories beneath it.
    Used for posts"""
    return f"""
<article class="post">
    <span><a href="{path}">
            <h4>{snippet.heading}</h4>
            {snippet.text}...
          </a>
    </span>
<p></p><br>
<p>Posted on: {date}, in Category: <a class="category" href="{cat_path_prefix}{category}.html">{category}</a>""" +\
        (f", tags: {tags}</p></article>" if tags else "</p></article>")


def about_snippet(about_path: str, img_path: str, name: str,
                  about_str: str, contact: Dict[str, str]):
    header = f"""
<header>
  <div class="cover-author-image">
    <a href="{str(about_path)}"><img src="{str(img_path)}" alt="{name}"></a>
  </div>
  <div class="author-name">{name}</div>
  <div class="author-description">{about_str}</div>
</header> <!-- End Header -->"""
    footer = """
<footer>
  <section class="contact">
    <h4 class="contact-title">Contact me</h4>
    <ul>"""
    for k, v in contact.items():
        if k == "twitter":
            footer += f"""
      <li>
        <a href="https://twitter.com/{v}" target="_blank">
          <i class="fa fa-twitter" aria-hidden="true"></i>
        </a>
      </li>"""
        elif k == "facebook":
            footer += f"""
      <li>
        <a href="https://facebook.com/{v}" target="_blank">
          <i class="fa fa-facebook" aria-hidden="true"></i>
        </a>
      </li>"""
        elif k == "github":
            footer += f"""
      <li class="github">
        <a href="https://github.com/{v}" target="_blank">
          <i class="fa fa-github"></i>
        </a>
      </li>"""
        elif k == "linkedin":
            footer += f"""
      <li class="linkedin">
        <a href="https://linkedin.com/in/{v}" target="_blank">
          <i class="fa fa-linkedin"></i>
        </a>
      </li>"""
        elif k in {"email", "mail", "gmail"}:
            footer += f"""
      <li class="email">
        <a href="mailto:{v}">
          <i class="fa fa-envelope-o"></i>
        </a>
      </li>"""
    footer += f"""
    </ul>
  </section> <!-- End Section Contact -->
  <div class="copyright">
  <p>{datetime.now().year} &copy; {name}</p>
  </div>
</footer> <!-- End Footer -->"""
    return header + footer
