from requests import Response, get
from access import BASE_URL, ACCESS_HEADER
from json import loads
from pytube import Search, YouTube
from os import mkdir, getcwd, remove
from os.path import isdir
import subprocess


class Track:
    def __init__(self, name: str, artists: list[str], album: str, duration: int) -> None:
        self.name: str = name
        self.artists: list[str] = artists
        self.album: str = album
        self.duration: int = duration

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
        self.id: str = link.split("/")[-1].split("?")[0]
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

    def get_tracks(self) -> list[dict]:
        return self.tracks


class YoutubeDownloader:
    def __init__(self):
        self.path_to_save: str = getcwd() + "\\tracks"
        if not isdir(self.path_to_save):
            mkdir(self.path_to_save)

    def search_for_video(self, track: Track, official: bool = True):
        searching: Search = Search(f"{track.artists[0]} - {track.name}{' official audio' if official else ''}")
        results: list[YouTube] = searching.results
        result: YouTube = results.pop(0)

        while not (abs(result.length * 1000 - track.duration) <= 1200):
            if not results:
                searching.get_next_results()
                results = searching.results
            result = results.pop(0)

        return result

    def download_video(self, video: YouTube):
        stream = video.streams.get_by_itag(251)
        stream.download(output_path=self.path_to_save, filename=video.title + ".webm")
        file_path = self.path_to_save + "\\" + video.title
        subprocess.run(f'ffmpeg -i "{file_path}.webm" -vn -ab 128k -ar 44100 -y "{file_path}.mp3"', shell=True)
        remove(file_path + ".webm")


searching_for = "https://open.spotify.com/playlist/6ZXl5BhSdGw4WT9u3yhxHM?si=223943e2fd454b61"
p = Playlist(searching_for)
YD = YoutubeDownloader()
downloaded = 0  # only for test TODO
for t in p.tracks:
    v = YD.search_for_video(t)
    if downloaded < 6:
        YD.download_video(v)
        downloaded += 1
