"""livecode kernel to execute code in a sandbox.
"""
import aiodocker
from pathlib import Path
import tempfile
import os
import json
from .msgtypes import ExecMessage
from . import config

class Kernel:
    def __init__(self, runtime):
        self.runtime = runtime

    async def execute(self, msg: ExecMessage):
        kspec = config.get_runtime(self.runtime)
        code_filename = msg.code_filename or kspec['code_filename']

        # ✅ FIX: stable workspace instead of temp dir
        base_dir = Path("/app/workspace")
        base_dir.mkdir(parents=True, exist_ok=True)

        job_id = getattr(msg, "id", None) or "default"
        root = base_dir / f"job-{job_id}"
        root.mkdir(parents=True, exist_ok=True)

        self.root = str(root)

        if msg.code:
            self.save_file(root, code_filename, msg.code)

        for f in msg.files:
            self.save_file(root, f['filename'], f['contents'])

        container = await self.start_container(
            image=kspec['image'],
            command=msg.command or kspec['command'],
            root=str(root),
            env=msg.env or {}
        )

        try:
            async for line in self.read_docker_log_lines(container):
                if line.startswith("--MSG--"):
                    json_message = line[len("--MSG--"):].strip()
                    msg_data = json.loads(json_message)

                    if "msgtype" not in msg_data:
                        continue

                    yield msg_data
                else:
                    yield {
                        "msgtype": "write",
                        "file": "stdout",
                        "data": line
                    }

        finally:
            status = await container.wait()
            yield {"msgtype": "exitstatus", "exitstatus": status["StatusCode"]}
            await container.delete()
            
    async def read_docker_log_lines(self, container, max_line_length=1000000):
        """Reads the docker log line by line.

        When a line is longer, the docker api gives the line in chunks.
        This function combines the chunks into a line and returns one
        line at a time as an generator.

        Also includes a protection against very long lines. if a line
        has more than max_line_length (default 1 million), reading
        is aborted and no further data is read.
        """
        logs = container.log(stdout=True, stderr=True, follow=True)

        remaining = ""

        async for line in logs:
            line = remaining + line
            remaining = ""

            if line.endswith("\n"):
                yield line
            else:
                # protection against very large images
                # stop reading further when the line has more than max_line_length
                if len(line) > max_line_length:
                    return
                remaining = line

        if remaining:
            yield remaining

    def save_file(self, root, filename, contents):
        Path(root, filename).write_text(contents)

    async def start_container(self, image, command, root, env):
        

        docker = aiodocker.Docker(
            url=os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
        )
        print('== starting a container ==')
        # command = ["timeout", "10"] + command
        env_entries = [f'{k}={v}' for k, v in env.items()]
        config = {
            'Cmd': command,
            'Image': image,
            'Env': ["PYTHONUNBUFFERED=1", "PYTHONDONTWRITEBYTECODE=1"] + env_entries,
            'HostConfig': {
                'Binds': [
                    f"{root}:/app"
                ],
                "Memory": 100*1024*1024,
                "CPUQuota": 50000,
                "CPUPeriod": 100000,
            }
        }
        container = await docker.containers.create(
            config=config
        )
        await container.start()
        return container
