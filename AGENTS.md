# AGENTS.md — travel-itinerary

Execution brief for the GitHub Copilot coding agent (and any [agents.md](https://agents.md)-compatible agent) running in a cloud runner. For local/IDE orientation, see `.github/copilot-instructions.md`.

## Stack

ASP.NET Core 10 Razor Pages app (`src/MX.TravelItinerary.Web`) for sharing travel itineraries. Entra ID auth (Microsoft.Identity.Web), Azure Table Storage (`DefaultAzureCredential`), Google Maps route views, a PWA service worker for offline access, and Terraform-managed Azure hosting.

## Build, test, format

```pwsh
dotnet build src/MX.TravelItinerary.slnx
dotnet run --project src/MX.TravelItinerary.Web/MX.TravelItinerary.Web.csproj
dotnet format src/MX.TravelItinerary.slnx --verify-no-changes
```

The application startup smoke test runs with `dotnet test src/MX.TravelItinerary.slnx`; also validate manual UI/offline checks (see `docs/OFFLINE_SUPPORT.md`).

```pwsh
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform init -lockfile=readonly -backend-config=backends/dev.backend.hcl
terraform -chdir=terraform validate
terraform -chdir=terraform plan -var-file=tfvars/dev.tfvars
```

## Boundaries

- **Auth**: all Razor Pages require Entra ID except `/Index`, `/Error`, and `/Shares/View` (anonymous read-only share link) — conventions are wired in `Program.cs` (`AuthorizeFolder`/`AllowAnonymousToPage`). Don't add a page without confirming which convention applies.
- **Maps**: `GoogleMaps__ApiKey` is a Key Vault secret reference in Terraform, bound via `Options/GoogleMapsOptions.cs`. Never hardcode a key or log its value.
- **Shared trips**: `Pages/Shares/*` are anonymous, read-only views backed by the owner/slug checks in `Data/TableStorage/TableItineraryRepository.cs`. Keep them read-only; do not add mutation endpoints under `Shares`.
- **PWA/service worker**: `wwwroot/sw.js` is cache-first for static assets and network-first for pages. Bump `CACHE_VERSION` in `sw.js` whenever cached asset contents change, or clients will serve stale files. See `docs/OFFLINE_SUPPORT.md` for full behavior.
- **Vendored vs. maintained assets**: `wwwroot/lib/*` (bootstrap, jquery, jquery-validation, jquery-validation-unobtrusive) are vendored — do not hand-edit. Maintained app JS lives in `wwwroot/js/*.js` (`pwa.js`, `shared-trips.js`, `site.js`).
- **Data/secrets**: Azure Table Storage via `DefaultAzureCredential`; no client secrets, connection strings, or hardcoded subscription IDs/GUIDs. Local config uses `appsettings.Development.json`/user-secrets; production uses Key Vault references set by Terraform.
- **Terraform** (`terraform/`): App Service, Storage, DNS, Key Vault, Entra ID app registration, remote state from `platform-hosting`/`platform-monitoring`. Commit each root's `.terraform-version` and `.terraform.lock.hcl`. Select the exact root CLI pin before invoking Terraform; normal initialization uses `-lockfile=readonly`. Regenerate provider selections only in a reviewed dependency-update PR; never commit state, plans, or `.terraform/`.
- **Runtime/deployment**: target `net10.0` (pinned via `global.json`); Azure Linux Web App runtime stack `dotnet_version = "10.0"`. Deployment is handled by `deploy-dev.yml`/`deploy-prd.yml` — out of scope unless that is the explicit task.

## Do NOT

- Do not modify `.github/workflows/` (other than an explicitly requested workflow change), `version.json`, or `Directory.Build.props`.
- Do not introduce client secrets, connection strings, or hardcoded subscription IDs/GUIDs.
- Do not change app behavior, dependencies, target framework, public contracts, generated/vendored assets, Terraform providers, or deployment wiring unless that is the explicit task.


CI-only main pushes are excluded by deployment push-path filters before workflow concurrency; they do not enqueue or displace cloud/backend deployments. Automatic deployment requires a change to the workload inputs already declared by the deployment filters; scheduled maintenance and explicit workflow dispatch retain their existing behavior. A deployment-workflow-only change requires explicit dispatch to exercise cloud operations.
