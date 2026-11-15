"""A study's frozen code, run from its tag.

Both studies are frozen at tags (freeze.FREEZE_TAG, followup_freeze.FREEZE_TAG): the commits
their test runs ran on. HEAD moves on after that (the demo, the README), and any change under
src/opt_agent/ or to requirements.lock makes each study's check() refuse at HEAD, as it should,
since check() gates a new test run. Rebuilding a study's numbers needs the code that made
them, not HEAD's:
- Tree.extract writes the tag's files from git's objects into an empty directory
  (`git archive`), so nothing depends on what the working tree holds;
- Tree.copy adds what the tag doesn't hold: git-ignored data (the LLM4OR keys), run
  directories committed after the tag, and the write-up scripts written after it;
- Tree.python runs Python there with this interpreter and the tree's src/ ahead of the
  editable install, so `import opt_agent` is the tag's package.
Inside the tree, each study's own check() passes or fails as it did at the tag: the tag's
fingerprint against the tag's approval, and the installed packages against the tag's lock.

Copies, not links: the frozen code resolves every input inside its own tree
(freeze._relative), and a rebuild must never write into this checkout. The API key (and the
switch that reads .env) is removed from the environment, so nothing run here can spend.
"""

import io
import os
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

from opt_agent.runs import REPO_ROOT, git

SECRETS = ("ANTHROPIC_API_KEY", "OPT_AGENT_LIVE")  # never passed to frozen code


class FrozenError(Exception):
    """A tag's tree can't be made or its code failed; the message says which and why."""


@dataclass(frozen=True)
class Tree:
    tag: str
    root: Path

    @classmethod
    def extract(cls, tag: str, root: Path) -> "Tree":
        """The files of `tag`, written to `root` (new or empty) from git's objects."""
        commit = git("rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}")
        if commit is None:
            raise FrozenError(f"no tag {tag} here (git fetch --tags)")
        if root.exists() and any(root.iterdir()):
            raise FrozenError(f"{root} isn't empty: a tag's tree goes into a new directory")
        archive = subprocess.run(["git", "archive", "--format=tar", commit], cwd=REPO_ROOT,
                                 capture_output=True, check=True).stdout  # fmt: skip
        root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(root, filter="data")
        return cls(tag, root.resolve())

    def copy(self, *paths: str) -> None:
        """Copy repo-relative files or directories from this checkout into the tree."""
        for rel in paths:
            source, target = REPO_ROOT / rel, self.root / rel
            if not source.exists():
                raise FrozenError(f"{rel} isn't here, so it can't go into {self.tag}'s tree")
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)

    def python(self, *args: str) -> str:
        """`python *args` in the tree, with the tree's package; its output, or FrozenError
        with everything it printed."""
        env = {k: v for k, v in os.environ.items() if k not in SECRETS}
        env["PYTHONPATH"] = str(self.root / "src")
        done = subprocess.run([sys.executable, *args], cwd=self.root, env=env,
                              capture_output=True, text=True)  # fmt: skip
        if done.returncode:
            raise FrozenError(f"`python {' '.join(args)}` failed in {self.tag}'s tree:\n"
                              f"{done.stdout}{done.stderr}")  # fmt: skip
        return done.stdout

    def read(self, rel: str) -> bytes:
        return (self.root / rel).read_bytes()
