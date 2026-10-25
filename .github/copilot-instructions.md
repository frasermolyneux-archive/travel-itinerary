# Copilot Instructions

- **Stack & auth**: ASP.NET Core 10 Razor Pages (`src/MX.TravelItinerary.Web`) with Microsoft.Identity.Web. All pages require Entra ID except `Index`, `Error`, and `/Shares/View` read-only shares. Auth cookie lasts seven days with sliding renewal.
- **Data**: Azure Table Storage via `TableServiceClient` + `DefaultAzureCredential`. Settings live in `appsettings*.json` and `Options/StorageOptions.cs`; prefer managed identity. `Data/TableStorage/TableItineraryRepository.cs` enforces owner checks, normalizes emails/slugs, and logs allow/deny decisions.
- **Models & routing**: Immutable records/enums in `Data/Models/ItineraryModels.cs`. Custom routes for `trips/{tripSlug}`, cost summary, and route map are wired in `Program.cs`, which also rewrites `/trips` to `/Trips/Index`.
- **PWA/offline**: Service worker (`wwwroot/sw.js`), manifest, and helpers in `wwwroot/js/pwa.js` support caching, manual offline toggle, and manual sync; fallback page at `wwwroot/offline.html`. See `docs/OFFLINE_SUPPORT.md` for behavior and testing notes.
- **UI assets**: Static assets under `wwwroot/`; Bootstrap + custom CSS/JS. Currency options and aliases live in `Infrastructure/CurrencyCatalog.cs`.
- **Configuration**: `appsettings.json` + `appsettings.Development.json` hold `AzureAd`, `Storage`, `ApplicationInsights`, `GoogleMaps:ApiKey`. Keep secrets out of source; use user-secrets (ID in csproj) locally.
- **Local dev loop**: `dotnet build src/MX.TravelItinerary.slnx` then `dotnet run --project src/MX.TravelItinerary.Web/MX.TravelItinerary.Web.csproj`. Ensure `Storage:TableEndpoint` and Entra settings are present so `DefaultAzureCredential` works.
- **Testing**: No automated tests today; rely on manual UI flows and offline checks (toggle offline in browser devtools, verify cache updates/service worker refresh).
- **Infra**: Terraform under `terraform/` builds App Service, storage, DNS, identities, monitoring (per-environment tfvars/backends). GitHub Actions workflows cover build/test, codequality, PR verify, deploy-dev/prd, destroy-development/environment, dependabot-automerge, and copilot-setup-steps.
- **Gotchas**: Keep everything ASCII. Service worker cache busting relies on updating `sw.js` cache name when assets change. DefaultAzureCredential needs either local Entra login or managed identity in Azure.

## Terraform toolchain

Commit each root's `.terraform-version` and `.terraform.lock.hcl`. Select the exact root CLI pin before invoking Terraform; normal initialization uses `-lockfile=readonly`. Regenerate provider selections only in a reviewed dependency-update PR; never commit state, plans, or `.terraform/`.
