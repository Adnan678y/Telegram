from flask import Flask, request, Response
import requests
from urllib.parse import urljoin

app = Flask(__name__)

# Headers to mimic a real browser request
HEADERS = {
    "Referer": "https://megacloud.club/",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
}

@app.route('/proxy')
def proxy():
    """ Main proxy endpoint. 
    - If ?type=segment, fetches as a segment.
    - If URL ends with .m3u8, fetches as a playlist.
    """
    url = request.args.get('url')
    if not url:
        return "Missing URL", 400

    force_type = request.args.get('type')
    if force_type == "segment":
        return proxy_segment(url)

    if url.lower().endswith(".m3u8"):
        return proxy_m3u8(url)
    
    return proxy_segment(url)

def proxy_m3u8(url):
    """Fetches and modifies M3U8 playlists to go through the proxy."""
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            return f"Failed to fetch {url}", 500

        content = response.text
        if not content.lstrip().startswith("#EXTM3U"):
            return proxy_segment(url)

        base_url = url.rsplit('/', 1)[0] + "/"
        modified_lines = []
        for line in content.splitlines():
            if line.startswith("#") or not line.strip():
                modified_lines.append(line)
            else:
                resolved_url = urljoin(base_url, line.strip())
                proxied_url = f"/proxy?url={resolved_url}"
                modified_lines.append(proxied_url)

        return Response("\n".join(modified_lines), content_type="application/vnd.apple.mpegurl")

    except Exception as e:
        return f"Error: {str(e)}", 500

def proxy_segment(url):
    """Fetches and streams segment files (TS files)."""
    try:
        response = requests.get(url, headers=HEADERS, stream=True)
        if response.status_code != 200:
            return f"Failed to fetch {url}", 500

        content_type = response.headers.get("Content-Type", "application/octet-stream")
        return Response(response.raw, content_type=content_type)

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
