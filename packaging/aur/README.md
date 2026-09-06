# AUR packaging for omarchy-feature-search

Two PKGBUILD variants are included:

| File | Package name | Source | When to use |
|---|---|---|---|
| `PKGBUILD` | `omarchy-feature-search` | release tarball (`v0.1.0` tag) | versioned releases |
| `PKGBUILD-git` | `omarchy-feature-search-git` | clones git HEAD | no tagging needed |

## Quick install (local, without AUR)

You can build and install the package right now on your own machine:

```fish
cd packaging/aur
makepkg -si PKGBUILD          # versioned
# or
makepkg -si PKGBUILD-git      # -git (clones latest)
```

`makepkg -si` builds the wheel, installs it into the system Python, drops the
`.desktop` entry + icon, and installs the package via pacman. After that the
app appears in the Super+Space launcher and `omarchy-feature-search` is on PATH.

## Publish to the AUR

### 1. Create an AUR account

Go to <https://aur.archlinux.org/register> and register. Then generate an SSH
key for AUR if you don't have one:

```fish
ssh-keygen -t ed25519 -C "your-email"
# upload the public key to AUR Account -> My Account -> SSH Public Key
```

### 2. Clone the empty AUR package

```fish
git clone ssh://aur@aur.archlinux.org/omarchy-feature-search.git aur-pkg
cd aur-pkg
```

### 3. Copy the PKGBUILD + assets into it

```fish
cp /path/to/ncomarchykb/packaging/aur/PKGBUILD .
cp /path/to/ncomarchykb/packaging/aur/omarchy-feature-search.desktop .
# Create a .SRCINFO (required by AUR)
makepkg --printsrcinfo > .SRCINFO
```

### 4. Commit and push to AUR

```fish
git add PKGBUILD omarchy-feature-search.desktop .SRCINFO
git commit -m "Initial import: omarchy-feature-search 0.1.0"
git push
```

### 5. Install from AUR

```fish
yay -S omarchy-feature-search
# or: paru -S omarchy-feature-search
```

## For the -git variant

Repeat steps 2-4 but clone `omarchy-feature-search-git` and use `PKGBUILD-git`
(renamed to `PKGBUILD`):

```fish
git clone ssh://aur@aur.archlinux.org/omarchy-feature-search-git.git aur-pkg-git
cd aur-pkg-git
cp /path/to/ncomarchykb/packaging/aur/PKGBUILD-git PKGBUILD
cp /path/to/ncomarchykb/packaging/aur/omarchy-feature-search.desktop .
makepkg --printsrcinfo > .SRCINFO
git add PKGBUILD omarchy-feature-search.desktop .SRCINFO
git commit -m "Initial import: omarchy-feature-search-git"
git push
```

## Important: the source URL must be publicly reachable

The `source=()` line in the PKGBUILD points at:

```
https://git.safehomelan.com/david/ncomarchykb
```

For public AUR, makepkg running on someone else's machine must be able to
download the source. Options:

1. **Mirror to GitHub** and update `url` + `source` to the GitHub URL
   (recommended for public AUR).
2. **Keep the LAN gitea** if this is a private/personal AUR or if the gitea is
   reachable from the target machines.
3. **Use the `-git` variant** with `git+https://` — simpler, no release
   tarballs to host.

## Updating after code changes

1. Tag a new release: `git tag v0.1.1 && git push origin v0.1.1`
2. Update `pkgver` in `PKGBUILD`
3. Rebuild `.SRCINFO`: `makepkg --printsrcinfo > .SRCINFO`
4. Commit + push to the AUR git repo

For `-git`: just push to AUR — `pkgver()` auto-derives from `git describe`.
