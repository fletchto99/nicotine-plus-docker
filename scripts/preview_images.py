import argparse
import datetime
import hashlib
import json
import os
import re
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


def preview_metadata(ref):
    branch_hash = hashlib.sha256(ref.encode()).hexdigest()[:12]
    name = ref.split("/", 2)[2]
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", name)[:107]
    return {
        "preview_tag": f"preview-{slug}-{branch_hash}",
        "preview_hash": branch_hash,
    }


def preview_pattern(ref):
    metadata = preview_metadata(ref)
    # Also clean up SHA aliases published before previews became branch-only.
    return (
        rf"^(?:{re.escape(metadata['preview_tag'])}|"
        rf"preview-sha-[0-9a-f]{{40}}-{metadata['preview_hash']})$"
    )


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Refusing an API redirect with registry credentials")


def api(url, token):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com":
        raise ValueError(f"Unexpected API origin: {parsed.netloc}")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with build_opener(NoRedirects).open(request, timeout=60) as response:
        return json.load(response)


def outputs(values):
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        for name, value in values.items():
            if "\n" in str(value) or "\r" in str(value):
                raise ValueError(f"Invalid workflow output: {name}")
            print(f"{name}={value}", file=output)


def dry_run_enabled():
    value = os.environ["DRY_RUN"]
    if value not in {"true", "false"}:
        raise ValueError("DRY_RUN must be true or false")
    return value == "true"


def build_metadata():
    ref = os.environ["PUBLISH_REF"]
    outputs({
        **preview_metadata(ref),
        "build_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "is_release": str(ref == f"refs/heads/{os.environ['DEFAULT_BRANCH']}").lower(),
    })


def cleanup_plan():
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    number = int(os.environ["PR_NUMBER"])
    dry_run = dry_run_enabled()
    pr = api(f"https://api.github.com/repos/{repository}/pulls/{number}", token)
    if (
        not pr["head"]["repo"]
        or pr["head"]["repo"]["full_name"] != repository
        or pr["base"]["ref"] != os.environ["DEFAULT_BRANCH"]
    ):
        print("::notice::Skipping a PR that cannot own this repository's branch previews")
        outputs({"enabled": "false"})
        return
    if not dry_run and pr["state"] != "closed":
        raise ValueError("Refusing to delete previews for an open PR")
    ref = f"refs/heads/{pr['head']['ref']}"
    if pr["head"]["ref"] == os.environ["DEFAULT_BRANCH"]:
        raise ValueError("Refusing to clean up the default branch")

    owner = repository.split("/")[0]
    if pr["state"] == "closed":
        head = quote(f"{owner}:{pr['head']['ref']}", safe="")
        base = quote(os.environ["DEFAULT_BRANCH"], safe="")
        open_prs = api(
            f"https://api.github.com/repos/{repository}/pulls?state=open&head={head}&base={base}&per_page=1",
            token,
        )
        if open_prs:
            print("::notice::Keeping previews because the branch is reused by an open PR")
            outputs({"enabled": "false"})
            return
    pattern = preview_pattern(ref)
    print("GHCR preview tag filter:", pattern)
    outputs({
        "enabled": "true",
        "branch_ref": ref,
        "delete_pattern": pattern,
        "dry_run": str(dry_run).lower(),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["metadata", "cleanup-plan"])
    operation = parser.parse_args().operation
    {
        "metadata": build_metadata,
        "cleanup-plan": cleanup_plan,
    }[operation]()
