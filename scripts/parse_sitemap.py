import argparse
import requests
import xml.etree.ElementTree as ET
import time
import logging
import gzip
import io
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

checked_sitemaps = set()
all_urls = set()
lock = Lock()


def get_namespace(tag):
    if tag.startswith("{"):
        return tag[1:].split("}")[0]
    return ""


def fetch_sitemap_urls(
    sitemap_url, depth, max_depth, max_urls, timeout, delay, retries
):
    with lock:
        if sitemap_url in checked_sitemaps or len(all_urls) >= max_urls:
            return
        checked_sitemaps.add(sitemap_url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "application/xml, text/xml;q=0.9, */*;q=0.8",
    }

    for attempt in range(1, retries + 1):
        try:
            time.sleep(delay)
            response = requests.get(sitemap_url, headers=headers, timeout=timeout)

            if response.status_code != 200:
                logging.error(
                    f"Failed to fetch {sitemap_url} (HTTP {response.status_code})"
                )
                return

            raw_content = response.content
            content_type = response.headers.get("Content-Type", "")
            if "gzip" in content_type or sitemap_url.endswith(".gz"):
                raw_content = gzip.decompress(raw_content)

            root = ET.fromstring(raw_content)
            namespace_uri = get_namespace(root.tag)
            ns = {"ns": namespace_uri} if namespace_uri else {}

            # Add URLs
            for tag in root.findall("ns:url", ns):
                loc = tag.find("ns:loc", ns)
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    with lock:
                        if url not in all_urls and len(all_urls) < max_urls:
                            all_urls.add(url)

            # Find nested sitemaps
            nested = []
            for tag in root.findall("ns:sitemap", ns):
                loc = tag.find("ns:loc", ns)
                if loc is not None and loc.text:
                    nested_url = loc.text.strip()
                    logging.info(f"Depth {depth} -> Nested: {nested_url}")
                    if depth < max_depth:
                        nested.append((nested_url, depth + 1))

            return nested  # Return nested sitemaps for further processing

        except Exception as e:
            logging.warning(f"[!] Error ({sitemap_url}): {e}")

    logging.error(f"Failed to fetch {sitemap_url} after {retries} retries")


def threaded_crawler(
    sitemap_urls, max_depth, max_urls, timeout, delay, retries, threads
):
    queue = [(url, 0) for url in sitemap_urls]

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []

        while queue:
            current_batch = []
            for url, depth in queue:
                future = executor.submit(
                    fetch_sitemap_urls,
                    url,
                    depth,
                    max_depth,
                    max_urls,
                    timeout,
                    delay,
                    retries,
                )
                futures.append(future)
                current_batch.append(future)
            queue = []  # clear queue for next nested layer

            for future in as_completed(current_batch):
                result = future.result()
                if result:
                    queue.extend(result)
                if len(all_urls) >= max_urls:
                    logging.warning("Max URL limit reached globally.")
                    return


def main():
    parser = argparse.ArgumentParser(description="Fast threaded sitemap parser")
    parser.add_argument("-i", "--input", required=True, help="File with sitemap URLs")
    parser.add_argument(
        "-o", "--output", required=True, help="File to save extracted URLs"
    )
    parser.add_argument(
        "--max-depth", type=int, default=5, help="Maximum recursion depth"
    )
    parser.add_argument(
        "--max-urls", type=int, default=10000, help="Maximum total URLs to extract"
    )
    parser.add_argument("--timeout", type=int, default=10, help="Timeout per request")
    parser.add_argument(
        "--delay", type=float, default=0.2, help="Delay per request (per thread)"
    )
    parser.add_argument("--retries", type=int, default=2, help="Retry attempts")
    parser.add_argument("--threads", type=int, default=10, help="Number of threads")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    try:
        with open(args.input, "r", encoding="utf-8", errors="replace") as f:
            sitemap_urls = [
                line.strip()
                for line in f
                if re.search(
                    r"(sitemap.*\.xml|\.xml(\.gz)?$)", line.strip(), re.IGNORECASE
                )
            ]
    except Exception as e:
        logging.error(f"Error reading input: {e}")
        return

    if not sitemap_urls:
        logging.error("No valid sitemap URLs found.")
        return

    threaded_crawler(
        sitemap_urls,
        args.max_depth,
        args.max_urls,
        args.timeout,
        args.delay,
        args.retries,
        args.threads,
    )

    try:
        with open(args.output, "w") as out:
            for url in sorted(all_urls):
                out.write(url + "\n")
        logging.info(f"[+] Done. {len(all_urls)} URLs saved to {args.output}")
        logging.info(f"[+] {len(checked_sitemaps)} sitemaps checked.")
    except Exception as e:
        logging.error(f"Error writing output: {e}")


if __name__ == "__main__":
    main()
