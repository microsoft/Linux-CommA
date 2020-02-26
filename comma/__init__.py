from datetime import datetime, timezone, timedelta
from elasticsearch import Elasticsearch, helpers
from pygit2 import (
    Repository,
    discover_repository,
    clone_repository,
    GIT_SORT_TOPOLOGICAL,
)


repos = [
    (
        "linux-mainline",
        "master",
        "git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
        "/tmp/linux-mainline",
    ),
    (
        "openSUSE",
        "SLE15-SP2-AZURE",
        "https://github.com/openSUSE/kernel.git",
        "/tmp/openSUSE",
    ),
]


def create_document(commit, repo, name):
    author_time = datetime.fromtimestamp(
        float(commit.author.time), timezone(timedelta(minutes=commit.author.offset)),
    ).isoformat()

    commit_time = datetime.fromtimestamp(
        float(commit.commit_time),
        timezone(timedelta(minutes=commit.commit_time_offset)),
    ).isoformat()

    patchid = 0
    files = []
    if len(commit.parents) > 0:
        diff = repo.diff(commit.parents[0], commit)
        patchid = diff.patchid.hex
        files = [d.new_file.path for d in diff.deltas]

    return {
        "_index": "commits",
        "_type": "document",
        "_id": commit.hex,
        "doc": {
            "repo": name,
            "commit_id": commit.hex,
            "patch_id": patchid,
            "parent_ids": [p.hex for p in commit.parents],
            "merge": len(commit.parents) > 1,
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
            "summary": commit.message.splitlines()[0],
            # TODO: Split out Signed-off-by etc.
            "message": "\n".join(commit.message.splitlines()[2:]),
            "files": files,
            # "hunks": [
            #     {
            #         "header": h.header,
            #         "lines": [
            #             l.content.strip() for l in h.lines if not l.content.isspace()
            #         ],
            #     }
            #     for d in diff
            #     for h in d.hunks
            # ],
        },
    }


def get_repo(name, branch, url, path):
    if discover_repository(path):
        repo = Repository(path)
        repo.remotes["origin"].fetch()
    else:
        repo = clone_repository(url, path, bare=True)
    return repo


def get_patches():
    for name, branch, url, path in repos:
        repo = get_repo(name, branch, url, path)
        walker = repo.walk(repo.lookup_branch(branch).target, GIT_SORT_TOPOLOGICAL)
        # TODO: Hide fewer commits.
        walker.hide(repo["4dba490412e7f6c9f17a0afcf7b08f110817b004"].id)
        for commit in walker:
            yield create_document(commit, repo, name)


elastic = Elasticsearch(sniff_on_start=True)
print(elastic.info())
print("Indexing commits...")
for success, info in helpers.parallel_bulk(elastic, get_patches(), thread_count=8):
    if not success:
        print(info)
