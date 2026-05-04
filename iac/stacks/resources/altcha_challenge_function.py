from aws_cdk import Duration
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from stacks.naming import Naming


_RUNTIMES: dict[str, lambda_.Runtime] = {
    "python3.12": lambda_.Runtime.PYTHON_3_12,
    "python3.11": lambda_.Runtime.PYTHON_3_11,
    "python3.10": lambda_.Runtime.PYTHON_3_10,
}


class AltchaChallengeFunction(Construct):
    """Lambda that issues HMAC-signed ALTCHA proof-of-work challenges."""

    CORE_NAME = "altcha-verify-lambda"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        naming: Naming,
        runtime: str,
        handler: str,
        code_path: str,
        timeout_seconds: int,
        memory_mb: int,
        env_vars: dict[str, str],
    ) -> None:
        super().__init__(scope, construct_id)

        if runtime not in _RUNTIMES:
            raise ValueError(
                f"Unsupported runtime '{runtime}'. "
                f"Supported: {sorted(_RUNTIMES)}"
            )

        self.function = lambda_.Function(
            self,
            "Function",
            function_name=naming.build(self.CORE_NAME),
            runtime=_RUNTIMES[runtime],
            handler=handler,
            code=lambda_.Code.from_asset(code_path),
            timeout=Duration.seconds(timeout_seconds),
            memory_size=memory_mb,
            environment=env_vars,
        )
