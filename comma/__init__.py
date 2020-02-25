from datetime import datetime, timezone, timedelta
from elasticsearch import Elasticsearch, helpers
from pygit2 import Repository, discover_repository, clone_repository

repo_url = "git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git"
repo_path = "repos/linux-mainline"

repo = (
    Repository(repo_path)
    if discover_repository(repo_path)
    else clone_repository(repo_url, repo_path, bare=True)
)


def get_patches():
    for commit in repo.walk(repo.head.target):
        author_time = datetime.fromtimestamp(
            float(commit.author.time), timezone(timedelta(minutes=commit.author.offset))
        ).isoformat()
        commit_time = datetime.fromtimestamp(
            float(commit.commit_time),
            timezone(timedelta(minutes=commit.commit_time_offset)),
        ).isoformat()
        diff = repo.diff(commit.parents[0], commit)
        files = [d.new_file.path for d in diff.deltas]
        yield {
            "_index": "commits",
            "_type": "document",
            "_id": commit.hex,
            "doc": {
                "repo": "linux-mainline",
                "commit_id": commit.hex,
                "parent_ids": [p.hex for p in commit.parents],
                "author": {
                    "name": commit.author.name,
                    "email": commit.author.email,
                    "time": author_time,
                },
                "committer": {
                    "name": commit.committer.name,
                    "email": commit.committer.email,
                    "time": commit_time,
                },
                "message": commit.message,
                "files": files,
                # TODO: This can be way richer.
                "patch": diff.patch,
            },
        }


elastic = Elasticsearch(sniff_on_start=True)
print(elastic.info())
for success, info in helpers.parallel_bulk(elastic, get_patches()):
    print(info)
