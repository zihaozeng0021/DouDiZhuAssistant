"""PyInstaller entrypoint for one-file Windows executable."""

from app.server import run_server


if __name__ == "__main__":
    run_server(auto_open_browser=True)
