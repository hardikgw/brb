from typing import Any

from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3_deployment
from constructs import Construct


class SiteRuntimeConfig(Construct):
    """Writes a runtime `config.json` to the site bucket.

    Lets the static page read deploy-time values (API URL, etc.) at runtime
    without regenerating the HTML. CDK tokens in `config` are resolved by a
    CloudFormation custom resource at deploy time, so values like
    `RestApi.url` substitute correctly.

    Uses its own `BucketDeployment` (not the static-file one) with
    `Cache-Control: no-store` so the file is never cached by browsers or
    CDNs.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket: s3.IBucket,
        config: dict[str, Any],
        filename: str = "config.json",
    ) -> None:
        super().__init__(scope, construct_id)

        self.deployment = s3_deployment.BucketDeployment(
            self,
            "Deployment",
            destination_bucket=bucket,
            sources=[s3_deployment.Source.json_data(filename, config)],
            prune=False,
            cache_control=[s3_deployment.CacheControl.no_store()],
            memory_limit=1024,
        )
