import os
import re
import unittest
from unittest.mock import patch

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
        selected = {tag for group in groups for tag in group if re.fullmatch(previews.preview_pattern(REF), tag)}
        self.assertEqual(selected, set(own))
        for tag in other + releases + [own[0] + "-extra"]:
            self.assertIsNone(re.fullmatch(previews.preview_pattern(REF), tag))

    def test_all_commit_tags_for_branch_are_selected(self):
        groups = [tags_for(REF, f"{i:040x}") for i in range(250)]
        selected = {tag for group in groups for tag in group if re.fullmatch(previews.preview_pattern(REF), tag)}
        self.assertEqual(len(selected), 251)

    def test_invalid_dry_run_fails_closed(self):
        for value in ["", "True", "0", "invalid"]:
            with patch.dict(os.environ, {"DRY_RUN": value}), self.assertRaises(ValueError):
                previews.dry_run_enabled()

    def test_reject_untrusted_api_origins_and_redirects(self):
        for url in ["https://example.com", "https://hub.docker.com", "http://api.github.com", "https://api.github.com.evil.test"]:
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

    def test_closed_pr_plan_only_matches_branch_scoped_tags(self):
        with patch.object(previews, "api", side_effect=[self.pr, []]) as api, \
                patch.object(previews, "outputs") as output:
            previews.cleanup_plan()
        self.assertEqual(api.call_count, 2)
        self.assertTrue(all("/repos/owner/image/pulls" in call.args[0] for call in api.call_args_list))
        result = output.call_args.args[0]
        self.assertEqual(result["branch_ref"], REF)
        self.assertEqual(result["dry_run"], "false")
        for tag in tags_for(REF):
            self.assertIsNotNone(re.fullmatch(result["delete_pattern"], tag))
        for tag in tags_for(OTHER_REF) + ["latest", "3.3.11", f"preview-sha-{'b' * 40}"]:
            self.assertIsNone(re.fullmatch(result["delete_pattern"], tag))

    def test_open_pr_cannot_be_deleted(self):
        self.pr["state"] = "open"
        with patch.object(previews, "api", return_value=self.pr), self.assertRaises(ValueError):
            previews.cleanup_plan()

    def test_branch_reused_by_open_pr_is_preserved(self):
        with patch.object(previews, "api", side_effect=[self.pr, [{"number": 80}]]) as api, \
                patch.object(previews, "outputs") as output:
            previews.cleanup_plan()
        self.assertIn("state=open&head=owner%3Afeature%2Fexample&base=main", api.call_args.args[0])
        self.assertEqual(output.call_args.args[0], {"enabled": "false"})

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


if __name__ == "__main__":
    unittest.main()
