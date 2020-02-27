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
        "/mnt/ramdisk/linux-mainline",
    ),
    (
        "openSUSE",
        "SLE15-SP2-AZURE",
        "https://github.com/openSUSE/kernel.git",
        "/mnt/ramdisk/openSUSE",
    ),
]

hyperv_files = {
    "arch/x86/include/asm/mshyperv.h",
    "arch/x86/include/asm/trace/hyperv.h",
    "arch/x86/include/asm/hyperv-tlfs.h",
    "arch/x86/kernel/cpu/mshyperv.c",
    "drivers/clocksource/hyperv_timer.c",
    "drivers/hid/hid-hyperv.c",
    "drivers/input/serio/hyperv-keyboard.c",
    "drivers/pci/controller/pci-hyperv.c",
    "drivers/pci/controller/pci-hyperv-intf.c",
    "drivers/scsi/storvsc_drv.c",
    "drivers/uio/uio_hv_generic.c",
    "drivers/video/fbdev/hyperv_fb.c",
    "drivers/iommu/hyperv-iommu.c",
    "net/vmw_vsock/hyperv_transport.c",
    "include/clocksource/hyperv_timer.h",
    "include/linux/hyperv.h",
    "include/uapi/linux/hyperv.h",
    "include/asm-generic/mshyperv.h",
}

hyperv_dirs = {
    "arch/x86/hyperv/",
    "drivers/hv/",
    "drivers/net/hyperv/",
    "tools/hv/",
}

patchids = set()


def create_document(commit, repo, name):
    author_time = datetime.fromtimestamp(
        float(commit.author.time), timezone(timedelta(minutes=commit.author.offset)),
    ).isoformat()

    commit_time = datetime.fromtimestamp(
        float(commit.commit_time),
        timezone(timedelta(minutes=commit.commit_time_offset)),
    ).isoformat()

    # Leaf commits and merges are useless
    if len(commit.parents) != 1:
        # print("Skipping due to parents!")
        return None

    # Commits without title and description are useless
    message = commit.message.splitlines()
    if len(message) < 3:
        return None

    diff = repo.diff(commit.parents[0], commit)
    files = [d.new_file.path for d in diff.deltas]

    # Limit to Microsoft relevance
    if not (
        commit.author.email.endswith("@microsoft.com")
        or not set(files).isdisjoint(hyperv_files)
        or any(f.startswith(d) for d in hyperv_dirs for f in files)
    ):
        return None

    # Record if patch is present
    patchid = diff.patchid.hex
    if name == "linux-mainline":
        upstream = True
        patchids.add(patchid)
    else:
        upstream = patchid in patchids

    bugfix = any(["Fixes:" in l for l in message])

    return {
        "_index": "commits",
        "_id": commit.hex,
        "repo": name,
        "commit_id": commit.hex,
        "parent_ids": [p.hex for p in commit.parents],
        # "merge": len(commit.parents) > 1,
        "upstream": upstream,
        "bugfix": bugfix,
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
        "title": message[0],
        # TODO: Split out Signed-off-by etc.
        "description": "\n".join(message[2:]),
        "files": files,
        # "patch": diff.patch,
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
        print("Indexing repo:", name)
        walker = repo.walk(
            repo.branches.remote["origin/" + branch].target, GIT_SORT_TOPOLOGICAL
        )
        # TODO: Hide fewer commits.
        walker.hide(repo["4dba490412e7f6c9f17a0afcf7b08f110817b004"].id)
        for commit in walker:
            document = create_document(commit, repo, name)
            if document:
                yield document


elastic = Elasticsearch(sniff_on_start=True)
print(elastic.info())
signature_mapping = {
    "properties": {
        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "email": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "time": {"type": "date"},
    }
}
body = {
    "settings": {
        "analysis": {
            "analyzer": {
                "file_path": {
                    "type": "custom",
                    "tokenizer": "path_hierarchy",
                    "filter": ["lowercase"],
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "repo": {"type": "keyword"},
            "commit_id": {"type": "keyword"},
            "parent_ids": {"type": "keyword"},
            # "merge": {"type": "boolean"},
            "upstream": {"type": "boolean"},
            "bugfix": {"type": "boolean"},
            "author": signature_mapping,
            "committer": signature_mapping,
            "title": {"type": "text"},
            "description": {"type": "text", "analyzer": "snowball"},
            "files": {"type": "text", "analyzer": "file_path", "fielddata": True},
            # "patch": {"type": "text", "index": False},
        }
    },
}
elastic.indices.create("commits", body)


print("Indexing commits...")
for success, info in helpers.streaming_bulk(elastic, get_patches()):
    if not success:
        print(info)
