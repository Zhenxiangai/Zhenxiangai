import unittest
import xml.etree.ElementTree as element_tree

from scripts import update_profile_projects as profile


def repository(
    name,
    *,
    fork=False,
    private=False,
    archived=False,
    pushed_at="2026-01-01T00:00:00Z",
):
    return {
        "name": name,
        "fork": fork,
        "private": private,
        "archived": archived,
        "pushed_at": pushed_at,
    }


class RepositorySelectionTests(unittest.TestCase):
    def test_features_kanwanle_without_including_other_forks(self):
        repos = [
            repository("ordinary-fork", fork=True, pushed_at="2026-09-03T00:00:00Z"),
            repository("kanwanle", fork=True, pushed_at="2026-09-02T00:00:00Z"),
            repository("original", pushed_at="2026-09-01T00:00:00Z"),
            repository(profile.OWNER, pushed_at="2026-08-31T00:00:00Z"),
            repository("private", private=True),
            repository("archived", archived=True),
        ]

        selected = profile.select_repositories(repos)

        self.assertEqual([repo["name"] for repo in selected], ["kanwanle", "original"])


class RenderingTests(unittest.TestCase):
    def test_formats_compact_counts(self):
        self.assertEqual(profile.format_count(999), "999")
        self.assertEqual(profile.format_count(1_000), "1k")
        self.assertEqual(profile.format_count(239_087), "239.1k")

    def test_repository_names_produce_distinct_safe_paths(self):
        names = ["foo-bar", "foo_bar", "foo.bar"]

        self.assertEqual(
            [profile.project_slug(name) for name in names],
            names,
        )

    def test_rejects_projects_without_a_real_description(self):
        with self.assertRaisesRegex(SystemExit, "needs a GitHub description"):
            profile.project_description(
                {"name": "no-description", "full_name": "owner/no-description"},
                {},
            )

    def test_wraps_description_to_two_bounded_lines(self):
        lines = profile.wrap_description("很长的中文简介" * 20)

        self.assertEqual(len(lines), 2)
        self.assertTrue(all(profile.display_units(line) <= 70 for line in lines))
        self.assertTrue(lines[-1].endswith("…"))

    def test_card_is_valid_xml_and_escapes_external_text(self):
        svg = profile.card_svg(
            title="A < B & C",
            subtitle="owner/repo",
            description="Use <safe> & reliable output.",
            language="Python",
            stars=12,
            forks=3,
            updated="2026-09-01",
        )

        element_tree.fromstring(svg)
        self.assertIn("A &lt; B &amp; C", svg)
        self.assertIn("Use &lt;safe&gt; &amp; reliable output.", svg)

    def test_replace_section_preserves_surrounding_content(self):
        source = "before\n<!--START-->old<!--END-->\nafter"
        result = profile.replace_section(
            source,
            "<!--START-->",
            "<!--END-->",
            "<!--START-->new<!--END-->",
        )

        self.assertEqual(result, "before\n<!--START-->new<!--END-->\nafter")

    def test_replace_section_rejects_duplicate_markers(self):
        source = (
            "<!--START-->one<!--END-->\n"
            "<!--START-->two<!--END-->"
        )

        with self.assertRaisesRegex(SystemExit, "exactly once"):
            profile.replace_section(
                source,
                "<!--START-->",
                "<!--END-->",
                "<!--START-->new<!--END-->",
            )


if __name__ == "__main__":
    unittest.main()
