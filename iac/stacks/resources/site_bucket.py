from aws_cdk import aws_s3 as s3
from constructs import Construct


class SiteBucket(Construct):
    """References an S3 bucket that already exists outside this stack."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        existing_bucket_name: str,
    ) -> None:
        super().__init__(scope, construct_id)
        self.bucket: s3.IBucket = s3.Bucket.from_bucket_name(
            self, "Bucket", existing_bucket_name
        )
