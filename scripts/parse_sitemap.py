import argparse
import requests
import xml.etree.ElementTree as ET
import time

checked_sitemaps = set()


def fetch_sitemap_urls(
    sitemap_url, depth, max_depth, all_urls, max_urls, timeout, delay, retries
):
    if sitemap_url in checked_sitemaps:
        return

    if depth > max_depth:
        print(f"[!] Max depth reached at {sitemap_url}")
        return

    if len(all_urls) >= max_urls:
        print(f"[!] Max URL limit reached ({max_urls}). Skipping {sitemap_url}")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "application/xml, text/xml;q=0.9, */*;q=0.8",
    }

    checked_sitemaps.add(sitemap_url)

    for attempt in range(1, retries + 1):
        try:
            time.sleep(delay)
            response = requests.get(sitemap_url, headers=headers, timeout=timeout)

            if response.status_code != 200:
                print(f"[!] Failed to fetch {sitemap_url} (HTTP {response.status_code})")
                return

            root = ET.fromstring(response.content)
            namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Extract URL entries
            for tag in root.findall("ns:url", namespace):
                loc = tag.find("ns:loc", namespace)
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    if url not in all_urls:
                        all_urls.add(url)
                        if len(all_urls) >= max_urls:
                            print(f"[!] Max URL limit reached while processing {sitemap_url}")
                            return

            # Extract nested sitemap entries
            for tag in root.findall("ns:sitemap", namespace):
                loc = tag.find("ns:loc", namespace)
                if loc is not None and loc.text:
                    nested_sitemap_url = loc.text.strip()
                    print(f"[*] Depth {depth} -> Nested: {nested_sitemap_url}")
                    fetch_sitemap_urls(
                        nested_sitemap_url,
                        depth + 1,
                        max_depth,
                        all_urls,
                        max_urls,
                        timeout,
                        delay,
                        retries,
                    )

            return  # Success, exit retry loop

        except requests.exceptions.Timeout:
            print(f"[!] Timeout ({timeout}s) on attempt {attempt}/{retries} for {sitemap_url}")
        except ET.ParseError as e:
            print(f"[!] XML parse error in {sitemap_url}: {e}")
            return
        except Exception as e:
            print(f"[!] Error on attempt {attempt}/{retries} for {sitemap_url}: {e}")

    print(f"[!] Failed to fetch {sitemap_url} after {retries} retries")


def main():
    parser = argparse.ArgumentParser(
        description="Recursively extract endpoint URLs from sitemap.xml files"
    )
    parser.add_argument("-i", "--input", required=True, help="File with sitemap URLs")
    parser.add_argument("-o", "--output", required=True, help="File to save extracted URLs")
    parser.add_argument("--max-depth", type=int, default=5, help="Maximum recursion depth (default: 5)")
    parser.add_argument("--max-urls", type=int, default=10000, help="Maximum number of URLs to extract (default: 10000)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds (default: 0.5)")
    parser.add_argument("--retries", type=int, default=3, help="Number of retry attempts per request (default: 3)")
    args = parser.parse_args()

    try:
        with open(args.input, "r") as infile:
            sitemap_urls = [line.strip() for line in infile if "sitemap" in line]
    except Exception as e:
        print(f"[!] Failed to read input file: {e}")
        return

    all_urls = set()

    for sitemap_url in sitemap_urls:
        print(f"[*] Root: {sitemap_url}")
        fetch_sitemap_urls(
            sitemap_url,
            depth=0,
            max_depth=args.max_depth,
            all_urls=all_urls,
            max_urls=args.max_urls,
            timeout=args.timeout,
            delay=args.delay,
            retries=args.retries,
        )
        if len(all_urls) >= args.max_urls:
            break

    with open(args.output, "w") as outfile:
        for url in sorted(all_urls):
            outfile.write(url + "\n")

    print(f"[+] Done. {len(all_urls)} URLs written to {args.output}")
    print(f"[+] {len(checked_sitemaps)} sitemap files checked")


if __name__ == "__main__":
    main()
