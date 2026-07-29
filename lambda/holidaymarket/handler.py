import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_SES_FROM = os.environ["SES_FROM_ADDRESS"]
_SES_TO = os.environ["SES_TO_ADDRESS"]
_HMAC_KEY = os.environ["ALTCHA_HMAC_KEY"].encode()

_ses = boto3.client("ses")

_CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}

_REQUIRED_FIELDS = (
    "business_name",
    "contact_name",
    "phone",
    "email",
    "category",
    "products",
    "booth_days",
    "electricity",
    "social_permission",
    "printed_name",
    "signature",
)

_OPTIONAL_FIELDS = (
    "website",
    "facebook",
    "instagram",
    "category_other",
    "electricity_needs",
    "photo_links",
    "signature_date",
    "_source",
)

_LONG_FIELDS = {"products", "electricity_needs", "photo_links"}
_MAX_SHORT = 300
_MAX_LONG = 4000


def lambda_handler(event, context):
    body = event.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return _response(400, {"ok": False, "error": "invalid_json"})
    body = body or {}

    if body.get("_gotcha"):
        logger.info("Honeypot triggered, dropping application silently")
        return _response(200, {"ok": True})

    if not _verify_altcha(body.get("altcha")):
        return _response(403, {"ok": False, "error": "captcha_failed"})

    fields = {
        key: _clean(body.get(key), long=key in _LONG_FIELDS)
        for key in _REQUIRED_FIELDS + _OPTIONAL_FIELDS
    }

    missing = [key for key in _REQUIRED_FIELDS if not fields[key]]
    if missing:
        return _response(400, {"ok": False, "error": "missing_fields", "fields": missing})

    if "@" not in fields["email"]:
        return _response(400, {"ok": False, "error": "invalid_email"})

    if body.get("agreement") != "accepted":
        return _response(400, {"ok": False, "error": "agreement_required"})

    subject_name = re.sub(r"\s+", " ", fields["contact_name"]).strip()[:120]
    subject = f"BRB Holidaymarket Signup - {subject_name}"

    try:
        _ses.send_email(
            Source=_SES_FROM,
            Destination={"ToAddresses": [_SES_TO]},
            ReplyToAddresses=[fields["email"]],
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": _format_email(fields)}},
            },
        )
    except ClientError:
        logger.exception("SES send failed")
        return _response(502, {"ok": False, "error": "send_failed"})

    return _response(200, {"ok": True})


def _clean(value, *, long: bool = False) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[: _MAX_LONG if long else _MAX_SHORT]


def _format_email(f: dict) -> str:
    category = f["category"]
    if f["category_other"]:
        category = f"{category} — {f['category_other']}"

    electricity = f["electricity"]
    if f["electricity_needs"]:
        electricity = f"{electricity} — {f['electricity_needs']}"

    submitted = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return (
        "Backroom Brewery Holiday Market — Vendor Application\n"
        "=====================================================\n"
        "\n"
        "BUSINESS INFORMATION\n"
        f"  Business Name:  {f['business_name']}\n"
        f"  Owner/Contact:  {f['contact_name']}\n"
        f"  Phone:          {f['phone']}\n"
        f"  Email:          {f['email']}\n"
        f"  Website:        {f['website'] or '(not provided)'}\n"
        f"  Facebook:       {f['facebook'] or '(not provided)'}\n"
        f"  Instagram:      {f['instagram'] or '(not provided)'}\n"
        "\n"
        "VENDOR CATEGORY\n"
        f"  {category}\n"
        "\n"
        "PRODUCTS\n"
        f"  {f['products']}\n"
        "\n"
        "BOOTH SELECTION\n"
        f"  {f['booth_days']}\n"
        "\n"
        "BOOTH REQUIREMENTS\n"
        f"  Electricity: {electricity}\n"
        "\n"
        "PHOTO LINKS\n"
        f"  {f['photo_links'] or '(none provided — follow up by email)'}\n"
        "\n"
        "SOCIAL MEDIA PERMISSION\n"
        f"  {f['social_permission']}\n"
        "\n"
        "VENDOR AGREEMENT\n"
        "  All terms acknowledged: Yes\n"
        "\n"
        "SIGNATURE\n"
        f"  Printed Name: {f['printed_name']}\n"
        f"  Signature:    {f['signature']}\n"
        f"  Date:         {f['signature_date'] or '(not provided)'}\n"
        "\n"
        f"Source:    {f['_source'] or 'unknown'}\n"
        f"Submitted: {submitted}\n"
    )


def _verify_altcha(payload_b64) -> bool:
    if not payload_b64 or not isinstance(payload_b64, str):
        return False
    try:
        payload = json.loads(base64.b64decode(payload_b64).decode())
    except (ValueError, UnicodeDecodeError):
        return False

    try:
        algorithm = payload.get("algorithm", "SHA-256")
        salt = payload["salt"]
        number = payload["number"]
        challenge = payload["challenge"]
        signature = payload["signature"]
    except (KeyError, TypeError):
        return False

    if algorithm != "SHA-256":
        return False

    # `salt` carries an `?expires=<unix-seconds>` suffix issued by the
    # challenge endpoint. Reject expired solutions to prevent replay.
    if "?expires=" in salt:
        try:
            expires = int(salt.split("?expires=", 1)[1])
        except ValueError:
            return False
        if expires < int(time.time()):
            return False

    expected_challenge = hashlib.sha256(f"{salt}{number}".encode()).hexdigest()
    if not hmac.compare_digest(expected_challenge, challenge):
        return False

    expected_sig = hmac.new(_HMAC_KEY, expected_challenge.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, signature)


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": _CORS_HEADERS,
        "body": json.dumps(body),
    }
