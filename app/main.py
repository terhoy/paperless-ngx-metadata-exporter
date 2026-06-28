from . import create_app
from .config import AppConfig

app = create_app()

if __name__ == "__main__":
    cfg = AppConfig.from_env()
    app.run(host=cfg.host, port=cfg.port, debug=False)
