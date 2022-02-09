# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from DatabaseDriver.SqlClasses import Distros, MonitoringSubjects

dry_run = False
fetch = True
since = "4 years ago"
verbose = 0
sections = ["Hyper-V CORE AND DRIVERS", "Hyper-V/Azure CORE AND DRIVERS", "DRM DRIVER FOR HYPERV SYNTHETIC VIDEO DEVICE"]
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
        distroID="Ubuntu20.04",
        repoLink="https://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-azure/+git/focal",
    ),
    Distros(
        distroID="Debian9-backport",
        repoLink="https://salsa.debian.org/kernel-team/linux.git",
    ),
    Distros(distroID="SUSE12", repoLink="https://github.com/openSUSE/kernel",),
]

# NOTE: The Ubuntu kernels get revisions added automatically by
# checking the remote repos’ tags.
default_monitoring_subjects = [
    MonitoringSubjects(distroID="Debian9-backport", revision="stretch-backports"),
    MonitoringSubjects(distroID="SUSE12", revision="SUSE12/SLE12-SP5-AZURE"),
]

"""
Guildelines:
    * Follow linux file path convention
    * File path should be given from root directory
    * e.g. arch/x86/include/asm/mshyperv.h
    * please refer to Hyper-V block under MAINTAINERS file to avoid duplicates.
"""
paths_to_track = []
