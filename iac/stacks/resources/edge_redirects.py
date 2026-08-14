from pathlib import Path

from aws_cdk import aws_cloudfront as cloudfront
from constructs import Construct

from stacks.naming import Naming


class EdgeRedirects(Construct):
    """CloudFront Function for host + trailing-slash canonicalization.

    301s apex -> www and strips trailing slashes (/beers/ -> /beers), which
    also retires the manually uploaded slash-key objects (e.g. the literal
    `holidaymarket/` key — delete it with `aws s3api delete-object` once the
    function is attached).

    The distribution itself pre-exists outside this stack, so deploying only
    creates/updates and publishes the function. Attaching it is a one-time
    manual step: CloudFront console -> the distribution -> default behavior ->
    Function associations -> Viewer request -> this function. The association
    survives later function-code updates deployed from here.
    """

    CORE_NAME = "edge-redirects"

    def __init__(self, scope: Construct, construct_id: str, *, naming: Naming) -> None:
        super().__init__(scope, construct_id)

        code_path = Path(__file__).resolve().parents[2] / "cloudfront" / "redirects.js"
        self.function = cloudfront.Function(
            self,
            "Function",
            function_name=naming.build(self.CORE_NAME),
            code=cloudfront.FunctionCode.from_file(file_path=str(code_path)),
            runtime=cloudfront.FunctionRuntime.JS_2_0,
            comment="301 apex->www and strip trailing slashes for backroombrewery.com",
        )
