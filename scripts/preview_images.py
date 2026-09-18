import argparse
from collections import defaultdict
import datetime
import hashlib
import json
import os
import re
from urllib.error import HTTPError
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
    return (
        rf"^(?:{re.escape(metadata['preview_tag'])}|"
        rf"preview-sha-[0-9a-f]{{40}}-{metadata['preview_hash']})$"
    )


def select_preview_tags(groups, ref):
    pattern = re.compile(preview_pattern(ref))
    legacy = re.compile(r"preview-sha-[0-9a-f]{40}")
    selected = set()
    for tags in groups:
        owned = {tag for tag in tags if pattern.fullmatch(tag)}
        selected.update(owned)
        # Migrate the original unscoped SHA tags only when ownership is unambiguous.
        if owned and all(tag in owned or legacy.fullmatch(tag) for tag in tags):
            selected.update(tags)
    return sorted(selected)


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Refusing an API redirect with registry credentials")


def api(url, token=None, method="GET", body=None):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc not in {"api.github.com", "hub.docker.com"}:
        raise ValueError(f"Unexpected API origin: {parsed.netloc}")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with build_opener(NoRedirects).open(request, timeout=60) as response:
            data = response.read()
            return json.loads(data) if data else None
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        for secret in [token, (body or {}).get("secret")]:
            if secret:
                detail = detail.replace(secret, "[redacted]")
        message = f"{method} {parsed.netloc}{parsed.path} returned HTTP {error.code}: {detail[:1000]}"
        if parsed.netloc == "hub.docker.com" and method == "DELETE" and error.code == 403:
            message += (
                " Check that the Docker Hub token stored in DOCKER_PASSWORD includes Delete permission;"
                " repository admin access alone does not establish the token's scope."
            )
        raise RuntimeError(message) from None


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

    owner, package = repository.split("/")
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
    owner_type = "orgs" if pr["base"]["repo"]["owner"]["type"] == "Organization" else "users"
    endpoint = f"https://api.github.com/{owner_type}/{owner}/packages/container/{quote(package, safe='')}/versions"
    groups = []
    page = 1
    while True:
        versions = api(f"{endpoint}?per_page=100&page={page}", token)
        groups.extend(version["metadata"]["container"]["tags"] for version in versions)
        if len(versions) < 100:
            break
        page += 1
    selected = select_preview_tags(groups, ref)
    print("GHCR preview tags selected:", json.dumps(selected))
    legacy = [tag for tag in selected if re.fullmatch(r"preview-sha-[0-9a-f]{40}", tag)]
    pattern = preview_pattern(ref)
    if legacy:
        pattern = f"(?:{pattern}|^(?:{'|'.join(map(re.escape, legacy))})$)"
    outputs({
        "enabled": "true",
        "branch_ref": ref,
        "delete_pattern": pattern,
        "dry_run": str(dry_run).lower(),
    })


def dockerhub_cleanup():
    ref = os.environ["PUBLISH_REF"]
    username = os.environ["DOCKER_USERNAME"]
    repository = os.environ["GITHUB_REPOSITORY"].split("/")[1]
    dry_run = dry_run_enabled()
    token = api(
        "https://hub.docker.com/v2/auth/token",
        method="POST",
        body={"identifier": username, "secret": os.environ["DOCKER_PASSWORD"]},
    )["access_token"]
    print(f"::add-mask::{token}")
    repository_url = f"https://hub.docker.com/v2/repositories/{quote(username, safe='')}/{quote(repository, safe='')}/"
    permissions = api(repository_url, token)["permissions"]
    if not permissions["admin"]:
        raise PermissionError("The Docker Hub account needs repository admin access")
    if dry_run:
        print("::notice::Dry-run does not verify the token's Delete permission; repository admin access is a separate check.")
    base = f"{repository_url}tags/"
    url = f"{base}?page_size=100"
    groups = defaultdict(list)
    while url:
        # Never send the Hub token to another host or repository via pagination.
        if not url.startswith(base):
            raise ValueError("Unexpected Docker Hub pagination URL")
        page = api(url, token)
        for tag in page["results"]:
            digest = tag["digest"]
            if not digest:
                raise ValueError(f"Missing Docker Hub digest for tag {tag['name']}")
            groups[digest].append(tag["name"])
        url = page["next"]
    selected = select_preview_tags(groups.values(), ref)
    # Keep the ownership alias until the last delete so legacy cleanup is retryable.
    selected.sort(key=lambda tag: tag == preview_metadata(ref)["preview_tag"])
    for tag in selected:
        print(f"{'Would delete' if dry_run else 'Deleting'} Docker Hub tag: {tag}")
        if not dry_run:
            api(f"{base}{quote(tag, safe='')}/", token, method="DELETE")
    print(f"{len(selected)} Docker Hub preview tags {'selected' if dry_run else 'deleted'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["metadata", "cleanup-plan", "dockerhub-cleanup"])
    operation = parser.parse_args().operation
    {
        "metadata": build_metadata,
        "cleanup-plan": cleanup_plan,
        "dockerhub-cleanup": dockerhub_cleanup,
    }[operation]()
