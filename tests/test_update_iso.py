"""
Tests for tools/update-iso.sh. The real checks and the real build are replaced by stand-ins that just
record they were called, so this runs in seconds and builds nothing.
"""
import atexit
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

PY_STUB = '''import os, sys
with open(os.environ["CALL_LOG"], "a") as fh:
    fh.write(os.path.basename(sys.argv[0]) + " " + " ".join(sys.argv[1:]) + "\\n")
print("stub", os.path.basename(sys.argv[0]), "ran")
sys.exit(1 if os.path.basename(sys.argv[0]) in os.environ.get("STUB_FAIL", "").split(",") else 0)
'''
BUILD_STUB = '''#!/bin/bash
echo "build.sh $*" >> "$CALL_LOG"
[ "${STUB_FAIL:-}" = build ] && exit 1
exit 0
'''
RPMS_STUB = '''#!/bin/bash
echo "build-rpms.sh $*" >> "$CALL_LOG"
[ "${STUB_FAIL:-}" = build-rpms ] && exit 1
exit 0
'''
TEST_STUB = '''import os, unittest
class T(unittest.TestCase):
    def test_it(self):
        self.assertNotIn("tests", os.environ.get("STUB_FAIL", "").split(","))
'''


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    if mode:
        os.chmod(path, mode)


def read(path):
    with open(path) as fh:
        return fh.read()


class UpdateIso(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp(prefix="normie-upd-iso-")
        atexit.register(shutil.rmtree, d, True)
        self.repo, self.out, self.log = f"{d}/repo", f"{d}/out", f"{d}/calls.log"
        os.makedirs(self.out)
        os.makedirs(f"{self.repo}/tools")
        write(self.log, "")
        shutil.copy(os.path.join(ROOT, "tools", "update-iso.sh"), self.tools("update-iso.sh"))
        os.chmod(self.tools("update-iso.sh"), 0o755)
        for name in ("validate-kiwi.py", "check-packages.py", "solve-check.py"):
            write(self.tools(name), PY_STUB)
        write(self.tools("build.sh"), BUILD_STUB, 0o755)
        write(self.tools("build-rpms.sh"), RPMS_STUB, 0o755)
        write(f"{self.repo}/tests/test_stub.py", TEST_STUB)
        self.env = dict(os.environ, NORMIE_TEST="1", NORMIE_OUT=self.out, CALL_LOG=self.log,
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        self.env.pop("STUB_FAIL", None)
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "start")

    def tools(self, name):
        return f"{self.repo}/tools/{name}"

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, env=self.env, capture_output=True, text=True)

    def make_patch(self, subject="Add a feature", filename="feature.txt"):
        write(f"{self.repo}/{filename}", "content\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject)
        patch = f"{os.path.dirname(self.repo)}/{abs(hash(subject))}.patch"
        write(patch, self.git("format-patch", "-1", "--stdout").stdout)
        self.git("reset", "-q", "--hard", "HEAD~1")
        return patch

    def run_script(self, *args, **extra):
        env = dict(self.env, **extra)
        r = subprocess.run(["bash", self.tools("update-iso.sh"), *args], cwd=self.repo, env=env,
                           capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def calls(self):
        return read(self.log).splitlines()

    def test_applies_the_patch_then_runs_every_step_in_order(self):
        patch = self.make_patch()
        rc, out = self.run_script(patch)
        self.assertEqual(rc, 0, out)
        self.assertTrue(os.path.exists(f"{self.repo}/feature.txt"))
        self.assertEqual(self.calls(), ["validate-kiwi.py ", "build-rpms.sh --if-needed", "check-packages.py ",
                                        "solve-check.py Normie-Full-Live", "build.sh Normie-Full-Live"])
        self.assertIn("All done", out)
        self.assertTrue(os.path.exists(f"{self.out}/preflight.txt"))

    def test_a_patch_that_is_already_applied_is_skipped_not_an_error(self):
        patch = self.make_patch()
        self.run_script(patch)
        open(self.log, "w").close()
        rc, out = self.run_script(patch)
        self.assertEqual(rc, 0, out)
        self.assertIn("Already applied, skipping", out)
        self.assertEqual(len(self.git("log", "--oneline").stdout.splitlines()), 2)      # not applied twice
        self.assertIn("build.sh Normie-Full-Live", self.calls())

    def test_a_long_title_that_git_folds_over_two_lines_is_still_recognised(self):
        subject = "Remove Snap, add experimental apps, deliver dependency fixes, prepare for GitHub and then some more words"
        patch = self.make_patch(subject)
        self.run_script(patch)
        rc, out = self.run_script(patch)
        self.assertEqual(rc, 0, out)
        self.assertIn("Already applied, skipping", out)

    def test_two_patches_apply_in_the_order_given(self):
        p1 = self.make_patch("First thing", "one.txt")
        self.git("am", p1)
        p2 = self.make_patch("Second thing", "two.txt")
        self.git("reset", "-q", "--hard", "HEAD~1")
        rc, out = self.run_script(p1, p2)
        self.assertEqual(rc, 0, out)
        subjects = self.git("log", "--format=%s").stdout.splitlines()
        self.assertEqual(subjects[:2], ["Second thing", "First thing"])

    def test_failing_tests_stop_everything_before_the_checks_and_the_build(self):
        rc, out = self.run_script(STUB_FAIL="tests")
        self.assertEqual(rc, 1)
        self.assertIn("automated tests failed", out)
        self.assertEqual(self.calls(), [])

    def test_missing_package_names_stop_before_the_solver_and_the_build(self):
        rc, out = self.run_script(STUB_FAIL="check-packages.py")
        self.assertEqual(rc, 1)
        self.assertIn("do not exist", out)
        self.assertIn("preflight.txt", out)
        self.assertEqual(self.calls(), ["validate-kiwi.py ", "build-rpms.sh --if-needed", "check-packages.py "])

    def test_a_failure_building_the_normie_packages_stops_before_the_checks_and_the_build(self):
        rc, out = self.run_script(STUB_FAIL="build-rpms")
        self.assertEqual(rc, 1)
        self.assertIn("could not be built", out)
        self.assertIn("rpm-build createrepo_c", out)
        self.assertEqual(self.calls(), ["validate-kiwi.py ", "build-rpms.sh --if-needed"])

    def test_a_version_without_the_package_script_still_works(self):
        os.remove(self.tools("build-rpms.sh"))
        rc, out = self.run_script()
        self.assertEqual(rc, 0, out)
        self.assertIn("no packages of its own", out)

    def test_conflicts_stop_before_the_build(self):
        rc, out = self.run_script(STUB_FAIL="solve-check.py")
        self.assertEqual(rc, 1)
        self.assertNotIn("build.sh Normie-Full-Live", self.calls())

    def test_a_failed_build_is_reported_with_where_the_log_is(self):
        rc, out = self.run_script(STUB_FAIL="build")
        self.assertEqual(rc, 1)
        self.assertIn("The build failed", out)
        self.assertIn("Normie-Full-Live.log", out)
        self.assertNotIn("All done", out)

    def test_a_patch_that_does_not_apply_changes_nothing_and_leaves_no_half_done_state(self):
        bad = f"{os.path.dirname(self.repo)}/bad.patch"
        write(bad, "this is not a patch\n")
        before = self.git("rev-parse", "HEAD").stdout
        rc, out = self.run_script(bad)
        self.assertEqual(rc, 1)
        self.assertIn("did not apply", out)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)
        self.assertFalse(os.path.exists(f"{self.repo}/.git/rebase-apply"))
        self.assertEqual(self.calls(), [])

    def test_a_missing_patch_file_is_explained(self):
        rc, out = self.run_script("/nonexistent/0099-nothing.patch")
        self.assertEqual(rc, 1)
        self.assertIn("Cannot find the patch file", out)

    def test_no_build_option_stops_after_the_checks(self):
        rc, out = self.run_script("--no-build")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("build.sh", " ".join(self.calls()))
        self.assertIn("Skipping the build", out)

    def test_profile_option_is_passed_to_the_solver_and_the_build(self):
        rc, out = self.run_script("--profile", "Normie-Live")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.calls()[-2:], ["solve-check.py Normie-Live", "build.sh Normie-Live"])

    def test_unknown_option_is_refused(self):
        rc, out = self.run_script("--frobnicate")
        self.assertEqual(rc, 2)

    def test_it_works_from_any_folder(self):
        patch = self.make_patch()
        r = subprocess.run(["bash", self.tools("update-iso.sh"), patch], cwd="/", env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(f"{self.repo}/feature.txt"))

    # ---- a half-finished earlier 'git am' (the "previous rebase directory still exists" error)
    def leave_a_stuck_am_session(self):
        write(f"{self.repo}/f.txt", "base\n")
        self.git("add", "-A"); self.git("commit", "-q", "-m", "add f")
        write(f"{self.repo}/f.txt", "change A\n")
        self.git("add", "-A"); self.git("commit", "-q", "-m", "Change f to A")
        conflicting = f"{os.path.dirname(self.repo)}/conflicting.patch"
        write(conflicting, self.git("format-patch", "-1", "--stdout").stdout)
        self.git("reset", "-q", "--hard", "HEAD~1")
        write(f"{self.repo}/f.txt", "change B\n")
        self.git("add", "-A"); self.git("commit", "-q", "-m", "Change f to B")
        self.git("am", conflicting)                                   # fails and leaves the session open
        self.assertTrue(os.path.isdir(f"{self.repo}/.git/rebase-apply"))

    def test_a_stuck_earlier_patch_attempt_is_cleared_automatically(self):
        good = self.make_patch("A fresh feature", "fresh.txt")
        self.leave_a_stuck_am_session()
        rc, out = self.run_script(good)
        self.assertEqual(rc, 0, out)
        self.assertIn("half-finished earlier patch attempt", out)
        self.assertFalse(os.path.exists(f"{self.repo}/.git/rebase-apply"))
        self.assertTrue(os.path.exists(f"{self.repo}/fresh.txt"))
        self.assertIn("build.sh Normie-Full-Live", self.calls())

    def test_a_stuck_session_is_cleared_even_when_no_patch_is_given(self):
        self.leave_a_stuck_am_session()
        rc, out = self.run_script()
        self.assertEqual(rc, 0, out)
        self.assertFalse(os.path.exists(f"{self.repo}/.git/rebase-apply"))

    def test_some_other_git_operation_in_progress_is_not_touched(self):
        os.makedirs(f"{self.repo}/.git/rebase-apply")                 # a rebase has this folder but no 'applying' file
        rc, out = self.run_script()
        self.assertEqual(rc, 1)
        self.assertIn("middle of something else", out)
        self.assertTrue(os.path.isdir(f"{self.repo}/.git/rebase-apply"))
        self.assertEqual(self.calls(), [])

    def test_a_patch_that_changes_the_script_itself_does_not_break_the_run(self):
        # patches can edit tools/update-iso.sh while it is running; reading it all first keeps that safe
        script = self.tools("update-iso.sh")
        with open(script, "a") as fh:
            fh.write("# touched by a patch\n")
        self.git("add", "-A"); self.git("commit", "-q", "-m", "Edit the update script itself")
        patch = f"{os.path.dirname(self.repo)}/selfedit.patch"
        write(patch, self.git("format-patch", "-1", "--stdout").stdout)
        self.git("reset", "-q", "--hard", "HEAD~1")
        rc, out = self.run_script(patch)
        self.assertEqual(rc, 0, out)
        self.assertIn("# touched by a patch", read(script))
        self.assertIn("All done", out)
        self.assertIn("build.sh Normie-Full-Live", self.calls())

    def test_the_whole_script_is_read_before_anything_runs(self):
        text = read(os.path.join(ROOT, "tools", "update-iso.sh"))
        self.assertTrue(text.rstrip().endswith('main "$@"\nexit $?'))


if __name__ == "__main__":
    unittest.main()
