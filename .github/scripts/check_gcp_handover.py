"""Fail closed before forgetting retained APIs or destroying the legacy stack."""

import argparse
import json
from pathlib import Path
import sys


PROJECT = "gcp-mx-io-travel-itinerary"
SERVICES = {
    "google_project_service.maps_backend": "maps-backend.googleapis.com",
    "google_project_service.places_api": "places.googleapis.com",
}


class HandoverError(Exception):
    """A safe diagnostic that never includes a plan or credential value."""


def validate_plan(plan, operation, environment, version):
    variables = plan.get("variables", {})
    if (
        environment not in ("dev", "prd")
        or plan.get("terraform_version") != version
        or not plan.get("format_version", "").startswith("1.")
        or variables.get("environment", {}).get("value") != environment
        or variables.get("gcp_project_id", {}).get("value") != PROJECT
        or plan.get("errored")
        or plan.get("deferred_changes")
    ):
        raise HandoverError("Plan identity, version or completeness differs from the reviewed contract.")
    if operation not in ("forget", "destroy"):
        raise HandoverError("Unsupported handover operation.")

    forgotten = set()
    for resource in plan.get("resource_changes", []):
        actions = resource.get("change", {}).get("actions", [])
        if actions == ["no-op"]:
            continue
        address = resource.get("address")
        before = resource.get("change", {}).get("before") or {}
        if operation == "forget":
            service = SERVICES.get(address)
            if (
                service is None
                or address in forgotten
                or resource.get("type") != "google_project_service"
                or resource.get("mode") != "managed"
                or resource.get("provider_name") != "registry.terraform.io/hashicorp/google"
                or actions != ["forget"]
                or before.get("project") != PROJECT
                or before.get("service") != service
                or before.get("id") != f"{PROJECT}/{service}"
                or resource["change"].get("after") is not None
            ):
                raise HandoverError("Handover plan contains more than the exact retained API forget actions.")
            forgotten.add(address)
        else:
            if resource.get("mode") == "data" and actions == ["read"]:
                continue
            if actions != ["delete"]:
                raise HandoverError("Retirement plan contains a non-destruction resource change.")
            if resource.get("provider_name") == "registry.terraform.io/hashicorp/google" and (
                address != "google_apikeys_key.maps"
                or resource.get("type") != "google_apikeys_key"
                or before.get("project") != PROJECT
            ):
                raise HandoverError("Retained Google resources remain in state; run the API handover first.")

    if operation == "forget" and any(
        change.get("actions") != ["no-op"]
        for change in plan.get("output_changes", {}).values()
    ):
        raise HandoverError("Handover plan unexpectedly changes stack outputs.")
    return len(forgotten)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("forget", "destroy"))
    parser.add_argument("--environment", required=True, choices=("dev", "prd"))
    arguments = parser.parse_args()
    version = (
        Path(__file__).resolve().parents[2] / "terraform" / ".terraform-version"
    ).read_text(encoding="ascii").strip()
    try:
        count = validate_plan(json.load(sys.stdin), arguments.operation, arguments.environment, version)
    except (HandoverError, ValueError, TypeError, KeyError) as error:
        message = str(error) if isinstance(error, HandoverError) else "Plan JSON could not be validated."
        print(message, file=sys.stderr)
        return 1
    print(f"Verified {arguments.operation} plan for {arguments.environment}; retained API forgets: {count}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
