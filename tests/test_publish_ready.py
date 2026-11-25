"""Guards for what the public sees: the front page, the alpha notes, the release steps, and every link.

These tests keep the public claims honest. For example, nothing may offer an ISO download before the
rebrand, and the logo and the links on the front page must actually exist."""
import glob
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def read(*parts):
    with open(os.path.join(ROOT, *parts)) as fh:
        return fh.read()


def markdown_files():
    names = ["README.md", "NOTICE.md", "CONTRIBUTING.md", "SECURITY.md"]
    names += sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "docs", "*.md")))
    names += sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "branding", "*.md")))
    return [n for n in names if os.path.exists(os.path.join(ROOT, n))]


class FrontPage(unittest.TestCase):
    def test_readme_shows_the_logo_and_the_file_exists(self):
        self.assertIn("branding/normie-logo.svg", read("README.md"))
        self.assertTrue(os.path.exists(os.path.join(ROOT, "branding", "normie-logo.svg")))

    def test_readme_says_alpha_points_to_the_release_and_links_the_alpha_notes(self):
        text = read("README.md")
        self.assertIn("alpha", text.lower())
        self.assertIn("/releases)", text)            # not /releases/latest: a pre-release is never "latest"
        self.assertIn("SHA-256", text)
        self.assertIn("docs/ALPHA-NOTES.md", text)
        self.assertNotIn("no public ISOs", text)

    def test_notice_says_the_logo_is_original(self):
        text = read("NOTICE.md")
        self.assertIn("original artwork", text)
        self.assertIn("not affiliated", text.lower())


class AlphaNotes(unittest.TestCase):
    def setUp(self):
        self.text = read("docs", "ALPHA-NOTES.md")
        self.low = " ".join(self.text.lower().split())      # line breaks do not matter

    def test_states_the_limits_plainly(self):
        for phrase in ("no snapshots", "reinstalling", "not for anything important"):
            self.assertIn(phrase, self.low, phrase)

    def test_says_where_the_iso_is_and_how_to_check_it(self):
        for phrase in ("sourceforge", "internet archive", "sha-256", "too big for a github release"):
            self.assertIn(phrase, self.low, phrase)

    def test_is_honest_about_the_codecs_and_the_unreviewed_rebrand(self):
        for phrase in ("rpm fusion free", "legal list has not looked"):
            self.assertIn(phrase, self.low, phrase)

    def test_says_what_is_untested(self):
        for phrase in ("not tested yet", "secure boot", "older nvidia"):
            self.assertIn(phrase, self.low, phrase)

    def test_does_not_link_an_iso_on_github(self):
        for bad in ("releases/download",):
            self.assertNotIn(bad, self.low, bad)


class ReleaseSteps(unittest.TestCase):
    def test_release_is_a_prerelease_and_never_carries_the_iso(self):
        text = read("docs", "DISTRIBUTING-THE-ISO.md")
        self.assertIn("gh release create", text)
        self.assertIn("--prerelease", text)
        self.assertIn("release-notes.md", text)
        self.assertIn("docs/ALPHA-NOTES.md", text)
        self.assertIn("Do not attach an ISO", read("docs", "PUBLISHING.md"))

    def test_the_iso_steps_tag_the_build_commit_and_use_valid_archive_names(self):
        text = read("docs", "DISTRIBUTING-THE-ISO.md")
        self.assertIn('git tag -a "v$VER" COMMIT', text)
        self.assertIn("BUILD-INFO.txt", text)
        self.assertIn("rsync", text)
        self.assertIn("frs.sourceforge.net", text)
        self.assertIn("IAID=normie-linux-${VER//./-}", text)
        self.assertNotIn("normie-linux-0.1", text)          # Internet Archive identifiers cannot hold periods
        # the gh command in the ISO steps must attach only small files
        for line in text.splitlines():
            if "gh release create" in line:
                self.assertNotIn(".iso ", line.replace(".iso.sha256", ""), line)
                self.assertIn("--prerelease", line)

    def test_release_steps_check_the_two_addresses_first(self):
        text = read("docs", "PUBLISHING.md")
        self.assertIn("grep '^DEPS_LIST_URL=' packaging/normie-tools/files/etc/normie/update.conf", text)
        self.assertIn("<contact>", text)

    def test_the_notes_file_named_in_the_release_command_exists(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, "docs", "ALPHA-NOTES.md")))


class NoFedoraArtwork(unittest.TestCase):
    def test_no_fedora_logo_files_are_shipped_in_the_source(self):
        found = []
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for name in files:
                low = name.lower()
                if low.endswith((".svg", ".png", ".jpg", ".jpeg", ".ico", ".xpm")) and "fedora" in low:
                    found.append(os.path.relpath(os.path.join(base, name), ROOT))
        self.assertEqual(found, [])


class Links(unittest.TestCase):
    def test_every_relative_link_in_the_public_documents_resolves(self):
        broken = []
        for name in markdown_files():
            text = read(name)
            for m in re.finditer(r"\]\(([^)\s]+)\)", text):
                url = m.group(1)
                if re.match(r"^(https?:|mailto:|#)", url):
                    continue
                target = os.path.normpath(os.path.join(os.path.dirname(os.path.join(ROOT, name)), url.split("#")[0]))
                if not os.path.exists(target):
                    broken.append((name, url))
        self.assertEqual(broken, [])

    def test_the_html_logo_tag_in_the_readme_points_at_a_real_file(self):
        for m in re.finditer(r'<img[^>]+src="([^"]+)"', read("README.md")):
            self.assertTrue(os.path.exists(os.path.join(ROOT, m.group(1))), m.group(1))


if __name__ == "__main__":
    unittest.main()
