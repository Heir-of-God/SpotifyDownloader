from typing import Any
from requests import Response, get
from access import BASE_URL, ACCESS_HEADER
from json import loads


class Playlist:
    def __init__(self, link: str) -> None:
        self.id: str = link.split("/")[-1]
        response: Response = get(BASE_URL + f"playlists/{self.id}", headers=ACCESS_HEADER)
        response_dict: Any = loads(response.content)
        self.name: str = response_dict["name"]
        self.description: str = response_dict["description"]
        self.owner: str = (
            response_dict["owner"]["display_name"] if response_dict["owner"]["display_name"] else "Unknown_User"
        )
        self.tracks: list[dict] = self._extract_tracks(response_dict["tracks"]["href"])
        print(len(self.tracks))

    def _extract_tracks(self, url: str) -> list[dict]:
        res = get(url, headers=ACCESS_HEADER)
        res: Any = loads(res.content)
        return res["items"] if not res["next"] else res["items"] + self._extract_tracks(res["next"])


searching_for = "https://open.spotify.com/playlist/2LalszocxvwtOre9CRnOuF"
p = Playlist(searching_for)
