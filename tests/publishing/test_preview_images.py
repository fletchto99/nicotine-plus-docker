import os
import re
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import preview_images as previews


REF = "refs/heads/feature/example"
OTHER_REF = "refs/heads/feature-example"
SHA = "a" * 40


def tags_for(ref, sha=SHA):
    metadata = previews.preview_metadata(ref)
    return [
        metadata["preview_tag"],
        f"preview-sha-{sha}-{metadata['preview_hash']}",
    ]


class PreviewTests(unittest.TestCase):
    def test_tag_length_sanitization_and_collisions(self):
        refs = [
            REF, OTHER_REF, "refs/heads/main", "refs/heads/Main",
            "refs/tags/main", "refs/heads/\u65e5\u672c\u8a9e",
            "refs/heads/" + "a" * 300, "refs/heads/" + "a" * 299 + "b",
        ]
        tags = [previews.preview_metadata(ref)["preview_tag"] for ref in refs]
        self.assertEqual(len(tags), len(set(tags)))
        for tag in tags:
            self.assertRegex(tag, r"^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$")

    def test_only_exact_default_branch_is_a_release(self):
        for ref in ["refs/heads/main", "refs/heads/Main", "refs/tags/main", REF]:
            with self.subTest(ref=ref), patch.dict(os.environ, {
                "PUBLISH_REF": ref, "DEFAULT_BRANCH": "main",
            }), patch.object(previews, "outputs") as output:
                previews.build_metadata()
                self.assertEqual(
                    output.call_args.args[0]["is_release"],
                    str(ref == "refs/heads/main").lower(),
                )

    def test_only_own_branch_tags_are_selected(self):
        own = tags_for(REF)
        other = tags_for(OTHER_REF)
        releases = ["latest", "3.3.11", "amd64-latest", "arm64-3.3.11"]
        groups = [own, other, releases]
        groups.extend(tags_for(f"refs/heads/branch-{i}") for i in range(200))
        self.assertEqual(previews.select_preview_tags(groups, REF), sorted(own))
        for tag in other + releases + [own[0] + "-extra"]:
            self.assertIsNone(re.fullmatch(previews.preview_pattern(REF), tag))

    def test_all_commit_tags_for_branch_are_selected(self):
        groups = [tags_for(REF, f"{i:040x}") for i in range(250)]
        self.assertEqual(len(previews.select_preview_tags(groups, REF)), 251)

    def test_legacy_sha_tag_requires_unambiguous_owned_image(self):
        own = tags_for(REF)[0]
        legacy = f"preview-sha-{SHA}"
        self.assertEqual(previews.select_preview_tags([[own, legacy]], REF), sorted([own, legacy]))
        self.assertEqual(previews.select_preview_tags([[legacy]], REF), [])
        for unrelated in [tags_for(OTHER_REF)[0], "latest", "3.3.11"]:
            self.assertEqual(previews.select_preview_tags([[own, legacy, unrelated]], REF), [own])

    def test_invalid_dry_run_fails_closed(self):
        for value in ["", "True", "0", "invalid"]:
            with patch.dict(os.environ, {"DRY_RUN": value}), self.assertRaises(ValueError):
                previews.dry_run_enabled()

    def test_reject_untrusted_api_origins_and_redirects(self):
        for url in ["https://example.com", "http://hub.docker.com", "https://hub.docker.com.evil.test"]:
            with self.assertRaises(ValueError):
                previews.api(url, token="test-token")
        with self.assertRaises(ValueError):
            previews.NoRedirects().redirect_request(None, None, 302, "", {}, "https://example.com")


class CleanupPlanTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "owner/image", "GH_TOKEN": "test-token",
            "PR_NUMBER": "79", "DEFAULT_BRANCH": "main", "DRY_RUN": "false",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.pr = {
            "state": "closed",
            "head": {"repo": {"full_name": "owner/image"}, "ref": "feature/example"},
            "base": {"ref": "main", "repo": {"owner": {"type": "User"}}},
        }

    def test_closed_pr_plan_paginates_and_includes_legacy(self):
        unrelated_page = [{"metadata": {"container": {"tags": ["3.3.11"]}}}] * 100
        legacy = f"preview-sha-{SHA}"
        own_page = [{"metadata": {"container": {"tags": [tags_for(REF)[0], legacy]}}}]
        with patch.object(previews, "api", side_effect=[self.pr, unrelated_page, own_page]) as api, \
                patch.object(previews, "outputs") as output:
            previews.cleanup_plan()
        self.assertIn("page=2", api.call_args.args[0])
        result = output.call_args.args[0]
        self.assertEqual(result["branch_ref"], REF)
        self.assertEqual(result["dry_run"], "false")
        for tag in tags_for(REF) + [legacy]:
            self.assertIsNotNone(re.fullmatch(result["delete_pattern"], tag))
        for tag in tags_for(OTHER_REF) + ["latest", "3.3.11", f"preview-sha-{'b' * 40}"]:
            self.assertIsNone(re.fullmatch(result["delete_pattern"], tag))

    def test_open_pr_cannot_be_deleted(self):
        self.pr["state"] = "open"
        with patch.object(previews, "api", return_value=self.pr), self.assertRaises(ValueError):
            previews.cleanup_plan()

    def test_open_pr_can_be_dry_run(self):
        self.pr["state"] = "open"
        with patch.dict(os.environ, {"DRY_RUN": "true"}), \
                patch.object(previews, "api", side_effect=[self.pr, []]), \
                patch.object(previews, "outputs") as output:
            previews.cleanup_plan()
        self.assertEqual(output.call_args.args[0]["dry_run"], "true")

    def test_forks_deleted_forks_and_other_base_branches_are_skipped(self):
        cases = [
            ("repo", {"full_name": "other/image"}),
            ("repo", None),
            ("base", "other-base"),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                pr = {
                    **self.pr,
                    "head": {**self.pr["head"]},
                    "base": {**self.pr["base"]},
                }
                if field == "base":
                    pr["base"]["ref"] = value
                else:
                    pr["head"]["repo"] = value
                with patch.object(previews, "api", return_value=pr), patch.object(previews, "outputs") as output:
                    previews.cleanup_plan()
                self.assertEqual(output.call_args.args[0], {"enabled": "false"})


class DockerHubTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "PUBLISH_REF": REF, "DOCKER_USERNAME": "owner",
            "DOCKER_PASSWORD": "test-password", "GITHUB_REPOSITORY": "owner/image",
            "DRY_RUN": "true",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.base = "https://hub.docker.com/v2/repositories/owner/image/tags/"
        self.pages = [
            {"access_token": "test-token"},
            {"permissions": {"read": True, "write": True, "admin": True}},
            {"results": [
                {"name": tags_for(REF)[0], "digest": "sha256:own"},
                {"name": "latest", "digest": "sha256:release"},
            ], "next": self.base + "?page=2"},
            {"results": [
                {"name": tags_for(REF)[1], "digest": "sha256:own"},
                {"name": tags_for(OTHER_REF)[1], "digest": "sha256:other"},
            ], "next": None},
        ]

    def test_dry_run_paginates_without_deletes(self):
        with patch.object(previews, "api", side_effect=self.pages) as api:
            previews.dockerhub_cleanup()
        self.assertEqual(api.call_count, 4)
        self.assertFalse(any(call.kwargs.get("method") == "DELETE" for call in api.call_args_list))

    def test_deletion_is_limited_to_own_tags(self):
        with patch.dict(os.environ, {"DRY_RUN": "false"}), \
                patch.object(previews, "api", side_effect=self.pages + [None, None]) as api:
            previews.dockerhub_cleanup()
        deleted = {
            call.args[0] for call in api.call_args_list if call.kwargs.get("method") == "DELETE"
        }
        self.assertEqual(deleted, {self.base + tag + "/" for tag in tags_for(REF)})

    def test_bad_pagination_does_not_receive_token(self):
        self.pages[2]["next"] = "https://api.github.com/other"
        with patch.object(previews, "api", side_effect=self.pages) as api, self.assertRaises(ValueError):
            previews.dockerhub_cleanup()
        self.assertEqual(api.call_count, 3)

    def test_missing_delete_permission_fails_before_deleting(self):
        self.pages[1]["permissions"]["admin"] = False
        with patch.object(previews, "api", side_effect=self.pages) as api, self.assertRaises(PermissionError):
            previews.dockerhub_cleanup()
        self.assertEqual(api.call_count, 2)

    def test_delete_failure_is_not_suppressed(self):
        failure = HTTPError(self.base, 403, "Forbidden", {}, None)
        with patch.dict(os.environ, {"DRY_RUN": "false"}), \
                patch.object(previews, "api", side_effect=self.pages + [failure]), \
                self.assertRaises(HTTPError):
            previews.dockerhub_cleanup()


if __name__ == "__main__":
    unittest.main()
