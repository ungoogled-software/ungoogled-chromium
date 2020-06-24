# Contributing

This document contains our criteria and guidelines for contributing to ungoogled-chromium.

If you have **small contributions that don't fit our criteria**, consider adding them to [ungoogled-software/contrib](https://github.com/ungoogled-software/contrib) or [our Wiki](https://github.com/ungoogled-software/ungoogled-chromium-wiki) instead.

If you are a developer of an **officially-supported platform**, be sure to check out the [Platform Repository Standards and Guidelines](repo_management.md).

List of contents:

* [How to help](#how-to-help)
* [Submitting changes](#submitting-changes)
* [Criteria for new features](#criteria-for-new-features)

### How to help

Generally, ungoogled-chromium needs contributors to help:

* Keep up-to-date with the latest stable Chromium, and any problematic changes in the new version that needs modification.
* Help with issues marked with the `help wanted` tag (usually either questions for other users, or request for help from other developers)
* Review Pull Requests from other contributors
* Implement feature requests ("enhancements" in the Issue Tracker), large or small.
* Implement issues marked with the `backlog` tag (that are closed).
	* If it requires new code, please read through the [Submitting changes](#submitting-changes) section below.

In addition, anyone is free to help others in need of support in the Issue Tracker.

If there are fixes, tweaks, or additions you want to make, continue onto the following section.

### Submitting changes

Please submit all changes via Pull Requests.

Guidelines:

* You are welcome to submit minor changes, such as bug fixes, documentation fixes, and tweaks.
* If your change has an associated issue, please let others know that you are working on it.
* If you want to submit a new feature, please read through the [Criteria for new features](#criteria-for-new-features) below.
* When in doubt about the acceptance of a change, you are welcome to ask via an issue first.

### Criteria for new features

1. New features should not detract from the default Chromium experience, unless it falls under the project's main objectives (i.e. removing Google integration and enhancing privacy).

    * For larger features, please propose them via an issue first.

2. New features should live behind a setting that is **off by default**.

    * Settings are usually added via a command-line flag and `chrome://flags` entries. See [the relevant section in docs/developing.md](developing.md#adding-command-line-flags-and-chromeflags-options) for more information.
    * Unless there are significant benefits, adding the setting to `chrome://settings` is *not recommended* due to the additional maintenance required (caused by the infrastructure that backs preferences).

**NOTE**: In the event that the codebase changes significantly for a non-essential patch (i.e. a patch that does not contribute to the main objectives of ungoogled-chromium), it will be removed until someone updates it.
