from typing import Any
from requests import Response, get
from access import BASE_URL, ACCESS_HEADER
from json import loads


class Track:
    def __init__(self, name: str, artists: list[str], album: str, duration: int) -> None:
        self.name = name
        self.artists = artists
        self.album = album
        self.duration = duration

    def __repr__(self) -> str:
        keys = list(self.__dict__)
        values: list[str] = [
            str(self.__dict__[key]) if not isinstance(self.__dict__[key], str) else f"'{self.__dict__[key]}'"
            for key in keys
        ]

        return f"{self.__class__.__name}({', '.join([f'{k}={v}' for k, v in zip(keys, values)])})"

    def __str__(self) -> str:
        return f'Track {self.name} by {", ".join(self.artists)}. Album: {self.album}'


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

    def _extract_tracks(self, url: str) -> list[dict]:
        response = get(url, headers=ACCESS_HEADER)
        response: Any = loads(response.content)
        res = (
            response["items"]
            if not response["next"]
            else response["items"] + self._extract_tracks(response["next"])
        )
        return [self._create_track(track) for track in [i["track"] for i in res] if track["track"]]

    def _create_track(self, track: list[dict]) -> Track:
        name: str = track["name"]
        album: str = track["album"]["name"]
        artists: list[str] = [artist["name"] for artist in track["artists"]]
        duration: int = track["duration_ms"]
        return Track(name, artists, album, duration)


searching_for = "https://open.spotify.com/playlist/3cEYpjA9oz9GiPac4AsH4n"
p = Playlist(searching_for)
for t in p.tracks:
    print(t)
