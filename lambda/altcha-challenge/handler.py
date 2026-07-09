import hashlib
import hmac
import json
import os
import secrets
import time

_HMAC_KEY = os.environ["ALTCHA_HMAC_KEY"].encode()
_MAX_NUMBER = int(os.environ.get("ALTCHA_MAX_NUMBER", "50000"))
_EXPIRES_SECONDS = int(os.environ.get("ALTCHA_EXPIRES_SECONDS", "600"))

_CORS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Cache-Control": "no-store",
}


def lambda_handler(event, context):
    expires_at = int(time.time()) + _EXPIRES_SECONDS
    salt = f"{secrets.token_hex(12)}?expires={expires_at}"
    number = secrets.randbelow(_MAX_NUMBER)
    challenge = hashlib.sha256(f"{salt}{number}".encode()).hexdigest()
    signature = hmac.new(_HMAC_KEY, challenge.encode(), hashlib.sha256).hexdigest()
    return {
        "statusCode": 200,
        "headers": _CORS,
        "body": json.dumps({
            "algorithm": "SHA-256",
            "challenge": challenge,
            "maxnumber": _MAX_NUMBER,
            "salt": salt,
            "signature": signature,
        }),
    }

