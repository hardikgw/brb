import re

from aws_cdk import ArnFormat, Stack
from aws_cdk import aws_ses as ses
from constructs import Construct


class SignupEmailIdentities(Construct):
    """SES email identities the signup Lambda needs verified.

    In the SES sandbox both sender and recipient must be verified, so the same
    list of identities is used to scope `ses:SendEmail` on the Lambda role.
    Identities of type `email` trigger SES to send a click-to-verify link to
    each address — the link must be clicked before SES will accept sends.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        emails: list[str],
    ) -> None:
        super().__init__(scope, construct_id)

        if not emails:
            raise ValueError("SignupEmailIdentities requires at least one email")

        stack = Stack.of(self)
        self.identity_arns: list[str] = []

        for email in emails:
            ses.EmailIdentity(
                self,
                f"Identity{_logical(email)}",
                identity=ses.Identity.email(email),
            )
            self.identity_arns.append(
                stack.format_arn(
                    service="ses",
                    resource="identity",
                    resource_name=email,
                    arn_format=ArnFormat.SLASH_RESOURCE_NAME,
                )
            )


def _logical(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", s)
