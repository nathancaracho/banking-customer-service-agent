from .config import load_settings
from .server import create_mcp


settings = load_settings()
mcp = create_mcp(settings)


def main() -> None:
    mcp.run(
        transport="streamable-http",
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
