from textual.events import Mount
from urllib.parse import urlparse

from .window_view import WindowView

from ..widgets import JobInfo, BuildTable
from ..client import Jenkins


class JobView(WindowView):
    def __init__(self, client: Jenkins, url: str) -> None:
        self.current_job_url = url
        self.client = client
        super().__init__()

    async def on_mount(self, event: Mount) -> None:

        url = urlparse(self.current_job_url)
        response = await self.client.get_job(path=url.path)

        info = JobInfo(title=response["displayName"], text="test")

        builds = BuildTable(client=self.client, url=self.current_job_url)

        await self.dock(*[info, builds])
