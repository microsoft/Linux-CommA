import os
from datetime import datetime
from elasticsearch_dsl import connections, Document, Text, Date
from pygit2 import Repository, discover_repository, clone_repository

repo_url = "git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git"
repo_path = "repos/linux-mainline"

repo = (
    Repository(repo_path)
    if discover_repository(repo_path)
    else clone_repository(repo_url, repo_path, bare=True)
)

# for commit in repo.walk(
#     pygit2.Oid(hex="63623fd44972d1ed2bfb6e0fb631dfcf547fd1e7"), pygit2.GIT_SORT_REVERSE
# ):
#     print(commit.message)

commit = repo.get("2e90ca68b0d2f5548804f22f0dd61145516171e3")
diff = commit.tree.diff_to_tree(commit.parents[0].tree, swap=True)
# print(diff.patch)
for d in diff.deltas:
    print(d.new_file.path)
    print(d.old_file.path)


class Patch(Document):
    author_name = Text()
    author_email = Text()
    committer = Text()
    message = Text()
    tree_id = Text()
    commit_time = Date()
    patch = Text()


# connections.create_connection(hosts=os.environ["ELASTIC_HOST"])

# Patch.init()
patch = Patch(
    author_name=commit.author.name,
    author_email=commit.author.email,
    commiter=commit.committer,
    message=commit.message,
    tree_id=commit.tree_id,
    commit_time=datetime.utcfromtimestamp(commit.commit_time),
    patch=diff,
)

print(patch.commit_time)
