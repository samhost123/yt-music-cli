from textual.screen import Screen
from textual.widgets import Static
from textual.app import ComposeResult


class HomeScreen(Screen):
    BINDINGS = [("escape", "dismiss", "Back")]

    def compose(self) -> ComposeResult:
        yield Static("  Welcome to yt-music-cli", id="home-title")
        yield Static("  Press / to search, or browse your library with 2", id="home-subtitle")
        yield Static("", id="home-quick")
