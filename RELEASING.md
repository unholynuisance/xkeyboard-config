# How to make a xkeyboard-config release

### Prerequisites

- Have write access to xkeyboard-config Git repositories.

### Steps

#### Prepare the release

- [ ] Ensure there is no issue in the tracker blocking the release. Make sure
  they have their milestone set to the relevant release and the relevant tag
  “critical”.

- [ ] Ensure all items in the current milestone are processed. Remaining items
  must be *explicitly* postponed by changing their milestone.

- [ ] Create a release branch: `git checkout -b release/MAJOR.MINOR master`

- [ ] Bump the `version` in `meson.build`.

- [ ] Run `meson dist -C build` to make sure the release is good to go.

- [ ] Commit `git commit -m 'New version MAJOR.MINOR'`.

- [ ] Create a pull request using this template and ensure *all* CI is green.

- [ ] Merge the pull request.

- [ ] Tag `git switch master && git pull && git tag --annotate -m xkeyboard-config-<MAJOR.MINOR> xkeyboard-config-<MAJOR.MINOR>`.

- [ ] Push the tag `git push origin xkeyboard-config-<MAJOR.MINOR>`.

#### Send announcement email to xorg-announce

- [ ] Send an email to the xorg-announce@lists.x.org mailing list, using this template:

```
Subject: [ANNOUNCE] xkeyboard-config MAJOR.MINOR

<NEWS & comments for this release>

Git tag:
--------

git tag: xkeyboard-config-<MAJOR.MINOR>
git commit: <git commit sha>

<YOUR NAME>
```