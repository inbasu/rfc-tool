#!/usr/bin/env python3

import json
import os
import re
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
from urllib.request import urlretrieve
from urllib.error import HTTPError


RFC_CACHE_DIR = Path.home() / "Documents/.rfc"
RFC_URL = "https://www.rfc-editor.org"
HELP_TEXT = """\
Options:
    -f, --find <query>    Search RFCs by keyword (table format)
    -l, --list            List cached RFCs (table format)
    -c, --clear           Clear cache
    -h, --help            Show this help

Examples:
    rfc 3261              Open RFC 3261 (download if not cached)
    rfc -f sip            Search for RFCs containing "sip"
    rfc -l                Show all cached RFCs
    rfc -c                Clear cache"""


@dataclass
class RFC:
    number: int
    title: str
    file_path: Optional[Path] = None


class FileManager:
    def __init__(self, cache_root_dir: Path) -> None:
        self._root_path = cache_root_dir
        self._root_path.mkdir(exist_ok=True)
        self._titles_json = self._root_path / ".titles.json"

    def get_rfc_file_path(self, rfc: int) -> Path:
        return self._root_path / f"RFC{rfc}.txt"

    def get_cached_rfcs(self) -> list[Path]:
        return list(self._root_path.glob("RFC*.txt"))

    def save_titles_cache(self, titles: dict[str, str]) -> None:
        with open(self._titles_json, "w") as file:
            file.write(json.dumps(titles))

    def load_titles_cache(self) -> dict[str, str]:
        if self._titles_json.exists():
            with open(self._titles_json, "r") as file:
                return json.load(file)
        return {}

    def clear(self) -> None:
        for file in self._root_path.glob("*"):
            file.unlink()

    @property
    def index_file(self) -> Path:
        return self._root_path / "index.txt"


class DownloadManager:
    def __init__(self, url: str, file_manager: FileManager) -> None:
        self._file_manager = file_manager
        self.base_url = url + "/rfc"
        self.index_url = url + "/rfc/rfc-index.txt"

    def download_rfc_txt(self, rfc: int) -> Union[Path, None]:
        """Download RFC file if it not cached"""
        rfc_file = self._file_manager.get_rfc_file_path(rfc)
        if rfc_file.exists():
            return rfc_file
        try:
            print(f"Downloading RFC {rfc}...")
            urlretrieve(f"{self.base_url}/rfc{rfc}.txt", rfc_file)
            return rfc_file
        except HTTPError as e:
            print(f"RFC {rfc} not found.") if e.code == 404 else print("Download error.")
            return None
        except Exception:
            print("Unexpected error.")
            return None

    def download_index_file(self) -> None:
        try:
            print("Downloading index file.")
            urlretrieve(self.index_url, self._file_manager.index_file)
        except Exception:
            print("Failed to download index file.")


class RFCViewService:
    """Класс обрабатывающий основную логику"""

    def __init__(self) -> None:
        self._file_manager = FileManager(RFC_CACHE_DIR)
        self._download_manager = DownloadManager(RFC_URL, self._file_manager)

    def open_rfc_file(self, rfc_id: int) -> None:
        rfc_file = self._download_manager.download_rfc_txt(rfc_id)
        if not rfc_file:
            return
        titles = self._file_manager.load_titles_cache()
        rfc_num = str(rfc_id)
        if rfc_num not in titles:
            title = self._get_title_from_index(rfc_num)
            if title:
                titles[rfc_num] = title
                self._file_manager.save_titles_cache(titles)

        os.system(f"less -R '{rfc_file}'")

    def find_rfc(self, query: str) -> None:
        q = query.lower()
        finded = [rfc for rfc in self._rfc_indexes() if q in rfc.title.lower()]
        if not finded:
            print(f'No RFCs founded matching "{query}"')
            return
        print(f"{'RFC:':<8} {'Title:':<50}")
        for rfc in finded:
            print(f"{rfc.number:<8} {rfc.title}")

    def list_downloaded_rfcs(self) -> None:
        files = self._file_manager.get_cached_rfcs()
        if not files:
            print("No downloaded files.")
            return

        titles = self._file_manager.load_titles_cache()

        print(f"{'RFC:':<8} {'Title:':<50}")
        for file in files:
            rfc_id = file.stem[3:]
            title = titles.get(rfc_id)
            if not title:
                title = self._get_title_from_index(rfc_id)
                title = title if title else "No title"
                title = title if (len(title) <= 50) else title[:47] + "..."
            print(f"{rfc_id:<8} {title}")

    def clear_cache(self, rfcs: Optional[list[int]] = None) -> None:
        if not rfcs:
            self._file_manager.clear()
            print("Downloaded files deleted.")
            return
        deleted: list[str] = []
        for rfc in rfcs:
            file = self._file_manager.get_rfc_file_path(rfc)
            if not file.exists():
                print(f"No RFC-{rfc} file in cache.")
                continue
            file.unlink()
            deleted.append(str(rfc))
        if deleted:
            print(f"RFC{'s: ' if len(deleted) > 1 else ''}{', '.join(deleted)} deleted.")
            return
        print("No one RFC file to delete.")

    def _get_title_from_index(self, rfc_num: str) -> Union[str, None]:
        for rfc in self._rfc_indexes():
            if rfc.number == int(rfc_num):
                return rfc.title
        return None

    def _rfc_indexes(self) -> list[RFC]:
        if not self._file_manager.index_file.exists():
            self._download_manager.download_index_file()

        with open(self._file_manager.index_file, "r", errors="ignore") as file:
            lines = file.readlines()

        result = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if match := re.match(r"^(\d+)\s+(.+)", line):
                rfc_num = int(match.group(1))
                title_parts = [match.group(2)]
                i += 1
                while i < len(lines) and lines[i].startswith("     "):
                    # Собираем многострочник к одну строку
                    title_parts.append(lines[i].strip())
                    i += 1

                title = " ".join(title_parts)
                title = re.split(r"\s+\(Format:|\.\s+[A-Z][a-z]+\.\s+\w+\s+\d{4}", title)[0]
                title = re.sub(r"\s+\(.*$", "", title).split(".")[0]
                result.append(RFC(number=rfc_num, title=title.strip()))
            else:
                i += 1
        return result


def main() -> None:
    parser = ArgumentParser(description="Utility for RFC search and read.", add_help=False)

    parser.add_argument("number", nargs="?", type=int, help="Open RFC manual")
    parser.add_argument("-f", "--find", type=str, help="Find RFCs by keyword")
    parser.add_argument("-l", "--list", action="store_true", help="List cached RFC files")
    parser.add_argument("-c", "--clear", nargs="*", type=int, help="Delete cached RFC")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")

    args = parser.parse_args()
    processor = RFCViewService()

    if args.help or (len(sys.argv) == 1):
        print(HELP_TEXT)
    elif args.find:
        processor.find_rfc(args.find)
    elif args.list:
        processor.list_downloaded_rfcs()
    elif args.clear is not None:
        processor.clear_cache(args.clear if args.clear else None)
    elif args.number:
        processor.open_rfc_file(args.number)
    else:
        print("Invalid arguments. Use 'rfc -h' for help.")


if __name__ == "__main__":
    main()
