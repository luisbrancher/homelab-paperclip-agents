## Hard rules (test phase, read-only)
- Work only on the ticket assigned to you. Do not start work or open tickets on your own.
- Do not change anything: no kubectl apply/delete, terraform apply, ansible-playbook, ssh, git push, merges.
- Never read or print secrets (Ansible Vault, tokens, .env, Cloudflare keys).
- Every finding needs evidence (query, log line, file:line, diff). No evidence = say "unverified".
- Proposed changes go in your report as a diff/PR description for the board (Luis) to approve. Reports in pt-BR.
- Report format: Status | What happened | Evidence | Next step | Needs your decision?
