import os
import yaml
import json
import shutil
import hashlib
from subprocess import Popen, PIPE
from bs4 import BeautifulSoup
from types import SimpleNamespace


def snippet_string(snippet, path, date, tags=None):
    return f"""
<div class="main parent content snippet">
    <span><a href="{path}">
            <h4>{snippet.heading}</h4>
            {snippet.text}...
          </a>
    </span>
<p></p></br>
<p>Posted on: {date}""" + (f", tags: {tags}</p></div>" if tags else "</p></div>")


def snippet_string_with_category(snippet, path, date, category, tags=None, cat_path_prefix=""):
    return f"""
<div class="main parent content snippet">
    <span><a href="{path}">
            <h4>{snippet.heading}</h4>
            {snippet.text}...
          </a>
    </span>
<p></p></br>
<p>Posted on: {date}, in Category: <a href="{cat_path_prefix}{category}.html">{category}</a>""" +\
        (f", tags: {tags}</p></div>" if tags else "</p></div>")

class BlogGenerator:
    def __init__(self):
        self.output_dir = "blog_output"
        self.assets_dir = "settings/blog/assets"
        self.exclude_dirs = ["assets", "images", "documents", "tags"]
        self.input_dir = "blog_input"
        self.files_data = os.path.join(self.input_dir, ".files_data")
        self.tag_pages_dir = os.path.join(self.output_dir, "tags")
        self._snippet_cache = {}
        self.sanity_check()
        self.run_pipeline()

    def run_pipeline(self):
        self.check_for_changes()
        self.update_category_and_post_pages()
        if self.index_data:     # only if updates needed
            self.generate_index_page(self.index_data)
        self.generate_tag_pages()
        self.generate_other_pages()
        # preview and push?

    # NOTE:
    # The blog post processor should
    # 1. create blog_output directory if it doesn't exist
    # 2. create the folder structure
    #    - Copy assets folder (DONE)
    #    - Generate research, programming, other_blog, links, about_me folders as required
    #      Get info from file metadata (DONE)
    #      DONE: Should I do it for all files again and again or
    #      should I check for changes from last time?
    #    - update index.html DONE
    #    - CHECK: Add any new generated html files (with folder if required which has
    #      images/docs etc.)
    # NOTE: I think filter by single tag can be done statically,
    #       but filter by multiple tag has to be JS
    def sanity_check(self):
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        shutil.copytree(self.assets_dir,
                        os.path.join(self.output_dir, self.assets_dir.split("/")[-1]),
                        dirs_exist_ok=True)

    def extract_metadata(self, filename):
        with open(filename) as f:
            doc = yaml.load_all(f, Loader=yaml.FullLoader)
            yaml_metadata = doc.__next__()
        return yaml_metadata

    def check_for_changes(self):
        if os.path.exists(self.files_data):
            with open(self.files_data) as f:
                files_data = json.load(f)
        else:
            files_data = {"files": {}}
        files = os.listdir(self.input_dir)
        for f in files:
            if f.endswith(".md"):
                if f not in files_data["files"]:
                    files_data["files"][f] = {}
                    with open(os.path.join(self.input_dir, f)) as _f:
                        hash = hashlib.md5(_f.read().encode("utf-8")).hexdigest()
                    files_data["files"][f]["hash"] = hash
                    files_data["files"][f]["metadata"] = self.extract_metadata(
                        os.path.join(self.input_dir, f))
                    files_data["files"][f]["update"] = True
                else:
                    with open(os.path.join(self.input_dir, f)) as _f:
                        hash = hashlib.md5(_f.read().encode("utf-8")).hexdigest()
                    if not hash == files_data["files"][f]["hash"]:
                        files_data["files"][f]["hash"] = hash
                        files_data["files"][f]["metadata"] = self.extract_metadata(
                            os.path.join(self.input_dir, f))
                        files_data["files"][f]["update"] = True
                    else:
                        files_data["files"][f]["update"] = False
        with open(self.files_data, "w") as dump_file:
            json.dump(files_data, dump_file, default=str)
        self.files_data = files_data

    def generate_post_page(self, post_file):
        p = Popen(f"/usr/bin/pandoc -r markdown+simple_tables+table_captions+yaml_metadata_block+raw_html --toc -t html -F pandoc-citeproc --csl=settings/csl/ieee.csl  --template=settings/blog/post.template -V layout_dir=settings/blog  {post_file}", shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        return page

    # TODO: code formatting for programming stuff
    def generate_posts(self):
        for fname, fval in self.files_data["files"].items():
            if fval["update"] and "category" in fval["metadata"]:
                print(f"Generating post {fname}")
                page = self.generate_post_page(os.path.join(self.input_dir, fname))
                with open(os.path.join(self.output_dir, fval["metadata"]["category"].lower(),
                                       fname.replace(".md", ".html")), "w") as f:
                    f.write(page)

    def update_category_and_post_pages(self):
        categories = {}
        for fname, fval in self.files_data["files"].items():
            meta = fval["metadata"]
            if "category" in meta and meta["category"] not in categories:  # avoid root pages
                categories[meta["category"]] = []
                categories[meta["category"]].append(fname)
        self.categories = [*categories.keys()]
        for cat, pages in categories.items():
            if not os.path.exists(os.path.join(self.output_dir, cat)):
                os.mkdir(os.path.join(self.output_dir, cat))
            pages.sort(key=lambda x: self.files_data["files"][x]["metadata"]["date"],
                       reverse=True)
        self.generate_posts()
        index_data = []
        for cat, pages in categories.items():
            # - filter by tags may only work with javascript
            # - page.insert snippet with a <next> for let's say 5-6 results per page
            # if noscript then show everything (no <next> tags)
            data = []
            for i, page in enumerate(pages):
                temp = {}
                temp["date"] = self.files_data["files"][page]["metadata"]["date"]
                tags = self.files_data["files"][page]["metadata"]["tags"]
                tags = [t.strip() for t in tags.split(",")]
                temp["tags"] = [t.replace(" ", "_") for t in tags]
                html_file = os.path.join(self.output_dir, cat, page.replace(".md", ".html"))
                temp["snippet"] = self.get_snippet_content(html_file)
                temp["path"] = "/".join([cat, page.replace(".md", ".html")])
                data.append(temp)
                if not i:
                    index_data.append({**temp, "category": cat})
            print(f"Generating category {cat} page")
            self.generate_category_page(cat, data)
        self.index_data = index_data

    def get_snippet_content(self, html_file):
        if html_file not in self._snippet_cache:
            with open(html_file) as f:
                soup = BeautifulSoup(f.read(), features="lxml")
            heading = soup.find("h1").text
            paras = soup.findAll("p")
            text = []
            while len(text) <= 70:
                para = paras.pop(0)
                text.extend(para.text.split(" "))
            self._snippet_cache[html_file] = SimpleNamespace(**{"heading": heading, "text": " ".join(text)})
        return self._snippet_cache[html_file]

    # NOTE: modify this to change index menu, rest should be similar
    def menu_string(self, categories, path_prefix=""):
        menu = []
        for cat in categories:
            menu.append(f"<li><a href='{path_prefix}{cat}.html'>{cat.capitalize()}</a></li>")
        menu.extend([f"<li><a href='{path_prefix}links.html'>Links</a></li>",
                     f"<li><a href='{path_prefix}about.html'>About</a></li>"])
        # Home by default shows most recent one snippet from each category
        menu.insert(0, f"<li><a href='{path_prefix}index.html'>Home</a></li>")
        menu.insert(0, "<ul>")
        menu.append("</ul>")
        return "".join(menu)

    # TODO: This should be done with pypandoc maybe
    #       so let's leave it here for now
    def generate_index_page(self, data):
        p = Popen("/usr/bin/pandoc -r markdown+simple_tables+table_captions+yaml_metadata_block+raw_html -t html -F pandoc-citeproc --csl=settings/csl/ieee.csl  --template=settings/blog/index.template -V layout_dir=settings/blog  blog_input/index.md", shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        if err:
            print(err)
        menu_string = self.menu_string(self.categories)
        page = page.replace("$INDEX_TOC$", menu_string)
        index_path = os.path.join("blog_output", "index.html")
        snippets = []
        for d in data:
            date = d["date"]
            tags = d["tags"]
            tags = ", ".join([f"<a href='tags/{tag}.html'>{tag}</a>" for tag in tags])
            path = d["path"]
            snippet = d["snippet"]
            category = d["category"]
            snippets.append(snippet_string_with_category(snippet, path, date, category, tags))
        page = page.replace("$SNIPPETS$", "\n".join(snippets))
        with open(index_path, "w") as f:
            f.write(page)

    # TODO: JS 5-6 snippets at a time with <next> etc.
    def generate_category_page(self, category, data):
        p = Popen(f"/usr/bin/pandoc -r markdown+simple_tables+table_captions+yaml_metadata_block+raw_html -t html -F pandoc-citeproc --csl=settings/csl/ieee.csl  --template=settings/blog/index.template -V layout_dir=settings/blog  blog_input/{category}.md", shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        if err:
            print(err)
        # CHECK: Should category menu string differ from index menu string?
        menu_string = self.menu_string(self.categories)
        page = page.replace("$INDEX_TOC$", menu_string)
        snippets = []
        for d in data:
            date = d["date"]
            tags = d["tags"]
            tags = ", ".join([f"<a href='tags/{tag}.html'>{tag}</a>" for tag in tags])
            path = d["path"]
            snippet = d["snippet"]
            snippets.append(snippet_string(snippet, path, date, tags))
        page = page.replace("$SNIPPETS$", "\n".join(snippets))
        with open(os.path.join(self.output_dir, f"{category}.html"), "w") as f:
            f.write(page)

    def generate_tag_pages(self):
        p = Popen(f"/usr/bin/pandoc -r markdown+simple_tables+table_captions+yaml_metadata_block+raw_html -t html -F pandoc-citeproc --csl=settings/csl/ieee.csl  --template=settings/blog/index.template -V layout_dir=settings/blog  blog_input/tag.md", shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        page = out.decode("utf-8")
        if err:
            print(err)
        # CHECK: Should category menu string differ from index menu string?
        menu_string = self.menu_string(self.categories, "../")
        page = page.replace("$INDEX_TOC$", menu_string)
        page = page.replace("href=\"assets/", "href=\"../assets/")
        page = page.replace("src=\"assets/", "src=\"../assets/")
        all_tags = {}
        for fname, fval in self.files_data["files"].items():
            if "category" in fval["metadata"]:  # only posts
                tags = fval["metadata"]["tags"]
                tags = [t.strip().replace(" ", "_") for t in tags.split(",")]
                for tag in tags:
                    if tag not in all_tags:
                        all_tags[tag] = []
                    all_tags[tag].append([fname, fval["metadata"]["category"],
                                          fval["metadata"]["date"]])
        if not os.path.exists(self.tag_pages_dir):
            os.mkdir(self.tag_pages_dir)
        for tag, files in all_tags.items():
            tag_page = page.replace("$TAG$", tag)
            snippets = []
            for fname, category, date in files:
                _fname = fname.replace(".md", ".html")
                snippet = self.get_snippet_content(os.path.join(
                    self.output_dir, category, fname.replace(".md", ".html")))
                path = f"../{category}/{_fname}"
                snippets.append(snippet_string_with_category(snippet, path, date, category,
                                                             cat_path_prefix="../"))
            tag_page = tag_page.replace("$SNIPPETS$", "\n".join(snippets))
            with open(os.path.join(self.tag_pages_dir, f"{tag}.html"), "w") as f:
                f.write(tag_page)

    def generate_other_pages(self):
        self.generate_about_page()
        self.generate_links_page()
        self.generate_quotes_page()

    def generate_about_page(self):
        pass

    def generate_links_page(self):
        pass

    def generate_quotes_page(self):
        pass


# NOTE: Initialize and export the function
post_processor = BlogGenerator()


# if __name__ == "__main__":
#     post_processor([])
