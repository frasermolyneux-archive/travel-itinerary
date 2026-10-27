import copy
import unittest

from check_gcp_handover import HandoverError, PROJECT, SERVICES, validate_plan


def plan():
    return {
        "format_version": "1.2",
        "terraform_version": "1.17.0",
        "variables": {
            "environment": {"value": "prd"},
            "gcp_project_id": {"value": PROJECT},
        },
        "resource_changes": [
            {
                "address": address,
                "mode": "managed",
                "type": "google_project_service",
                "provider_name": "registry.terraform.io/hashicorp/google",
                "change": {
                    "actions": ["forget"],
                    "before": {"project": PROJECT, "service": service, "id": f"{PROJECT}/{service}"},
                    "after": None,
                },
            }
            for address, service in SERVICES.items()
        ],
    }


class HandoverTests(unittest.TestCase):
    def test_exact_forgets_and_idempotent_retries(self):
        for count in (0, 1, 2):
            with self.subTest(count=count):
                document = plan()
                document["resource_changes"] = document["resource_changes"][:count]
                self.assertEqual(validate_plan(document, "forget", "prd", "1.17.0"), count)

    def test_other_actions_cannot_mutate_resources(self):
        for action in ("create", "update", "delete", "read"):
            with self.subTest(action=action):
                document = plan()
                document["resource_changes"][0]["change"]["actions"] = [action]
                with self.assertRaises(HandoverError):
                    validate_plan(document, "forget", "prd", "1.17.0")

    def test_foreign_resource_provider_project_service_and_duplicates_fail(self):
        for key, value in (
            ("address", "google_project_service.unreviewed"),
            ("type", "google_project"),
            ("provider_name", "registry.terraform.io/example/google"),
            ("mode", "data"),
            ("project", "unreviewed-project"),
            ("service", "unreviewed.googleapis.com"),
            ("id", "unreviewed/service"),
            ("after", {}),
        ):
            with self.subTest(key=key):
                document = plan()
                resource = document["resource_changes"][0]
                target = resource["change"] if key == "after" else (
                    resource["change"]["before"] if key in ("project", "service", "id") else resource
                )
                target[key] = value
                with self.assertRaises(HandoverError):
                    validate_plan(document, "forget", "prd", "1.17.0")
        document = plan()
        document["resource_changes"].append(copy.deepcopy(document["resource_changes"][0]))
        with self.assertRaises(HandoverError):
            validate_plan(document, "forget", "prd", "1.17.0")

    def test_wrong_identity_outputs_or_incomplete_plans_fail(self):
        for update in (
            {"terraform_version": "1.15.8"},
            {"format_version": "2.0"},
            {"errored": True},
            {"deferred_changes": [{}]},
            {"output_changes": {"unexpected": {"actions": ["update"]}}},
            {"variables": {"environment": {"value": "dev"}, "gcp_project_id": {"value": PROJECT}}},
            {"variables": {"environment": {"value": "prd"}, "gcp_project_id": {"value": "foreign"}}},
        ):
            with self.subTest(update=update):
                document = plan()
                document.update(update)
                with self.assertRaises(HandoverError):
                    validate_plan(document, "forget", "prd", "1.17.0")

    def test_destroy_cannot_bypass_removed_lifecycle_protection(self):
        document = plan()
        for resource in document["resource_changes"]:
            resource["change"]["actions"] = ["delete"]
        with self.assertRaises(HandoverError):
            validate_plan(document, "destroy", "prd", "1.17.0")

    def test_only_legacy_google_key_can_be_destroyed(self):
        document = plan()
        resource = document["resource_changes"][0]
        resource.update(address="google_apikeys_key.maps", type="google_apikeys_key")
        resource["change"]["actions"] = ["delete"]
        document["resource_changes"] = [resource]
        self.assertEqual(validate_plan(document, "destroy", "prd", "1.17.0"), 0)
        for key, value in (("address", "google_apikeys_key.replacement"), ("type", "google_project")):
            with self.subTest(key=key):
                modified = copy.deepcopy(document)
                modified["resource_changes"][0][key] = value
                with self.assertRaises(HandoverError):
                    validate_plan(modified, "destroy", "prd", "1.17.0")

    def test_destroy_rejects_recreation_but_accepts_legacy_azure_deletion(self):
        document = plan()
        resource = document["resource_changes"][0]
        resource.update(
            address="azurerm_linux_web_app.app",
            type="azurerm_linux_web_app",
            provider_name="registry.terraform.io/hashicorp/azurerm",
        )
        document["resource_changes"] = [resource]
        for actions, accepted in ((["delete"], True), (["create"], False), (["delete", "create"], False)):
            with self.subTest(actions=actions):
                resource["change"]["actions"] = actions
                if accepted:
                    self.assertEqual(validate_plan(document, "destroy", "prd", "1.17.0"), 0)
                else:
                    with self.assertRaises(HandoverError):
                        validate_plan(document, "destroy", "prd", "1.17.0")


if __name__ == "__main__":
    unittest.main()
