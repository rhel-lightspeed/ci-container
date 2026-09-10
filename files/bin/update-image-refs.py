#!/usr/bin/env python

import argparse
import dataclasses
import datetime
import json
import re
import sys
import typing as t
import urllib.request
from pathlib import Path


def parse_from_line(line: str) -> tuple[str, ...] | None:
    # Parse a FROM statement into components. This works with simple specifications
    # such as "FROM nginx" up to more complex specifications such as:
    #   FROM registry.access.redhat.com/ubi10-minimal:latest@sha256:d801168f5e8b108586c27a4fd5c92e3c1e8d061084383713926e2ca61b8b6c64
    image_re = re.compile(
        r"^FROM\s+"
        r"(?:(?P<registry>[^/]+)/)?"
        r"(?P<image>[^:@]+)"
        r"(?::(?P<tag>[^@]+?))?"
        r"(?:@(?P<digest>[a-z0-9:]+))?"
        r"(?:(?P<suffix>\s+AS.+))?$"
    )

    if match := image_re.match(line):
        return match.groups()


def fetch_tags(
    registry: str | None,
    image: str,
    start_tag: str,
    limit: int = 100,
) -> list[str]:
    count = 0
    tags = []
    last = start_tag
    while count < limit:
        url = f"https://{registry or 'registry-1.docker.io'}/v2/{image}/tags/list?last={last}"
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        current_tags = data.get("tags", [])
        if not current_tags:
            break

        remaining = limit - count
        tags.extend(current_tags[:remaining])
        count += min(len(current_tags), remaining)
        next_last = current_tags[-1]
        if next_last == last:
            break

        last = next_last

    return tags


def get_digest(registry: str, image: str, tag: str) -> str:
    # Setting the header here is what gives the latest image hash.
    url = f"https://{registry}/v2/{image}/manifests/{tag}"
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.oci.image.index.v1+json"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        digest = response.getheader("Docker-Content-Digest")

    if digest is None:
        raise ValueError(f"Unable to find digest for {registry}/{image}:{tag}.")

    return digest


def extract_version_timestamp(tag: str) -> tuple[str, int]:
    timestamp_re = re.compile(r"(\S+)-(\d{10,})-?")
    if match := timestamp_re.match(tag):
        version, timestamp = match.groups()
        try:
            return version, int(timestamp)
        except ValueError:
            print(f"Error extracting timestamp: {timestamp}")

    return tag, 0


def find_latest_tag(
    current_tag: str, version: str, timestamp: int, tags: list[str]
) -> str:
    current_version = version
    latest_ts = timestamp
    latest_tag = current_tag
    for tag in tags:
        version, ts = extract_version_timestamp(tag)
        if version == current_version and ts > latest_ts:
            latest_ts = ts
            latest_tag = tag

    return latest_tag


def timestamp_to_date(tag: str) -> str | None:
    _, ts = extract_version_timestamp(tag)
    if ts:
        dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)

        return dt.strftime("%Y-%m-%d")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update base images in container files to latest tags"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        type=Path,
        help="Directory to search for container files (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        help="Container file to update",
    )
    parser.add_argument(
        "--image",
        "-i",
        type=str,
        help="Show latest blobs for image",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=100,
        help="Maximum number of items to return when listing image details.",
    )
    parser.add_argument(
        "--digest",
        "-d",
        action="store_true",
        help="Add image digest",
    )
    return parser.parse_args()


@dataclasses.dataclass
class ImageUpdater:
    args: argparse.Namespace
    dry_run: bool = dataclasses.field(init=False)
    total_updates: int = dataclasses.field(init=False, default=0)
    _patterns: t.ClassVar[list[str]] = ["*Containerfile*", "*Dockerfile*"]

    def __post_init__(self):
        self.dry_run = self.args.dry_run

    @property
    def container_files(self):
        if self.args.file:
            return [self.args.file]

        if not self.args.directory.is_dir():
            print(f"Error: {self.args.directory} is not a directory", file=sys.stderr)
            sys.exit(1)

        files = []
        for pattern in self._patterns:
            files.extend(self.args.directory.rglob(pattern))

        return sorted(files)

    def process_file(self, filepath: Path) -> list[tuple[str, str, str]]:
        print(f"Processing {filepath}...")
        updates = []
        lines = filepath.read_text().splitlines()
        new_lines = []
        date_comment_re = re.compile(r"^#\s*\d{4,4}-\d{2,2}-\d{2,2}")
        for line in lines:
            last_output_index = len(new_lines) - 1
            if not (parsed := parse_from_line(line)):
                new_lines.append(line)
                continue

            registry, image, current_tag, digest, suffix = parsed
            if not registry:
                new_lines.append(line)
                continue

            # Image specs do not require a tag. In that case, only continue if the digest was requested
            # and set the current_tag to "latest".
            if current_tag is None and not self.args.digest:
                new_lines.append(line)
                continue

            latest_tag = current_tag or "latest"
            version, timestamp = extract_version_timestamp(latest_tag)
            if timestamp:
                tags = fetch_tags(registry, image, current_tag)
                latest_tag = find_latest_tag(current_tag, version, timestamp, tags)
                new_timestamp = timestamp_to_date(latest_tag)
                timestamp_comment = f"# {new_timestamp}"
                if last_output_index >= 0 and date_comment_re.match(new_lines[last_output_index]):
                    new_lines[last_output_index] = timestamp_comment
                else:
                    new_lines.append(timestamp_comment)

            digest_suffix = ""
            if self.args.digest:
                digest = get_digest(registry, image, latest_tag)
                digest_suffix = f"@{digest}"

            tag_suffix = f":{latest_tag}" if current_tag is not None else ""
            updated_line = f"FROM {registry}/{image}{tag_suffix}{digest_suffix or ''}{suffix or ''}"
            new_lines.append(updated_line)
            if line != updated_line:
                updates.append((f"{registry}/{image}", current_tag, latest_tag))

        if updates and not self.dry_run:
            filepath.write_text("\n".join(new_lines) + "\n")

        return updates

    def update(self):
        if self.args.image:
            # If the tag doesn't have a timestamp, just get the digest. It's a floating tag.
            # If it does have a timestamp, use that as the last value and get the latest tag-timestamp,
            # then get the digest

            # Examples:
            #   registry.access.redhat.com/hi/python:3.12
            #   registry.access.redhat.com/hi/python:3.12-[timestamp]-builder
            #   registry.access.redhat.com/hi/python:3.12-builder
            #   registry.access.redhat.com/ubi10-minimal:10.2-1788137716
            registry_image, _, tag = self.args.image.partition(":")
            tag = tag or "latest"
            registry, image = registry_image.split("/", 1)
            version, timestamp = extract_version_timestamp(tag)
            if timestamp:
                tags = fetch_tags(registry, image, tag, self.args.limit)
                tag = find_latest_tag(tag, version, timestamp, tags) or "latest"

            digest = get_digest(registry, image, tag)
            print(f"{registry}/{image}:{tag}@{digest}")

            sys.exit(0)

        if not self.container_files:
            sys.exit("No container files found")

        for filepath in self.container_files:
            updates = self.process_file(filepath)
            if updates:
                print(f"{filepath}:")
                for image, old_tag, new_tag in updates:
                    print(f"  {image}:{old_tag} -> {new_tag}")
                    self.total_updates += 1

        if self.total_updates == 0:
            print("All base images are up to date")
        elif self.dry_run:
            print(f"\nWould update {self.total_updates} image(s)")
        else:
            print(f"\nUpdated {self.total_updates} image(s)")


def main():
    args = parse_args()

    updater = ImageUpdater(args)
    updater.update()


if __name__ == "__main__":
    main()
