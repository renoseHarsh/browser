import socket
import ssl

ConnectionPool = {}


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

    def request(self) -> str:
        if self.schema == "file":
            with open(self.path, "r", encoding="utf8") as f:
                return f.read()

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
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
            ConnectionPool[pool_key] = s

        headers = {"Host": self.host, "User-Agent": "timid/1.0"}

        request = f"GET {self.path} HTTP/1.1\r\n"

        for key, value in headers.items():
            request += f"{key}: {value}\r\n"

        request += "\r\n"
        s.send(request.encode("utf8"))

        response = s.makefile("rb")
        _, _, _ = response.readline().decode("utf8").split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        body_bytes = response.read(int(response_headers.get("content-length", -1)))
        content = body_bytes.decode("utf8")
        return content


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
