"""Diffbot tool provider. Credential checks call the Account API only."""

from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools.client import DiffbotError
from tools.common import make_client


class DiffbotProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            make_client(credentials).validate_token()
        except DiffbotError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc
        except Exception as exc:
            raise ToolProviderCredentialValidationError(
                "Could not validate the Diffbot token."
            ) from exc
