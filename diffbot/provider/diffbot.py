"""Diffbot tool provider. Credential checks call the Account API only."""

from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools.client import DiffbotError
from tools.sdk import make_client, mapped_errors, verify_token


class DiffbotProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            client = make_client(credentials)
            with client, mapped_errors(client):
                # verify_token() never hands back the account payload (it contains the token).
                valid = verify_token(client)
            if not valid:
                raise DiffbotError("Invalid or unauthorized Diffbot token.")
        except DiffbotError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc
        except Exception as exc:
            raise ToolProviderCredentialValidationError(
                "Could not validate the Diffbot token."
            ) from exc
