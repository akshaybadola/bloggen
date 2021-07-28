from typing import List, Union, Dict
import os
import re
import json
import hashlib
import datetime
from pathlib import Path

from .util import print_1, extract_metadata


def check_metadata_for(metadata, prop):
    if prop in metadata:
        return metadata[prop]
    else:
        return False


class Files:
    def __init__(self, input_dir: Path, output_dir: Path,
                 files_data_file: Path, update_all: bool):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.files_data_file = files_data_file
        self.update_all = update_all
        self.load_files_data()
        self.deleted_files: List[str] = []
        self.new_files: List[str] = []
        self.changed_files: List[str] = []

    def generation_files(self, include_drafts):
        if include_drafts:
            return self.files_data['files']
        else:
            return {k: v for k, v in self.files_data['files'].items()
                    if not (v["metadata"].get("ignore", "") or
                            v["metadata"].get("draft", ""))}

    @property
    def changes(self) -> List[str]:
        return [*self.new_files, *self.changed_files, *self.deleted_files]

    def load_files_data(self):
        if os.path.exists(self.files_data_file):
            with open(self.files_data_file) as f:
                self.files_data = json.load(f)
        else:
            print_1(f"No previous files data found. Will update all files")
            self.files_data = {"files": {}}
        if self.update_all:
            print_1(f"Force updating all files")
            self.files_data = {"files": {}}
        self.in_files: List[str] = os.listdir(self.input_dir)

    def check_for_changes(self, include_drafts: bool = False,
                          input_pattern: str = ""):
        self.remove_deleted_files_from_files_data()
        self.update_files_data(include_drafts, input_pattern)

    def remove_deleted_files_from_files_data(self):
        indexed_files = self.files_data["files"].keys()
        diff = set(indexed_files) - set(self.in_files)
        for fname in diff:
            self.deleted_files.append(fname)
            self.files_data["files"].pop(fname)

    def get_hash_and_metadata(self, fname):
        with open(os.path.join(self.input_dir, fname)) as f:
            hash = hashlib.md5(f.read().encode("utf-8")).hexdigest()
        self.files_data["files"][fname]["metadata"] = extract_metadata(
            os.path.join(self.input_dir, fname))
        metadata = self.files_data["files"][fname]["metadata"]
        return hash, metadata

    def change_category_to_lowercase(self, fname: str, metadata: Dict):
        if "category" in metadata:
            self.files_data["files"][fname]["metadata"]["category"] =\
                metadata["category"].lower()

    def replace_space_to_dash_in_category(self, fname: str, metadata: Dict):
        if "category" in metadata:
            self.files_data["files"][fname]["metadata"]["category"] =\
                metadata["category"].replace(" ", "-")

    def only_update_if_matching_pattern(self, fname, input_pattern):
        if fname in self.files_data["files"]:
            if re.match(input_pattern, fname, flags=re.IGNORECASE):
                self.files_data["files"][fname]["update"] = True
            else:
                self.files_data["files"][fname]["update"] = False

    def maybe_mark_for_update(self, fname, metadata, hash):
        if check_metadata_for(metadata, "ignore"):
            return False
        elif check_metadata_for(metadata, "draft"):
            print_1(f"Draft {fname} will not be published.")
            return False
        else:
            if self.files_data["files"][fname].get("hash", "") != hash:
                self.files_data["files"][fname]["hash"] = hash
                self.files_data["files"][fname]["update"] = True
                return True

    def mark_for_update_maybe_add_drafts_to_tags(self, fname, metadata):
        if "tags" in metadata and (check_metadata_for(metadata, "ignore") or
                                   check_metadata_for(metadata, "draft")):
            metadata["tags"] = ",".join([*metadata["tags"].split(","), "drafts"])
            self.files_data["files"][fname]["update"] = True
            # self.files_data["files"][fname]["tags"] = ",".join([*tags, "drafts"])
            return True
        else:
            return False

    def mark_update_if_index_or_no_out_file(self, fname: str, metadata):
        if not (check_metadata_for(metadata, "ignore") or
                check_metadata_for(metadata, "draft")):
            if "category" in metadata:
                out_file = os.path.join(self.output_dir, metadata["category"],
                                        fname.replace(".md", ".html"))
                if not os.path.exists(out_file):
                    self.files_data["files"][fname]["update"] = True
            else:
                self.files_data["files"][fname]["update"] = True

    def maybe_mark_file_for_update(self, fname, hash, metadata, include_drafts):
        self.files_data["files"][fname]["metadata"] = metadata
        self.change_category_to_lowercase(fname, metadata)
        self.replace_space_to_dash_in_category(fname, metadata)
        maybe_draft = self.mark_for_update_maybe_add_drafts_to_tags(fname, metadata)\
            if include_drafts else False
        if maybe_draft:
            return True
        else:
            return self.maybe_mark_for_update(fname, metadata, hash)

    def mark_new_file_for_update(self, fname, include_drafts):
        self.files_data["files"][fname] = {}
        hash, metadata = self.get_hash_and_metadata(fname)
        if self.maybe_mark_file_for_update(fname, hash, metadata, include_drafts):
            self.new_files.append(fname)
        return metadata

    def mark_existing_file_for_update(self, fname, include_drafts):
        self.files_data["files"][fname]["update"] = False
        hash, metadata = self.get_hash_and_metadata(fname)
        if self.maybe_mark_file_for_update(fname, hash, metadata, include_drafts):
            self.changed_files.append(fname)
        return metadata

    def update_files_data(self, include_drafts, input_pattern):
        files = [fname for fname in self.in_files if fname.endswith(".md")]
        for fname in files:
            if fname not in self.files_data["files"]:
                metadata = self.mark_new_file_for_update(fname, include_drafts)
            else:
                metadata = self.mark_existing_file_for_update(fname, include_drafts)
            if input_pattern:
                self.only_update_if_matching_pattern(fname, input_pattern)
            self.mark_update_if_index_or_no_out_file(fname, metadata)

    def write_files_data(self):
        def defaults(o):
            if isinstance(o, datetime.date):
                return str(o)
            else:
                return o
        serialized = json.dumps(self.files_data, default=defaults)
        with open(self.files_data_file, "w") as f:
            f.write(serialized)
