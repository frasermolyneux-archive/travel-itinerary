# Retained Google capability and workload retirement

The Google project `gcp-mx-io-travel-itinerary`, billing association and bootstrap
federation belong to the retained Trip Side Kick capability. Do not delete the
project or disable its Maps/Places APIs.

Both legacy environment states may own the same project-wide API enablements.
The `removed` blocks preserve those services during a **normal apply only**:
Terraform 1.17.0 ignores that protection during `plan -destroy`. This behavior
was verified using isolated built-in resources before writing the guard.

## Required sequence

1. Apply Trip Side Kick's reviewed Production API/key ownership, restricted to
   the four Trip Side Kick hostnames. Verify the rotated key securely and its
   delivery to the retained Production vault before revoking any legacy key.
2. Run **Forget Retained Google API Ownership** on `main`. It checks the enabled
   APIs and exact replacement key restrictions, then runs both Development and
   Production sequentially using their existing identities and backends.
   The exceptional targeted plans may contain only the two exact `forget`
   actions and no output changes. The saved-plan apply verifies its source,
   toolchain and environment; the final state-list check rejects any remaining
   Google service resources. Repeating an already completed handover is safe.
3. After the new host, authentication and restore acceptance pass, run the
   approved legacy environment destroys. Both destroy entry points validate
   their saved plans before applying: only the legacy Google key can be
   deleted, never API enablements, the project or other Google capabilities.
   Inspect Azure residuals, including automatically recreated alert rules.
4. Follow `platform-workloads/docs/decommissioning.md`: destroy this repository's
   own stacks before removing its deployment identities or state storage;
   detach exactly `github_repository.workload["travel-itinerary"]` using the
   supported **Decommission State Rm** workflow before deleting the catalog JSON.
   Review/apply the catalog removal, then transfer the repository to
   `frasermolyneux-archive`.
5. Remove the legacy repository's Google trust only after its stack operations
   finish. Preserve Trip Side Kick and platform federation.

No Google key string or Terraform state should be printed or attached to an
issue, PR discussion or job summary. The checks inspect metadata or read a
plan through a pipe and emit only credential-free diagnostics.
