from aws_cdk import Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from stacks.naming import Naming


_RUNTIMES: dict[str, lambda_.Runtime] = {
    "python3.12": lambda_.Runtime.PYTHON_3_12,
    "python3.11": lambda_.Runtime.PYTHON_3_11,
    "python3.10": lambda_.Runtime.PYTHON_3_10,
}


class SignupFunction(Construct):
    """Lambda backing the site's signup form.

    Sends an SES notification to a configured address. Caller must pass the
    ARNs of the SES identities the function is allowed to send from/to.
    """

    CORE_NAME = "signup-lambda"

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
        ses_identity_arns: list[str],
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

        self.function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=ses_identity_arns,
            )
        )
