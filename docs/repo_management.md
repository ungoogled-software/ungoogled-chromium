# Platform Repository Standards and Guidelines

*This document is new, and its structure and content may change. If you have suggestions, please create an issue!*

ungoogled-chromium is comprised of anonymous developers who volunteer their efforts. Some of these developers may choose to provide long-term support for [an officially-supported platform](platforms.md), or bring support to a new platform. For such developers, this document consists of standards and management guidelines for platform repos.

We will refer to this git repository as "the main repo", and refer to repositories that add platform-specific code to build ungoogled-chromium as "platform repos". An "officially-supported platform" is a platform with a platform repo in [the ungoogled-software organization](https://github.com/ungoogled-software) and noted in [docs/platforms.md](platforms.md).

## Standards

An officially-supported platform repo:

* Must not modify or remove existing patches, GN flags, domain substitution, or binary pruning in the main repo. Instead, you can add new patches or add more files/rules to domain substitution or binary pruning. (If you think a change is needed in the main repo, please make an issue!)
* Must have a tagging/versioning scheme that includes the ungoogled-chromium version.
* Must not require an Internet connection during compilation (before compilation is OK).
* Should allow the user to download all build requirements before building.
* Must not require external services to build, aside from repos in the ungoogled-software organization and repos provided by or used by Chromium.
* Should have a reproducible build for all versions (currently, there is no formal process to enforce/verify reproducibility of binaries)

Each deviation must be clearly noted in the platform repo's documentation (such as the repo's README), and have an associated issue in the platform repo. 

## Teams in the ungoogled-software organization

Each officially-supported platform has one or more teams in the ungoogled-software organization. These teams provide additional means for collaborating with other developers, such as issue triaging and private discussions (see section "How to communicate" below).

If you are a regular contributor and would like to provide long-term support for a platform, you can request to be included in the ungoogled-software organization team for your platform. Since the number of developers is low, there is no formal process to do this; just ask in an issue.

## How to communicate

In the interest of transparency, it is recommended to discuss work in public spaces like issues or PRs. If a discussion should not involve outsiders, you can lock the issue or PR to collaborators only.

You must use team discussions if you are discussing or sharing information that can affect the security of the repository. Otherwise, you may use team discussions at your discretion.

## Issues

Each platform repo should have a team in ungoogled-software with the Triage permission level. All members should feel free to manage issues.

TODO: More details?

## Pull Requests

TODO

## Repository Settings and Shared Resources

Shared resources includes:

* CI services like CirrusCI, GitHub Actions, etc.
* Build services like OpenSUSE Build Service (OBS)

These need to be handled with care, as they can cause a wide variety of issues from security and privacy leaks all the way to data loss.

There are several ways to handle shared resources:

* Assign one person to manage a certain set of settings (i.e. grant them "ownership" of those settings). If you want to change a setting, you should request a change in a team discussion.
* TODO: More ways to manage settings?
