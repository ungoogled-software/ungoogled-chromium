---
name: Create an "Updating to Chromium x.x.x.x"
about: For letting the community track progress to a new stable Chromium
title: Updating to Chromium {{ env.VERSION }} on {{ env.PLATFORM }}
labels: update
assignees: ''

---

Chromium stable channel for {{ env.PLATFORM }} has been updated to a newer version: {{ env.VERSION }}.

If you are willing to work on updating the patches and lists, please leave a comment in this issue in order to facilitate better coordination and avoid wasted/duplicated efforts.

If you'd like to increase visibility of your progress or get early feedback/advice, consider creating a [Draft Pull Request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests#draft-pull-requests). Finally, make sure to reference this issue in your PR. Please make sure to read [/docs/developing.md](https://github.com/ungoogled-software/ungoogled-chromium/blob/master/docs/developing.md#updating-patches) for guidance.

Feel free to raise issues or questions throughout the process here. However, please refrain from asking for ETAs unless no visible progress has been made here or in the developer's PR for a while (e.g. 2 weeks).

{{ env.NOTIFY_MAINTAINERS }}
