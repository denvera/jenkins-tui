from rich.console import RenderableType
from rich.padding import Padding
from rich.style import StyleType
from rich.table import Table
from rich.panel import Panel
from textual.widget import Widget

from textual.widgets import Header as TextualHeader
from textual.reactive import Reactive
from textual import events

from .. import config
from ..client import Jenkins

from .build_queue import BuildQueue
from .executor_status import ExecutorStatus

from rich.layout import Layout


class HomeWidget(Widget):

    style: Reactive[StyleType] = Reactive("")
    layout_size: Reactive[int] = 3

    def __init__(self, client: Jenkins) -> None:
        self.client = client

        self.defaults = {
            "title": "Welcome!",
            "text": "Welcome to Jenkins TUI! 🚀\n\n👀 Use the navigation fly-out on the left!",
        }

        name = self.__class__.__name__
        super().__init__(name=name)

    def render(self) -> RenderableType:

        _text = self.defaults["text"]
        panel_content = Padding(
            renderable=_text,
            pad=(1, 0, 0, 1),
            style=self.style,
        )

        _title = self.defaults["title"]
        info = Panel(renderable=panel_content, title=_title, expand=True)
        queue = BuildQueue(self.client)
        builds = ExecutorStatus(self.client)

        # layout.split(
        #     Layout(name="header", size=3),
        #     Layout(name="main", ratio=1),
        #     Layout(name="footer", size=7),
        # )
        # layout["main"].split_row(
        #     Layout(name="side"),
        #     Layout(name="body", ratio=2, minimum_size=60),
        # )
        # layout["side"].split(Layout(name="box1"), Layout(name="box2"))

        layout: RenderableType
        layout = Layout()
        layout.split_column(
            Layout(name="info"), Layout(name="queue"), Layout(name="builds")
        )
        layout["info"].update(info)

        return layout

        return layout.renderable
