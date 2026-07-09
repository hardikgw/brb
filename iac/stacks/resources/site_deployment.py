from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3_deployment
from constructs import Construct


class SiteDeployment(Construct):
    """Uploads the static site files to the destination bucket.

    `prune=False` is intentional: the bucket pre-exists and may hold objects
    managed outside this stack, so we only add/overwrite — never delete.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket: s3.IBucket,
        source_path: str,
        exclude: list[str],
    ) -> None:
        super().__init__(scope, construct_id)

        self.deployment = s3_deployment.BucketDeployment(
            self,
            "Deployment",
            destination_bucket=bucket,
            sources=[s3_deployment.Source.asset(source_path, exclude=exclude)],
            prune=False,
            memory_limit=1024,
        )
