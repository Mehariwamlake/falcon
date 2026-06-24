"""livecode kernel to execute code in a sandbox."""
import json
import os
from pathlib import Path

import aiodocker

from .msgtypes import ExecMessage
from . import config


HOST_WORKSPACE = os.getenv(
    "HOST_WORKSPACE",
    "/opt/falcon-workspace"
)

CONTAINER_WORKSPACE = "/workspace"


class Kernel:
    def __init__(self, runtime):
        self.runtime = runtime

    async def execute(self, msg: ExecMessage):
        kspec = config.get_runtime(self.runtime)
        code_filename = msg.code_filename or kspec["code_filename"]

        job_id = getattr(msg, "id", None) or os.urandom(8).hex()

        # Path inside Falcon container
        container_root = (
            Path(CONTAINER_WORKSPACE)
            / f"job-{job_id}"
        )

        # Corresponding host path
        host_root = (
            Path(HOST_WORKSPACE)
            / f"job-{job_id}"
        )

        container_root.mkdir(
            parents=True,
            exist_ok=True
        )

        self.root = str(container_root)

        if msg.code:
            self.save_file(
                container_root,
                code_filename,
                msg.code
            )

        for f in msg.files:
            self.save_file(
                container_root,
                f["filename"],
                f["contents"]
            )

        print("===================================")
        print("Runtime:", self.runtime)
        print("Container Root:", container_root)
        print("Host Root:", host_root)
        print("Files:", os.listdir(container_root))
        print("===================================")

        container = await self.start_container(
            image=kspec["image"],
            command=msg.command or kspec["command"],
            host_root=str(host_root),
            env=msg.env or {},
        )

        try:
            async for line in self.read_docker_log_lines(container):
                if line.startswith("--MSG--"):
                    json_message = (
                        line[len("--MSG--"):].strip()
                    )

                    try:
                        data = json.loads(json_message)

                        if "msgtype" in data:
                            yield data

                    except Exception:
                        pass

                else:
                    yield {
                        "msgtype": "write",
                        "file": "stdout",
                        "data": line,
                    }

        finally:
            status = await container.wait()

            yield {
                "msgtype": "exitstatus",
                "exitstatus": status["StatusCode"],
            }

            try:
                await container.delete(force=True)
            except Exception:
                pass

    async def read_docker_log_lines(
        self,
        container,
        max_line_length=1000000,
    ):
        logs = container.log(
            stdout=True,
            stderr=True,
            follow=True,
        )

        remaining = ""

        async for line in logs:
            line = remaining + line
            remaining = ""

            if line.endswith("\n"):
                yield line
            else:
                if len(line) > max_line_length:
                    return

                remaining = line

        if remaining:
            yield remaining

    def save_file(
        self,
        root,
        filename,
        contents
    ):
        filepath = Path(root) / filename

        filepath.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        filepath.write_text(contents)

    async def start_container(
        self,
        image,
        command,
        host_root,
        env,
    ):
        docker = aiodocker.Docker(
            url=os.getenv(
                "DOCKER_HOST",
                "unix:///var/run/docker.sock",
            )
        )

        print("== starting container ==")
        print("Image:", image)
        print("Command:", command)
        print("Mount:", f"{host_root}:/app")

        env_entries = [
            f"{k}={v}"
            for k, v in env.items()
        ]

        container_config = {
            "Image": image,
            "Cmd": command,
            "Env": [
                "PYTHONUNBUFFERED=1",
                "PYTHONDONTWRITEBYTECODE=1",
            ] + env_entries,
            "HostConfig": {
                "Binds": [
                    f"{host_root}:/app"
                ],
                "Memory": 100 * 1024 * 1024,
                "CPUQuota": 50000,
                "CPUPeriod": 100000,
            },
        }

        container = await docker.containers.create(
            config=container_config
        )

        await container.start()

        return container