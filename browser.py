import socket
import ssl
from typing import BinaryIO, Dict

ConnectionPool: Dict[tuple[str, str, int], socket.socket] = {}


class URL:
    def __init__(self, url: str) -> None:
        if not url:
            self.schema = "file"
            self.path = "/Users/harsh/Project/browser/browser.py"
            return
        self.schema, url = url.split("://", 1)
        assert self.schema in ["http", "https", "file"]
        if self.schema == "http":
            self.port = 80
        elif self.schema == "https":
            self.port = 443

        if self.schema == "file":
            self.path = url
            return
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

        self.path = "/" + url

    def make_request(self, s: socket.socket) -> None:
        headers = {"Host": self.host, "User-Agent": "timid/1.0"}

        request = f"GET {self.path} HTTP/1.1\r\n"

        for key, value in headers.items():
            request += f"{key}: {value}\r\n"

        request += "\r\n"
        s.send(request.encode("utf8"))

    def make_socket(self) -> socket.socket:
        pool_key = (self.schema, self.host, self.port)

        if pool_key in ConnectionPool:
            s = ConnectionPool[pool_key]
        else:
            s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
            s.connect((self.host, self.port))
            if self.schema == "https":
                ctx = ssl._create_unverified_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
            ConnectionPool[pool_key] = s
        return s

    def extract_headers(self, response: BinaryIO) -> dict:
        response_headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        return response_headers

    def request(self) -> str:
        if self.schema == "file":
            with open(self.path, "r", encoding="utf8") as f:
                return f.read()
        tries = 5
        s = None
        while tries:
            if not s:
                s = self.make_socket()
            self.make_request(s)
            response = s.makefile("rb")
            _, status, _ = response.readline().decode("utf8").split(" ", 2)
            response_headers = self.extract_headers(response)

            if 300 <= int(status) < 400:
                redirect = response_headers.get("location")
                if redirect is not None:
                    if "://" in redirect:
                        self.__init__(redirect)
                        s = None
                    else:
                        self.path = redirect
                else:
                    return "Redirect Error"
                tries -= 1
                continue
            else:
                assert "content-encoding" not in response_headers
                if "transfer-encoding" in response_headers:
                    data_length = int(response.readline().decode("utf8").strip(), 16)
                    content = ""
                    while data_length:
                        content += response.read(data_length).decode("utf8")
                        response.readline()
                        data_length = int(
                            response.readline().decode("utf8").strip(), 16
                        )

                else:
                    body_bytes = response.read(
                        int(response_headers.get("content-length", -1))
                    )
                    content = body_bytes.decode("utf8")
                return content
        return "Redirect Loop"


def load(url: URL):
    body = url.request()
    show(body)


def show(body: str):
    in_tag = False
    idx = 0
    length = len(body)

    ENTITIES = {"&lt;": "<", "&gt;": ">"}

    while idx < length:
        c = body[idx]
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            if c == "&":
                end_idx = body.find(";", idx, idx + 4)
                entity = body[idx : end_idx + 1] if end_idx != -1 else ""
                if entity in ENTITIES:
                    print(ENTITIES[entity], end="")
                    idx = end_idx + 1
                    continue

            print(c, end="")
        idx += 1


if __name__ == "__main__":
    import sys

    load(URL(sys.argv[1] if len(sys.argv) > 1 else ""))
