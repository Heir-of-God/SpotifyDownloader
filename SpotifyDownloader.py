from typing import Self
from requests import Response, get
from access import BASE_URL, ACCESS_HEADER
from json import loads
from pytube import Search, YouTube
from os import mkdir, getcwd, remove
from os.path import isdir, exists
import subprocess
from mutagen.id3 import ID3, TALB, TIT2, TPE1, APIC, TLEN, ID3NoHeaderError
from argparse import ArgumentParser, Namespace


def get_image_binary(img_url: str) -> bytes:
    """Returns byte representation of image by its url"""
    response = get(img_url)
    # region SavingImage
    # if response.status_code:
    #     output = open("output.png", "wb")
    #     output.write(response.content)
    #     output.close()
    # endregion
    return response.content


def get_spotify_id(url: str) -> str:
    """Returns only Spotify's id from provided url"""
    return url.split("/")[-1].split("?")[0]


class Track:
    """Class for representing Spotify's tracks details"""

    def __init__(self, name: str, artists: list[str], album: str, duration: int, binary_image: bytes) -> None:
        self.name: str = name
        self.artists: list[str] = artists
        self.album: str = album
        self.duration: int = duration  # in milliseconds
        self.binary_image: bytes = binary_image

    @classmethod
    def get_track_by_data(cls, data: dict) -> Self:
        """Creates track from provided data (dict from Spotify API about this track)"""
        name: str = data["name"]
        album: str = data["album"]["name"]
        artists: list[str] = [artist["name"] for artist in data["artists"]]
        duration: int = data["duration_ms"]
        binary_image: bytes = get_image_binary(data["album"]["images"][0]["url"])
        return cls(name, artists, album, duration, binary_image)

    def __repr__(self) -> str:
        keys = list(self.__dict__)
        values: list[str] = [
            str(self.__dict__[key]) if not isinstance(self.__dict__[key], str) else f"'{self.__dict__[key]}'"
            for key in keys
        ]

        return f"{self.__class__.__name__}({', '.join([f'{k}={v}' for k, v in zip(keys, values)])})"

    def __str__(self) -> str:
        return f'Track {self.name} by {", ".join(self.artists)}. Album: {self.album}'


class Playlist:
    """Class for representing Spotify's playlists details (As in Spotify, playlist consists of Track()s)"""

    def __init__(self, link: str, start_from: int, end_at: int) -> None:
        self.id: str = get_spotify_id(link)
        response: Response = get(BASE_URL + f"playlists/{self.id}", headers=ACCESS_HEADER)
        response_dict = loads(response.content)
        self.name: str = response_dict["name"]
        self.description: str = response_dict["description"]
        self.owner: str = (
            response_dict["owner"]["display_name"] if response_dict["owner"]["display_name"] else "Unknown_User"
        )  # Unknown_user can appear when API hasn't access to user account details
        self.tracks: list[Track] = self._extract_tracks(response_dict["tracks"]["href"])

        # Cutting out the desired part
        if start_from and end_at:
            self.tracks = self.tracks[start_from - 1 : end_at]
        elif start_from:
            self.tracks = self.tracks[start_from - 1 :]
        elif end_at:
            self.tracks = self.tracks[:end_at]

        self.tracks = [
            Track.get_track_by_data(track) for track in [i["track"] for i in self.tracks] if track["track"]
        ]  # converting all tracks in Track() objects

    def _extract_tracks(self, url: str) -> list[dict]:
        """Returns all tracks from playlist via recursion"""
        response = get(url, headers=ACCESS_HEADER)
        response = loads(response.content)
        res: list[dict] = (
            response["items"]
            if not response["next"]
            else response["items"] + self._extract_tracks(response["next"])
        )
        return res

    def get_tracks(self) -> list[Track]:
        """Returns playlist's tracks"""
        return self.tracks


class YoutubeDownloader:
    """The class responsible for downloading, searching and other work with YouTube."""

    def __init__(self) -> None:
        self.path_to_save: str = getcwd() + "\\tracks"
        if not isdir(self.path_to_save):
            mkdir(self.path_to_save)

    def search_for_video(self, track: Track) -> list[YouTube]:  # Returns up to 3 YouTube objects in list
        """Searching for videos on YouTube with simillar name and duration

        Args:
            track (Track): the track you want to search YouTube for

        Returns:
            list[YouTube]: list object which contains UP TO 3 YouTube objects - 1 main and 2 spares. Have chances to contain less than 3 items!
        """
        searching: Search = Search(f"{track.artists[0]} - {track.name} audio only")
        searching_results: list[YouTube] = searching.results
        searched = 1
        ms_range = 2000
        results: list[YouTube] = []
        video_count = 0

        while not (video_count != 0 and not results) and (video_count != 3):
            if not searching_results:
                searching.get_next_results()
                searching_results = searching.results
            cur_video: YouTube = searching_results.pop(0)
            if abs(cur_video.length * 1000 - track.duration) <= ms_range:
                results.append(cur_video)
                video_count += 1

            searched += 1
            if searched == 15:
                ms_range = 15000
            if searched >= 40 and not results:  # limit there!
                print(
                    f"Seems like there's no this song '{track.name} {track.artists}' with this duration {track.duration}ms on Youtube, you can try to change limit in search_for_video function"
                )
                return results
        return results

    def _correct_metadata(self, track: Track, path: str) -> None:
        """Helper method which helps to set right metadata after downloading a song"""
        try:
            id3 = ID3(path)
        except ID3NoHeaderError:
            id3 = ID3()
        id3.delete()
        id3["TPE1"] = TPE1(encoding=3, text=f"{', '.join(track.artists)}")
        id3["TALB"] = TALB(encoding=3, text=f"{track.album}")
        id3["TIT2"] = TIT2(encoding=3, text=f"{track.name}")
        id3["APIC"] = APIC(encoding=3, mime="image/png", type=3, desc="Cover", data=track.binary_image)
        id3["TLEN"] = TLEN(encoding=3, text=f"{track.duration}")
        id3.save(path)

    def _get_correct_name(self, track: Track) -> str:
        """There's low chance to face conflicts with file names, but this method cares so there's no chance at all"""
        new_name: str = track.name
        for char in '"/\<>:|?*':  # replacing forbidden characters for file's name in windows and linux
            new_name = new_name.replace(char, "")
        num_to_add = 1
        if exists(self.path_to_save + f"\\{new_name}.mp3"):
            new_name = f"{track.artists[0]} - {track.name}"
        while exists(self.path_to_save + f"\\{new_name}.mp3"):
            new_name += str(num_to_add)
            num_to_add += 1
        return new_name

    def download_track(self, videos: list[YouTube], track: Track) -> str:
        """Method to download a single track from its YouTube instances

        Args:
            videos (list[YouTube]): up to 3 YouTube objects (up to 3 attempts to download this song)
            track (Track): track associated with list of YouTube videos (used by helper methods to rename, correct metadata etc)

        Returns:
            str: download result message
        """
        if not videos:
            return None
        downloaded = False
        cur_candidate_ind = 0
        file_name: str = self._get_correct_name(track)

        while not downloaded and cur_candidate_ind != len(videos):
            youtube_obj: YouTube = videos[cur_candidate_ind]
            try:
                stream = youtube_obj.streams.get_by_itag(251)
                stream.download(output_path=self.path_to_save, filename=file_name + ".webm")
                file_path: str = self.path_to_save + "/" + file_name
                subprocess.run(
                    f'ffmpeg -i "{file_path}.webm" -vn -ab 128k -ar 44100 -y -map_metadata -1 "{file_path}.mp3" -loglevel quiet'
                )  # Using ffmpeg to convert webm file to mp3. remove -loglevel quiet if you want to see output from ffmpeg
                remove(file_path + ".webm")
                file_path += ".mp3"
                self._correct_metadata(track, file_path)
                downloaded = True
            except Exception as e:
                print(
                    f"Encountering unexpected error while downloading the track {track.name}. Error: {e}. Attempt: {cur_candidate_ind + 1}"
                )
            cur_candidate_ind += 1

        if not downloaded:
            return f"Sorry, can't download track {track.name} by {track.artists[0]}"
        else:
            return f"Successfully downloaded {track.name} by {track.artists[0]}"

    def download_playlist(self, playlist: list[Track]) -> None:
        """Separate method to download full Spotify playlist"""
        length: int = len(playlist)
        for track_num, track in enumerate(playlist, 1):
            videos: list[YouTube] = self.search_for_video(track)
            download_output: str = self.download_track(videos, track)
            if download_output:
                print(f"Progress: {track_num}/{length}. " + download_output)
        return


if __name__ == "__main__":

    # region CLI interface creating
    parser = ArgumentParser()
    parser.add_argument("url", help="this parameter must be either url to your playlist or song on Spotify")
    parser.add_argument(
        "-sa",
        "--start_at",
        type=int,
        help="If specified start downloading your songs in playlist from this song (1-indexed)",
    )
    parser.add_argument(
        "-ea",
        "--end_at",
        type=int,
        help="If specified end downloading your songs in playlist after this song (1-indexed)",
    )
    args: Namespace = parser.parse_args()
    # endregion

    searching_for: str = args.url
    YD = YoutubeDownloader()

    if "track" in searching_for:
        track_id: str = get_spotify_id(searching_for)
        response: Response = get(BASE_URL + f"tracks/{track_id}", headers=ACCESS_HEADER)
        response_dict = loads(response.content)

        targeted_track: Track = Track.get_track_by_data(response_dict)
        candidates: list[YouTube] = YD.search_for_video(targeted_track)
        download_output: str = YD.download_track(candidates, targeted_track)

        if download_output:
            print(download_output)

    elif "playlist" in searching_for:
        start_from = args.start_at
        end_at = args.end_at

        # validating parameters
        if (
            (start_from and start_from < 1)
            or (end_at and end_at < 1)
            or (start_from and end_at and end_at < start_from)
        ):
            raise ValueError(
                f"You must provide positive integers for params -sa and -ea and -ea >= -sa. You've provided: {start_from} {end_at}"
            )

        playlist_obj: Playlist = Playlist(searching_for, start_from, end_at)
        YD.download_playlist(playlist_obj.get_tracks())

    else:
        print("Encountered error! Your parameter must be a valid link to the PUBLIC playlist or track!")

    exit(0)
