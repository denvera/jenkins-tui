from __future__ import annotations
from dependency_injector.wiring import Container, Provide, inject

import rich.repr

from jenkins_tui import config

from ..client import Jenkins

from urllib.parse import unquote

from rich.console import RenderableType
from rich.text import Text

from functools import lru_cache

from dataclasses import dataclass
from textual.reactive import Reactive
from textual.widgets import TreeControl, TreeClick, TreeNode, NodeID

from ..containers import Container
from ..messages import RootClick, JobClick


@dataclass
class JobEntry:
    """Represents the data"""

    name: str
    url: str
    color: str
    type: str
    jobs: str | list[dict[str, str]]


class JenkinsTree(TreeControl[JobEntry]):

    has_focus: Reactive[bool] = Reactive(False)

    @inject
    def __init__(self, client: Jenkins = Provide[Container.client]) -> None:
        """Creates a directory tree struction from Jenkins jobs and builds.
        This class is a copy of textual.widgets.DirectoryTree with ammendments that allow it to be used with Jenkins Api responses.

        Args:
            client (Jenkins): A jenkins.Jenkins client instance.
            name (str): The name of the Tree instance.
        """
        data = JobEntry(name="root", url="", color="", type="root", jobs=[])
        name = self.__class__.__name__
        super().__init__(label="pipelines", name=name, data=data)

        self.styles = config.style_map[config.style]
        self.client = client
        self.color_map = {
            "aborted": "❌",
            "blue": "🔵",
            "blue_anime": "🔄",
            "disabled": "⭕",
            "grey": "⚪",
            "notbuilt": "⏳",
            "red_anime": "🔄",
            "red": "🔴",
            "yellow": "🟡",
            "none": "🟣",
        }

        self.type_map = {
            "org.jenkinsci.plugins.workflow.job.WorkflowJob": "job",
            "com.cloudbees.hudson.plugins.folder.Folder": "folder",
            "org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject": "multibranch",
        }

        self.root.tree.guide_style = self.styles["tree_guide"]

    async def action_click_label(self, node_id: NodeID) -> None:
        """Overrides action_click_label from tree control and sets show cursor to True"""
        node = self.nodes[node_id]
        self.cursor = node.id
        self.cursor_line = self.find_cursor() or 0
        self.show_cursor = True
        await self.post_message(TreeClick(self, node))

    def on_focus(self) -> None:
        """Sets has_focus to true when the item is clicked."""
        self.has_focus = True

    def on_blur(self) -> None:
        """Sets has_focus to false when an item no longer has focus."""
        self.has_focus = False

    async def watch_hover_node(self, hover_node: NodeID) -> None:
        """Configures styles for a node when hovered over by the mouse pointer."""
        for node in self.nodes.values():
            node.tree.guide_style = (
                self.styles["tree_guide_on_hover"]
                if node.id == hover_node
                else self.styles["tree_guide"]
            )
        self.refresh(layout=True)

    def render_node(self, node: TreeNode[JobEntry]) -> RenderableType:
        """Renders a node in the tree.

        Args:
            node (TreeNode[JobEntry]): A node in the tree.

        Returns:
            RenderableType: A renderable object.
        """

        return self.render_tree_label(
            node,
            node.data.type,
            node.expanded,
            node.is_cursor,
            node.id == self.hover_node,
            self.has_focus,
        )

    @lru_cache(maxsize=1024 * 32)
    def render_tree_label(
        self,
        node: TreeNode[JobEntry],
        type: str,
        expanded: bool,
        is_cursor: bool,
        is_hover: bool,
        has_focus: bool,
    ) -> RenderableType:
        """[summary]

        Args:
            node (TreeNode[JobEntry]): [description]
            type (str): [description]
            expanded (bool): [description]
            is_cursor (bool): [description]
            is_hover (bool): [description]
            has_focus (bool): [description]

        Returns:
            RenderableType: [description]
        """

        meta = {
            "@click": f"click_label({node.id})",
            "tree_node": node.id,
            "cursor": node.is_cursor,
        }

        label = Text(node.label) if isinstance(node.label, str) else node.label

        if is_hover:
            label.stylize(self.styles["node_on_hover"])

        if is_cursor and has_focus:
            label.stylize(self.styles["tree_on_cursor"])

        if type == "root":
            label.stylize(self.styles["root_node"])
            icon = "📂"

        elif type == "folder":
            label.stylize(self.styles["folder"])
            icon = "📂" if expanded else "📁"

        elif type == "multibranch":
            label.stylize(self.styles["multibranch_node"])
            icon = "🌱"

        else:
            label.stylize(self.styles["node"])
            icon = self.color_map.get(node.data.color, "?")

        icon_label = Text(f"{icon} ", no_wrap=True, overflow="ellipsis") + label
        icon_label.apply_meta(meta)
        return icon_label

    async def on_mount(self) -> None:
        """Actions that are executed when the widget is mounted.

        Args:
            event (events.Mount): A mount event.
        """
        await self.load_jobs(self.root)

    async def load_jobs(self, node: TreeNode[JobEntry]):
        """Load jobs for a tree node. If the current node is "root" then a call is made to Jenkins to retrieve a full list otherwise process jobs from the current node.

        Args:
            node (TreeNode[JobEntry]): [description]
        """
        jobs = []
        if node.data.type == "root":
            jobs = await self.client.get_jobs(recursive=True)
        else:
            jobs = node.data.jobs

        entry: dict[str, str]
        for entry in jobs:

            typeof = self.type_map.get(entry["_class"], "")
            clean_name = (
                "chicken"
                if getattr(self.app, "chicken_mode_enabled", None)
                else unquote(entry["name"])
            )
            parts = entry["url"].strip("/").split("/job/")
            full_name = "/".join(parts[1:])

            job = JobEntry(
                name=full_name,
                url=entry["url"],
                color=entry.get("color", "none"),
                type=typeof,
                jobs=entry.get("jobs", []),
            )

            await node.add(clean_name, job)

        node.loaded = True
        await node.expand()
        self.refresh(layout=True)

    async def handle_tree_click(self, message: TreeClick[JobEntry]) -> None:
        """Handle messages that are sent when a tree item is clicked.

        Args:
            message (TreeClick[JobEntry]): A message that is sent when a tree item is clicked.
        """
        node_data = message.node.data

        if node_data.type == "job":
            self.log("Emitting JobClick message")
            await self.emit(JobClick(self, node_data.name, node_data.url))

        elif node_data.name == "root":
            self.log("Emitting RootClick message")
            await self.emit(RootClick(self))

        else:
            if not message.node.loaded:
                await self.load_jobs(message.node)
                await message.node.expand()
            else:
                await message.node.toggle()
