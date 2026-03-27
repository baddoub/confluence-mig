"""Confluence Cloud REST API v2 client wrapper."""

import os
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

load_dotenv()


class ConfluenceClient:
    """Thin wrapper around Confluence Cloud REST API v2."""

    def __init__(self, base_url=None, email=None, api_token=None):
        self.base_url = (base_url or os.environ["CONFLUENCE_URL"]).rstrip("/")
        self.email = email or os.environ["CONFLUENCE_EMAIL"]
        self.api_token = api_token or os.environ["CONFLUENCE_API_TOKEN"]
        self.session = requests.Session()
        self.session.auth = (self.email, self.api_token)
        self.session.headers.update({"Accept": "application/json"})

    def _api_url(self, path: str) -> str:
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = self._api_url(path)
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_data: dict) -> dict:
        url = self._api_url(path)
        resp = self.session.post(
            url, json=json_data, headers={"Content-Type": "application/json"}
        )
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, json_data: dict) -> dict:
        url = self._api_url(path)
        resp = self.session.put(
            url, json=json_data, headers={"Content-Type": "application/json"}
        )
        resp.raise_for_status()
        return resp.json()

    # --- Space operations ---

    def get_space_by_key(self, space_key: str) -> dict:
        """Get space details by key using v1 API (v2 uses space ID)."""
        return self._get(f"/wiki/rest/api/space/{space_key}")

    # --- Page operations (REST API v2, cursor-based pagination) ---

    def get_pages_in_space(self, space_id: str, limit: int = 25) -> list[dict]:
        """Fetch all pages in a space using cursor-based pagination."""
        pages = []
        path = f"/wiki/api/v2/spaces/{space_id}/pages"
        params = {"limit": limit}

        while True:
            data = self._get(path, params=params)
            pages.extend(data.get("results", []))

            next_link = data.get("_links", {}).get("next")
            if not next_link:
                break

            path = next_link
            params = None  # cursor is embedded in the next link

        return pages

    def get_page_by_id(self, page_id: str, body_format: str = "storage") -> dict:
        """Fetch a single page with its body content."""
        return self._get(
            f"/wiki/api/v2/pages/{page_id}",
            params={"body-format": body_format},
        )

    def get_child_pages(self, page_id: str, limit: int = 25) -> list[dict]:
        """Fetch child pages of a given page."""
        children = []
        path = f"/wiki/api/v2/pages/{page_id}/children"
        params = {"limit": limit}

        while True:
            data = self._get(path, params=params)
            children.extend(data.get("results", []))

            next_link = data.get("_links", {}).get("next")
            if not next_link:
                break

            path = next_link
            params = None

        return children

    def get_page_labels(self, page_id: str) -> list[str]:
        """Fetch labels for a page."""
        data = self._get(f"/wiki/api/v2/pages/{page_id}/labels")
        return [label["name"] for label in data.get("results", [])]

    # --- Create / Update pages ---

    def create_page(
        self, space_id: str, title: str, body: str, parent_id: str | None = None
    ) -> dict:
        """Create a new page in a space."""
        payload = {
            "spaceId": space_id,
            "status": "current",
            "title": title,
            "body": {"representation": "storage", "value": body},
        }
        if parent_id:
            payload["parentId"] = parent_id
        return self._post("/wiki/api/v2/pages", payload)

    def update_page(self, page_id: str, title: str, body: str, version: int) -> dict:
        """Update an existing page."""
        payload = {
            "id": page_id,
            "status": "current",
            "title": title,
            "body": {"representation": "storage", "value": body},
            "version": {"number": version + 1},
        }
        return self._put(f"/wiki/api/v2/pages/{page_id}", payload)

    # --- Search ---

    def search_pages(self, cql: str, limit: int = 25) -> list[dict]:
        """Search pages using CQL."""
        data = self._get(
            "/wiki/rest/api/content/search", params={"cql": cql, "limit": limit}
        )
        return data.get("results", [])
