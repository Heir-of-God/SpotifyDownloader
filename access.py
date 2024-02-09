from dotenv import load_dotenv
from os import getenv
from base64 import b64encode
from requests import post
from json import loads


def get_access_token_header() -> dict[str, str]:
    auth_string: str = client_id + ":" + client_secret
    auth_bytes: bytes = auth_string.encode("utf-8")
    auth_base64 = str(b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"

    headers: dict[str, str] = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data: dict[str, str] = {"grant_type": "client_credentials"}

    result = post(url=url, headers=headers, data=data)
    json_result = loads(result.content)
    token: str = json_result["access_token"]

    return {"Authorization": "Bearer " + token}


load_dotenv()
client_id: str = getenv("CLIENT_ID")
client_secret: str = getenv("CLIENT_SECRET")
BASE_URL: str = "https://api.spotify.com/v1/"
ACCESS_HEADER: dict[str, str] = get_access_token_header()
