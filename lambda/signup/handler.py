import base64
import hashlib
import hmac
import json
import logging
import os
import time

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


def lambda_handler(event, context):
    body = event.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return _response(400, {"ok": False, "error": "invalid_json"})
    body = body or {}

    if body.get("_gotcha"):
        logger.info("Honeypot triggered, dropping signup silently")
        return _response(200, {"ok": True})

    if not _verify_altcha(body.get("altcha")):
        return _response(403, {"ok": False, "error": "captcha_failed"})

    email = (body.get("email") or "").strip()
    if not email or "@" not in email:
        return _response(400, {"ok": False, "error": "invalid_email"})

    name = (body.get("name") or "").strip() or "(no name given)"
    message = (body.get("message") or "").strip() or "(no message)"
    source = body.get("_source") or "unknown"

    text = (
        "New message from the web\n"
        "---------------------------\n"
        f"Email:   {email}\n"
        f"Name:    {name}\n"
        f"Source:  {source}\n"
        f"Message: {message}\n"
    )

    try:
        _ses.send_email(
            Source=_SES_FROM,
            Destination={"ToAddresses": [_SES_TO]},
            ReplyToAddresses=[email],
            Message={
                "Subject": {"Data": f"New signup: {email}"},
                "Body": {"Text": {"Data": text}},
            },
        )
    except ClientError:
        logger.exception("SES send failed")
        return _response(502, {"ok": False, "error": "send_failed"})

    return _response(200, {"ok": True})


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
