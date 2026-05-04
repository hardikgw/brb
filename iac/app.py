#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.config_loader import load_config
from stacks.naming import Naming
from stacks.site_stack import SiteStack


env_name = os.environ.get("BRB_ENV", "dev")
config = load_config(env_name)

naming = Naming(
    project=config["project"],
    env=config["env"],
    prefix=config.get("prefix"),
    suffix=config.get("suffix"),
)

app = cdk.App()

SiteStack(
    app,
    "SiteStack",
    config=config,
    naming=naming,
    stack_name=naming.build(SiteStack.CORE_NAME),
    env=cdk.Environment(
        account=config.get("account") or os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=config["region"],
    ),
)

app.synth()
