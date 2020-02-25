from datetime import datetime, timezone, timedelta
from elasticsearch import Elasticsearch
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


def get_patches():
    commit = repo.get("35a571346a94fb93b5b3b6a599675ef3384bc75c")
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
        "_index": "linux-mainline",
        "_op_type": "index",
        "_type": "document",
        "_id": commit.hex,
        "doc": {
            "commit_id": commit.hex,
            "author_name": commit.author.name,
            "author_email": commit.author.email,
            "author_time": author_time,
            "committer_name": commit.committer.name,
            "committer_email": commit.committer.email,
            "commit_time": commit_time,
            "message": commit.message,
            "files": files,
            "patch": diff,
        },
    }


es = Elasticsearch(sniff_on_start=True)
print(es.info())
Elasticsearch.bulk(es, get_patches())
