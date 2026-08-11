from pathlib import Path

from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3_deployment
from constructs import Construct


class SiteAliasObjects(Construct):
    """Uploads extensionless "pretty URL" copies of subdirectory pages.

    The site is served by CloudFront with the bucket's REST endpoint as the
    origin, which has no directory-index behavior: `/holidaymarket` does not
    resolve to `holidaymarket/index.html` (only the root path gets
    `index.html` via CloudFront's default root object). This construct
    re-uploads each page's HTML at the bare key so the pretty URL serves the
    page directly.

    `prune=False` for the same reason as SiteDeployment: the bucket is shared
    and pre-existing.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket: s3.IBucket,
        aliases: dict[str, str],
    ) -> None:
        super().__init__(scope, construct_id)

        sources = [
            s3_deployment.Source.data(
                key, Path(file_path).read_text(encoding="utf-8")
            )
            for key, file_path in aliases.items()
        ]

        self.deployment = s3_deployment.BucketDeployment(
            self,
            "Deployment",
            destination_bucket=bucket,
            sources=sources,
            prune=False,
            content_type="text/html; charset=utf-8",
            memory_limit=1024,
        )
