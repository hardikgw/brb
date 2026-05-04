from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from stacks.naming import Naming


class SiteApi(Construct):
    """REST API fronting the signup + altcha-challenge Lambdas.

    Routes (all under stage `/prod`):
      GET  /altcha   ->  altcha challenge function
      POST /signup   ->  signup function

    CORS preflight is handled by API Gateway itself (via
    `default_cors_preflight_options`), so the Lambdas don't need to handle
    OPTIONS requests.
    """

    CORE_NAME = "api"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        naming: Naming,
        signup_function: lambda_.IFunction,
        altcha_function: lambda_.IFunction,
        allowed_origins: list[str] | None = None,
    ) -> None:
        super().__init__(scope, construct_id)

        cors = apigw.CorsOptions(
            allow_origins=allowed_origins or apigw.Cors.ALL_ORIGINS,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
        )

        self.api = apigw.RestApi(
            self,
            "RestApi",
            rest_api_name=naming.build(self.CORE_NAME),
            deploy_options=apigw.StageOptions(stage_name="prod"),
            default_cors_preflight_options=cors,
        )

        altcha = self.api.root.add_resource("altcha")
        altcha.add_method("GET", apigw.LambdaIntegration(altcha_function))

        signup = self.api.root.add_resource("signup")
        signup.add_method("POST", apigw.LambdaIntegration(signup_function))
