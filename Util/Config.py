from DatabaseDriver.SqlClasses import Distros

dry_run = False
fetch = True
since = "4 years ago"
verbose = 0
default_distros = [
    Distros(
        distroID="Ubuntu16.04",
        repoLink="https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/xenial",
    ),
    Distros(
        distroID="Ubuntu18.04",
        repoLink="https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/bionic",
    ),
    Distros(
        distroID="Ubuntu19.04",
        repoLink="https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/disco",
    ),
    Distros(
        distroID="Ubuntu19.10",
        repoLink="https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/eoan",
    ),
    Distros(
        distroID="Debian9-backport",
        repoLink="https://salsa.debian.org/kernel-team/linux.git",
    ),
    Distros(distroID="SUSE12", repoLink="https://github.com/openSUSE/kernel",),
]

"""
Guildelines:
    * Follow linux file path convention
    * File path should be given from root directory
    * e.g. arch/x86/include/asm/mshyperv.h
    * please refer to Hyper-V block under MAINTAINERS file to avoid duplicates.
"""
paths_to_track = []
