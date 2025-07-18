from curses import ERR
import sys
import time
import argparse
import logging
import random
import hashlib
import os
from typing import List, Optional, Tuple
from collections import defaultdict, deque
from urllib.parse import urlparse
from fnmatch import fnmatch

import undetected_chromedriver as uc
from tqdm import tqdm

DEFAULT_NOT_FOUND_KEYWORDS = ["404", "not found", "tidak ditemukan"]
DEFAULT_DRIVER_PATH = "/usr/local/bin/chromedriver"
SKIP_PATTERNS = ["*/tag/*", "*/id/*", "*/en/*"]
ERROR_SIGNATURES = [
    "ERR_EMPTY_RESPONSE",
    "This site can’t be reached",
    "No data received",
    "net::ERR_EMPTY_RESPONSE",
    "Error code: ERR_EMPTY_RESPONSE",
]

def parse_args():
    parser = argparse.ArgumentParser(description="Check URLs using Selenium.")
    parser.add_argument("-i", "--input", required=True, help="Input file with list of URLs")
    parser.add_argument("-o", "--output", help="File to save valid (non-404) URLs")
    parser.add_argument("-d", "--delay", type=int, default=1, help="Initial delay between requests (default: 1)")
    parser.add_argument("--timeout", type=int, default=10, help="Page load timeout in seconds (default: 10)")
    parser.add_argument("--not-found-keywords", type=str, help="Comma-separated keywords to detect 'not found' pages")
    parser.add_argument("--driver-path", type=str, help=f"Path to ChromeDriver (default: {DEFAULT_DRIVER_PATH})")
    parser.add_argument("--retries", type=int, default=2, help="Number of retries on failure (default: 2)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--html-dump-dir", type=str, help="Directory to save raw HTML of each successful page")
    return parser.parse_args()

def setup_logging(verbose: bool):
    level = logging.INFO if verbose else logging.CRITICAL
    logging.basicConfig(level=level, format="%(message)s")

def load_urls(filepath: str) -> List[str]:
    try:
        with open(filepath, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error(f"[!] File not found: {filepath}")
        sys.exit(1)

def get_common_prefix(url: str) -> str:
    parts = urlparse(url)
    path_parts = [p for p in parts.path.strip("/").split("/") if p]
    if len(path_parts) > 2:
        prefix_path = "/".join(path_parts[:-1])
        return f"{parts.scheme}://{parts.netloc}/{prefix_path}/"
    else:
        return str(random.randint(100000, 999999))
    
def get_path_without_query(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path.rstrip("/")

def should_skip_path(url: str, skip_patterns: List[str]) -> bool:
    parsed = urlparse(url)
    return any(fnmatch(parsed.path, pattern) for pattern in skip_patterns)

def setup_driver(timeout: int, driver_path: Optional[str] = None) -> uc.Chrome:
    options = uc.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")

    path_to_use = driver_path if driver_path else DEFAULT_DRIVER_PATH
    try:
        driver = uc.Chrome(options=options, driver_executable_path=path_to_use)
        driver.set_page_load_timeout(timeout)
        return driver
    except Exception as e:
        logging.error(f"[!] ERROR during driver setup using path '{path_to_use}': {e}")
        sys.exit(1)

def is_not_found(title: str, source: str, keywords: List[str]) -> bool:
    content = f"{title} {source}".lower()
    return any(keyword.lower() in content for keyword in keywords)

def url_to_filename(url: str) -> str:
    parsed = urlparse(url)
    clean_path = parsed.path.strip("/").replace("/", "_") or "root"
    base = f"{parsed.netloc}_{clean_path}"
    hashed = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{base}_{hashed}.html"

def check_url(driver: uc.Chrome, url: str, delay: int, keywords: List[str], retries: int = 3) -> Tuple[str, int, Optional[str]]:
    """
    Attempts to load a URL using the given WebDriver and returns the result status,
    updated delay, and page source if available.
    """
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            time.sleep(random.uniform(0, delay))

            title = driver.title
            source = driver.page_source.strip()
            # logging.info(f"[{attempt}/{retries}] Checking: {url} - Title: {title} - Source length: {len(source)}")

            # Check for empty or error-like response
            if not source:
                return "empty_response", delay, None
            if any(sig.lower() in source.lower() for sig in ERROR_SIGNATURES):
                return "empty_response", delay, None

            # Handle WAF or browser challenge
            if "one moment" in title.lower() or "one moment" in source.lower():
                delay = min(delay + 2, 15)
                time.sleep(delay)
                if attempt >= retries:
                    return "waf_blocked", delay, None
                continue

            # Detect not-found pages
            if is_not_found(title, source[:100], keywords):
                return "not_found", max(delay - 1, 1), source

            return "ok", max(delay - 1, 1), source

        except Exception as e:
            error_msg = str(e).lower()
            if "err_name_not_resolved" in error_msg:
                return "dns_error", delay, None
            if "err_empty_response" in error_msg:
                return "empty_response", delay, None
            if attempt >= retries:
                return f"error: {type(e).__name__}", delay, None

    return "error: UnknownError", delay, None

def save_valid_url(output_file: str, url: str):
    with open(output_file, "a") as f:
        f.write(url + "\n")

def save_html(html_dir: str, url: str, source: str, saved_hashes: set):
    content_hash = hashlib.md5(source.encode()).hexdigest()
    if content_hash in saved_hashes:
        return
    saved_hashes.add(content_hash)

    os.makedirs(html_dir, exist_ok=True)
    filename = url_to_filename(url)
    filepath = os.path.join(html_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(source)

def process_urls(
    urls: List[str],
    delay: int,
    timeout: int,
    output_file: Optional[str],
    keywords: List[str],
    driver_path: Optional[str] = None,
    retries: int = 3,
    html_dump_dir: Optional[str] = None,
    args=None,
):
    driver = setup_driver(timeout, driver_path)
    try:
        common_path_status = defaultdict(lambda: deque(maxlen=3))
        skipped_prefixes = set()
        saved_hashes = set()

        iterator = enumerate(urls, 1)
        if not args.verbose:
            iterator = tqdm(iterator, total=len(urls), desc="Checking URLs", unit="url")

        for idx, url in iterator:
            common_path = get_common_prefix(url)

            if should_skip_path(url, SKIP_PATTERNS):
                continue
            if common_path in skipped_prefixes:
                continue

            recent = common_path_status[common_path]
            if len(recent) == 3 and len(set(recent)) == 1:
                skipped_prefixes.add(common_path)
                continue

            if args.verbose:
                logging.info(f"[{idx}/{len(urls)}] Visiting: {url}")
            status, delay, source = check_url(driver, url, delay, keywords, retries)
            common_path_status[common_path].append(status)

            if args.verbose:
                if status == "not_found":
                    logging.info("  [!] Page not found.")
                elif status == "ok":
                    logging.info("  [+] Page OK.")
                elif status == "waf_blocked":
                    logging.info("  [!] WAF detected.")
                else:
                    logging.info(f"  [!] {status}")
                logging.info(f"  [~] Next delay: {delay} seconds")

            if status == "ok":
                if output_file:
                    save_valid_url(output_file, url)
                if html_dump_dir and source:
                    save_html(html_dump_dir, url, source, saved_hashes)

    finally:
        driver.quit()

def main():
    args = parse_args()
    setup_logging(args.verbose)
    keywords = [kw.strip() for kw in args.not_found_keywords.split(",")] if args.not_found_keywords else DEFAULT_NOT_FOUND_KEYWORDS
    urls = load_urls(args.input)
    process_urls(
        urls=urls,
        delay=args.delay,
        timeout=args.timeout,
        output_file=args.output,
        keywords=keywords,
        driver_path=args.driver_path,
        retries=args.retries,
        html_dump_dir=args.html_dump_dir,
        args=args,
    )

if __name__ == "__main__":
    main()
