#!/bin/sh
# Fast-forward every git repo directly under $1 (the agents' working directory).
# Managed by Ansible; run by homelab-repos-pull.timer as the paperclip user.
set -u
rc=0
for d in "$1"/*/; do
  [ -d "$d/.git" ] || continue
  git -C "$d" pull --ff-only --quiet || { echo "pull failed: $d" >&2; rc=1; }
done
exit $rc
