from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3_deployment
from constructs import Construct


class SiteDeployment(Construct):
    """Uploads the static site files to the destination bucket.

    `prune=False` is intentional: the bucket pre-exists and may hold objects
    managed outside this stack, so we only add/overwrite — never delete.

    The upload is split in two so each content class carries an explicit
    Cache-Control (S3 objects otherwise send none and CloudFront falls back
    to its default TTL): images are long-lived; pages/text must propagate
    within minutes. When `distribution` is provided, each deployment also
    issues a `/*` invalidation so changes are visible at the edge immediately.
    """

    PAGES_CACHE_CONTROL = "public, max-age=300, must-revalidate"
    IMAGES_CACHE_CONTROL = "public, max-age=2592000"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket: s3.IBucket,
        source_path: str,
        exclude: list[str],
        distribution: cloudfront.IDistribution | None = None,
    ) -> None:
        super().__init__(scope, construct_id)

        invalidation = (
            {"distribution": distribution, "distribution_paths": ["/*"]}
            if distribution is not None
            else {}
        )

        self.deployment = s3_deployment.BucketDeployment(
            self,
            "Deployment",
            destination_bucket=bucket,
            sources=[
                s3_deployment.Source.asset(
                    source_path, exclude=[*exclude, "images", "images/**"]
                )
            ],
            cache_control=[
                s3_deployment.CacheControl.from_string(self.PAGES_CACHE_CONTROL)
            ],
            prune=False,
            memory_limit=1024,
            **invalidation,
        )

        self.images = s3_deployment.BucketDeployment(
            self,
            "Images",
            destination_bucket=bucket,
            destination_key_prefix="images",
            sources=[
                s3_deployment.Source.asset(f"{source_path}/images", exclude=exclude)
            ],
            cache_control=[
                s3_deployment.CacheControl.from_string(self.IMAGES_CACHE_CONTROL)
            ],
            prune=False,
            memory_limit=1024,
            **invalidation,
        )
