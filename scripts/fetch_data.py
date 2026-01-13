import json
import requests
import time
import os
from urllib.parse import urlparse

NVDA_API_URL = "https://addonstore.nvaccess.org/en/all/latest.json"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    # You can add Authorization: token YOUR_TOKEN here if you want to increase rate limits
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

def get_github_asset_downloads(owner, repo, url):
    """
    Query GitHub releases API for a repo and look for an asset by name.
    Return download_count or None if not found.
    """
    releases_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
    try:
        resp = requests.get(releases_url, headers=GITHUB_API_HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"Warning: GitHub API returned {resp.status_code} for {owner}/{repo}")
            return None
        releases = resp.json()
        for release in releases:
            assets = release.get("assets", [])
            for asset in assets:
                if asset.get("browser_download_url") == url:
                    return asset.get("download_count", -1)
        # Asset not found in any release
        print(f"Info: Asset '{url}' not found in releases of {owner}/{repo}")
        return None
    except Exception as e:
        print(f"Error querying GitHub releases for {owner}/{repo}: {e}")
        return None

def main():
    print(f"Fetching NVDA add-ons list from {NVDA_API_URL}")
    try:
        r = requests.get(NVDA_API_URL, timeout=30)
        r.raise_for_status()
        addons = r.json()
    except Exception as e:
        print(f"Failed to fetch NVDA add-ons JSON: {e}")
        return

    results = []

    for addon in addons:
        addon_id = addon.get("addonId")
        addon_name = addon.get("displayName")
        url = addon.get("URL")
        version = addon.get("addonVersionName")
        
        # Prepare result entry per add-on with list of versions stats
        addon_entry = {
            "id": addon_id,
            "name": addon_name,
            "url": url,
            "version": version,
            "on_github": None,  # will be True/False after check
        }

        # Determine if hosted on GitHub from homepage url
        githubOwnerRepo = extract_github_owner_repo(url)
        if githubOwnerRepo is None:
            addon_entry["on_github"] = False
            # No GitHub hosting, skip download counts
            results.append(addon_entry)
            continue
        else:
            addon_entry["on_github"] = True

        owner, repo = githubOwnerRepo
        
        download_count = get_github_asset_downloads(owner, repo, url)
        if download_count is None:
        	addon_entry["download_count"] = -1
        	addon_entry["asset_missing"] = True
        else:
        	addon_entry["download_count"] = download_count
        	addon_entry["asset_missing"] = False

        results.append(addon_entry)

    # Write result JSON
    with open("new_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("Data collection complete. Results saved to new_data.json")

if __name__ == "__main__":
    main()
