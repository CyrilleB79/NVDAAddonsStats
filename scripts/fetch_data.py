# This file is part of NVDA add-ons stats.
#
# Copyright (C) 2026 Cyrille Bougot
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <https://www.gnu.org/licenses/>.

import json
import requests
import time
import datetime
import os
from urllib.parse import urlparse

NVDA_API_URL = "https://addonstore.nvaccess.org/en/all/latest.json"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {os.getenv('GITHUB_TOKEN')}"
}

def extract_github_owner_repo(url):
    """
    Extract GitHub owner and repo from a URL if possible.
    Return (owner, repo) or None if not GitHub URL.
    """
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.netloc.lower() != "github.com":
        return None
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        return None
    return parts[0], parts[1]

def isSameReleaseUrl(url1, url2):
    """
    Compares two GitHub release URLs to decide if they are the same.
    We ignore owner and repo in the path. to test if same release because owner / repo may have changed.
    We also ignore case because some URL suffixes only differ with case; but GitHub download URL are not
    case sensitive.
    """
    def get_suffix(url):
        p = urlparse(url)
        # E.g.: path = /owner/repo/releases/download/tag/filename
        parts = p.path.split('/')
        try:
            idx = parts.index("download")
            suffix = parts[idx+1:]
            return "/".join(suffix)
        except ValueError:
            return None

    suffix1 = get_suffix(url1)
    suffix2 = get_suffix(url2)
    if suffix1 is None or suffix2 is None:
        return False
    return suffix1.lower() == suffix2.lower()

def get_github_asset_downloads(owner, repo, url):
    """
    Query GitHub releases API for a repo and look for an asset by name.
    Return download_count or None if not found.
    """
    releases_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
    try:
        resp = requests.get(releases_url, headers=GITHUB_API_HEADERS, timeout=15)
        if resp.status_code == 403:
            print(f"Warning: GitHub API returned 403 for {owner}/{repo}")
            if resp.status_code == 403:
                try:
                    error_data = resp.json()
                    message = error_data.get("message", "No message in response")
                except ValueError:
                    # The response is not a valid JSON
                    message = resp.text or "No error message returned"
                print(f"Warning: GitHub API returned 403 for {owner}/{repo}: {message}")
                return None
            
        elif resp.status_code != 200:
            print(f"Warning: GitHub API returned {resp.status_code} for {owner}/{repo}")
            return None
        releases = resp.json()
        for release in releases:
            assets = release.get("assets", [])
            for asset in assets:
                if isSameReleaseUrl(asset.get("browser_download_url"), url):
                    return asset.get("download_count", -1)
        # Asset not found in any release
        print(f"Info: Asset '{url}' not found in releases of {owner}/{repo}")
        # Debug info
        print(f"{url=}")
        for release in releases:
            assets = release.get("assets", [])
            for asset in assets:
                print(f'{asset.get("browser_download_url")=}')
        return None
    except Exception as e:
        print(f"Error querying GitHub releases for {owner}/{repo}: {e}")
        return None

def main():
    print(f"Fetching NVDA add-ons list from {NVDA_API_URL}")
    start_time = time.perf_counter()
    generated_at = datetime.datetime.utcnow().isoformat() + "Z"

    github_requests_count = 0
    try:
        r = requests.get(NVDA_API_URL, timeout=30)
        r.raise_for_status()
        addons = r.json()
    except Exception as e:
        print(f"Failed to fetch NVDA add-ons JSON: {e}")
        return

    items = []

    for addon in addons:
        addon_id = addon.get("addonId")
        addon_name = addon.get("displayName")
        url = addon.get("URL")
        version = addon.get("addonVersionName")
        channel = addon.get("channel")
        publisher = addon.get("publisher")
        submissionTime = addon.get("submissionTime")

        # Prepare result entry per add-on with list of versions stats
        addon_entry = {
            "id": addon_id,
            "name": addon_name,
            "url": url,
            "version": version,
            "channel": channel,
            "publisher": publisher,
            "submission_time": submissionTime,
            "on_github": None,  # will be True/False after check
        }

        # Determine if hosted on GitHub from homepage url
        githubOwnerRepo = extract_github_owner_repo(url)
        if githubOwnerRepo is None:
            addon_entry["on_github"] = False
            # No GitHub hosting, skip download counts
            items.append(addon_entry)
            continue
        else:
            addon_entry["on_github"] = True

        owner, repo = githubOwnerRepo
        
        download_count = get_github_asset_downloads(owner, repo, url)
        github_requests_count += 1
        if download_count is None:
        	addon_entry["download_count"] = -1
        	addon_entry["asset_missing"] = True
        else:
        	addon_entry["download_count"] = download_count
        	addon_entry["asset_missing"] = False

        items.append(addon_entry)

    end_time = time.perf_counter()
    duration = round(end_time - start_time, 2)

    # Write result JSON
    output = {
        "meta": {
            "generated_at": generated_at,
            "generation_duration_seconds": duration,
            "total_addons": len(items),
            "github_api_requests": github_requests_count,
        },
        "items": items
    }
    
    with open("new_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("Data collection complete. Results saved to new_data.json")

if __name__ == "__main__":
    main()
