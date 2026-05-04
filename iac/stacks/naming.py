import aws_cdk as cdk
from constructs import IConstruct


class Naming:
    """Resource naming + default tagging helper.

    Physical names follow `<prefix>-<core>-<suffix>`, where:
      - `prefix` defaults to the `project` value when not set explicitly
      - `suffix` defaults to the `env` value when not set explicitly
      - `core` is owned by each resource construct (its `CORE_NAME` constant)

    Resources never accept a name from config — they describe themselves via
    `CORE_NAME` and ask `Naming` for the composed physical name.
    """

    def __init__(
        self,
        *,
        project: str,
        env: str,
        prefix: str | None = None,
        suffix: str | None = None,
    ) -> None:
        self.project = project
        self.env = env
        self.prefix = prefix or project
        self.suffix = suffix or env

    def build(self, core: str) -> str:
        return f"{self.prefix}-{core}-{self.suffix}"

    def apply_default_tags(
        self,
        scope: IConstruct,
        extra: dict[str, str] | None = None,
    ) -> None:
        """Tag every taggable resource in `scope` with `project` and `env`.

        CDK's tag aspect walks the construct tree at synth time, so calling
        this once on a stack covers every nested resource — no per-resource
        opt-in needed.
        """
        cdk.Tags.of(scope).add("project", self.project)
        cdk.Tags.of(scope).add("env", self.env)
        for key, value in (extra or {}).items():
            cdk.Tags.of(scope).add(key, value)
