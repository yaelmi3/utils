import sys
import baker
from contextlib import contextmanager
from git import Repo, GitCommandError
from logbook import Logger, StreamHandler

StreamHandler(sys.stdout).push_application()
log = Logger(__name__)


@contextmanager
def base_branch(git):
    """
    1. Get current branch
    2. Return branch to current branch at the end
    :type git: git.cmd.Git
    """
    current_branch = git.rev_parse("--abbrev-ref", "HEAD")
    try:
        yield
    finally:
        git.checkout(current_branch)


@baker.command
def mass_cherry_pick(source_branch, working_tree_dir, *branch_list):
    """
    1. Init repo specified in the working tree directory
    2. Obtain required commit
    3. iterate through the specified branches
    4. Create new branch that combines the source branch name
    5. Cherry pick commit
    :type source_branch: str
    :type working_tree_dir: str
    :type branch_list: list
    """
    repo = Repo(working_tree_dir)
    git = repo.git
    with base_branch(git):
        required_commit = get_required_commit(git, source_branch)
        log.info(f"Cherry-picking commit: {required_commit}")
        for branch_name in branch_list:
            new_branch = f"{source_branch}_{branch_name}"
            if new_branch not in git.branch().split():
                log.info(f"Moving to {branch_name} and pulling...")
                git.checkout(branch_name)
                log.info(git.pull())
                git.checkout("-b", new_branch)
                log.info(f"Created new branch: {new_branch}")
                git_cherry_pick(git, required_commit)
                git.push("--set-upstream", "origin", new_branch)
            else:
                log.error(f"Branch {new_branch} already exists!")


def get_required_commit(git, source_branch):
    """
    get hash of the required commit that will be cherry picked
    :type git: git.cmd.Git
    :type source_branch: str
    """
    git.checkout(source_branch)
    return git.show("-s", "--format=%H")


def git_cherry_pick(git, required_commit):
    """
    Attempt to cherry pich with the specified commit. In case of error, abort
    :type git: git.cmd.Git
    :type required_commit: str

    """
    try:
        log.notice(git.cherry_pick(required_commit))
    except GitCommandError as e:
        for error_line in e.stderr.split('\n'):
            log.error(error_line)
        log.error(f"Aborting cherry picking due to errors")
        git.cherry_pick("--abort")


if __name__ == '__main__':
    baker.run()