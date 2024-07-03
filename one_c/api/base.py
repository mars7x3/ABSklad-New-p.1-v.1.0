from abc import ABC
from json import JSONDecodeError
from typing import Any
from urllib.parse import urljoin

from requests import Session, Request, Response


class BaseAPIClient(ABC):
    base_url: str = None

    def __init__(self):
        assert self.base_url

        self._session = Session()
        self._session_kwargs = {}

    def close_session(self):
        self._session.close()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        request = Request(method, urljoin(self.base_url, path), **kwargs)
        self._process_request(request)
        response = self._session.send(request.prepare(), **self._session_kwargs)
        return self._process_response(response)

    def _process_request(self, request: Request) -> None:
        pass

    def _process_response(self, response: Response) -> Any:
        pass


class APIClient(BaseAPIClient):
    def _process_response(self, response: Response) -> dict[str, Any] | list[dict[str, Any]]:
        try:
            return response.json()
        except (JSONDecodeError, ValueError):
            response.raise_for_status()
            raise

    def get(self, path: str, params: dict[str, Any] = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] = None) -> Any:
        return self._request("POST", path, json=json)

    def patch(self, path: str, json: dict[str, Any] = None) -> Any:
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)
