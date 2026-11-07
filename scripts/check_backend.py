"""Check the local service before starting it: 0 running, 1 free, 2 occupied."""
import json
import socket
from urllib.request import ProxyHandler, build_opener


def main():
    # Local diagnostics must not depend on the user's system HTTP proxy.
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:8000/api/v1/health', timeout=3) as response:
            health = json.load(response)
        with opener.open('http://127.0.0.1:8000/openapi.json', timeout=3) as response:
            schema = json.load(response)
        if (isinstance(health, dict) and isinstance(schema, dict)
                and health.get('status') == 'ok'
                and '/api/v1/bills' in schema.get('paths', {})):
            return 0
    except (OSError, ValueError):
        pass
    try:
        with socket.create_connection(('127.0.0.1', 8000), timeout=2):
            return 2
    except OSError:
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
