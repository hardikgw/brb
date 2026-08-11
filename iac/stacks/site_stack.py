import os
import secrets
from pathlib import Path

import aws_cdk as cdk
from constructs import Construct

from stacks.naming import Naming
from stacks.resources.altcha_challenge_function import AltchaChallengeFunction
from stacks.resources.api import SiteApi
from stacks.resources.email_identity import SignupEmailIdentities
from stacks.resources.fbevents_function import FacebookEventsFunction
from stacks.resources.holidaymarket_function import HolidayMarketFunction
from stacks.resources.site_alias_objects import SiteAliasObjects
from stacks.resources.signup_function import SignupFunction
from stacks.resources.site_bucket import SiteBucket
from stacks.resources.site_deployment import SiteDeployment
from stacks.resources.site_runtime_config import SiteRuntimeConfig


# Local cache for the auto-generated dev HMAC key. Gitignored. Regenerate by
# deleting this file. For prod/CI, set ALTCHA_HMAC_KEY in the environment.
_DEV_KEY_CACHE = Path(__file__).resolve().parents[1] / ".altcha-hmac-key"


def _resolve_altcha_hmac_key(config_value: str | None) -> str:
    env_value = os.environ.get("ALTCHA_HMAC_KEY")
    if env_value:
        return env_value
    if config_value:
        return config_value
    if _DEV_KEY_CACHE.exists():
        cached = _DEV_KEY_CACHE.read_text().strip()
        if cached:
            return cached
    new_key = secrets.token_hex(32)
    _DEV_KEY_CACHE.write_text(new_key)
    print(
        f"[altcha] No ALTCHA_HMAC_KEY env var or altcha.hmacKey in config — "
        f"generated a dev key and cached at {_DEV_KEY_CACHE} (gitignored). "
        "Override with ALTCHA_HMAC_KEY for prod/CI."
    )
    return new_key


class SiteStack(cdk.Stack):
    CORE_NAME = "static-site"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: dict,
        naming: Naming,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        naming.apply_default_tags(self)

        site_bucket = SiteBucket(
            self,
            "SiteBucket",
            existing_bucket_name=config["existingBucketName"],
        )

        iac_root = Path(__file__).resolve().parents[1]
        project_root = iac_root.parent
        source_path = (iac_root / config["siteSourcePath"]).resolve()

        SiteDeployment(
            self,
            "SiteDeployment",
            bucket=site_bucket.bucket,
            source_path=str(source_path),
            exclude=config["siteExclude"],
        )

        SiteAliasObjects(
            self,
            "SiteAliasObjects",
            bucket=site_bucket.bucket,
            aliases={
                "holidaymarket": str(source_path / "holidaymarket" / "index.html"),
                "story": str(source_path / "story" / "index.html"),
                "taproom": str(source_path / "taproom" / "index.html"),
                "events": str(source_path / "events" / "index.html"),
                "visit": str(source_path / "visit" / "index.html"),
                "connect": str(source_path / "connect" / "index.html"),
                "beers": str(source_path / "beers" / "index.html"),
                "food": str(source_path / "food" / "index.html"),
                "private-events": str(source_path / "private-events" / "index.html"),
                "faq": str(source_path / "faq" / "index.html"),
                "farm": str(source_path / "farm" / "index.html"),
            },
        )

        ses_cfg = config["ses"]
        hm_cfg = config["holidayMarket"]
        hm_to_address = hm_cfg.get("toAddress") or ses_cfg["toAddress"]
        verify_emails = list({
            *(ses_cfg.get("verifyEmails") or []),
            ses_cfg["fromAddress"],
            ses_cfg["toAddress"],
            hm_to_address,
        })
        identities = SignupEmailIdentities(
            self,
            "EmailIdentities",
            emails=verify_emails,
        )

        altcha_cfg = config["altcha"]
        hmac_key = _resolve_altcha_hmac_key(altcha_cfg.get("hmacKey"))
        altcha_env = {
            "ALTCHA_HMAC_KEY": hmac_key,
            "ALTCHA_MAX_NUMBER": str(altcha_cfg.get("maxNumber", 50000)),
            "ALTCHA_EXPIRES_SECONDS": str(altcha_cfg.get("expiresSeconds", 600)),
        }

        challenge_cfg = altcha_cfg["challenge"]
        challenge = AltchaChallengeFunction(
            self,
            "AltchaChallengeFunction",
            naming=naming,
            runtime=challenge_cfg["runtime"],
            handler=challenge_cfg["handler"],
            code_path=str((project_root / challenge_cfg["codePath"]).resolve()),
            timeout_seconds=challenge_cfg["timeoutSeconds"],
            memory_mb=challenge_cfg["memoryMb"],
            env_vars={**(challenge_cfg.get("envVars") or {}), **altcha_env},
        )

        lambda_cfg = config["lambda"]
        code_path = (project_root / lambda_cfg["codePath"]).resolve()
        signup = SignupFunction(
            self,
            "SignupFunction",
            naming=naming,
            runtime=lambda_cfg["runtime"],
            handler=lambda_cfg["handler"],
            code_path=str(code_path),
            timeout_seconds=lambda_cfg["timeoutSeconds"],
            memory_mb=lambda_cfg["memoryMb"],
            env_vars={
                **(lambda_cfg.get("envVars") or {}),
                "SES_FROM_ADDRESS": ses_cfg["fromAddress"],
                "SES_TO_ADDRESS": ses_cfg["toAddress"],
                "ALTCHA_HMAC_KEY": hmac_key,
            },
            ses_identity_arns=identities.identity_arns,
        )

        hm_lambda_cfg = hm_cfg["lambda"]
        holidaymarket = HolidayMarketFunction(
            self,
            "HolidayMarketFunction",
            naming=naming,
            runtime=hm_lambda_cfg["runtime"],
            handler=hm_lambda_cfg["handler"],
            code_path=str((project_root / hm_lambda_cfg["codePath"]).resolve()),
            timeout_seconds=hm_lambda_cfg["timeoutSeconds"],
            memory_mb=hm_lambda_cfg["memoryMb"],
            env_vars={
                **(hm_lambda_cfg.get("envVars") or {}),
                "SES_FROM_ADDRESS": ses_cfg["fromAddress"],
                "SES_TO_ADDRESS": hm_to_address,
                "ALTCHA_HMAC_KEY": hmac_key,
            },
            ses_identity_arns=identities.identity_arns,
        )

        fb_cfg = config["facebook"]
        fb_token = os.environ.get("FB_PAGE_TOKEN") or fb_cfg.get("pageToken") or ""
        if not fb_token:
            print(
                "[facebook] No FB_PAGE_TOKEN env var or facebook.pageToken in "
                "config — GET /fbevents will return an empty list until one is set."
            )
        fb_lambda_cfg = fb_cfg["lambda"]
        fbevents = FacebookEventsFunction(
            self,
            "FacebookEventsFunction",
            naming=naming,
            runtime=fb_lambda_cfg["runtime"],
            handler=fb_lambda_cfg["handler"],
            code_path=str((project_root / fb_lambda_cfg["codePath"]).resolve()),
            timeout_seconds=fb_lambda_cfg["timeoutSeconds"],
            memory_mb=fb_lambda_cfg["memoryMb"],
            env_vars={
                **(fb_lambda_cfg.get("envVars") or {}),
                "FB_PAGE_ID": str(fb_cfg.get("pageId") or ""),
                "FB_PAGE_TOKEN": fb_token,
                "FB_GRAPH_VERSION": str(fb_cfg.get("graphVersion", "v21.0")),
                "FB_CACHE_SECONDS": str(fb_cfg.get("cacheSeconds", 1800)),
                "FB_EVENTS_LIMIT": str(fb_cfg.get("eventsLimit", 10)),
            },
        )

        api_cfg = config.get("api") or {}
        site_api = SiteApi(
            self,
            "Api",
            naming=naming,
            signup_function=signup.function,
            altcha_function=challenge.function,
            holidaymarket_function=holidaymarket.function,
            fbevents_function=fbevents.function,
            allowed_origins=api_cfg.get("allowedOrigins"),
        )

        SiteRuntimeConfig(
            self,
            "SiteRuntimeConfig",
            bucket=site_bucket.bucket,
            config={
                "apiBaseUrl": site_api.api.url,
                "altchaChallengeUrl": site_api.api.url_for_path("/altcha"),
                "signupUrl": site_api.api.url_for_path("/signup"),
                "holidayMarketUrl": site_api.api.url_for_path("/holidaymarket"),
                "fbEventsUrl": site_api.api.url_for_path("/fbevents"),
            },
        )

        cdk.CfnOutput(self, "ApiBaseUrl", value=site_api.api.url)
        cdk.CfnOutput(self, "AltchaChallengeUrl", value=site_api.api.url_for_path("/altcha"))
        cdk.CfnOutput(self, "SignupUrl", value=site_api.api.url_for_path("/signup"))
        cdk.CfnOutput(self, "HolidayMarketUrl", value=site_api.api.url_for_path("/holidaymarket"))
        cdk.CfnOutput(self, "FbEventsUrl", value=site_api.api.url_for_path("/fbevents"))
