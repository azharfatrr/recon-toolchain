import sys
import time
import argparse
import logging
import random
from typing import List, Optional, Tuple
from collections import defaultdict, deque
from urllib.parse import urlparse
from fnmatch import fnmatch

import undetected_chromedriver as uc

# Default keywords that indicate "Not Found" pages
DEFAULT_NOT_FOUND_KEYWORDS = ["404", "not found", "tidak ditemukan"]
DEFAULT_DRIVER_PATH = "/usr/local/bin/chromedriver"  
# DEFAULT_DRIVER_PATH = ""  # Adjust this path as needed

SKIP_PATTERNS = [
    "/tag/*",  # Add more patterns if needed
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check URLs using Selenium (undetected_chromedriver)."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Input file with list of URLs"
    )
    parser.add_argument("-o", "--output", help="File to save valid (non-404) URLs")
    parser.add_argument(
        "-d",
        "--delay",
        type=int,
        default=1,
        help="Initial delay between requests in seconds (default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Page load timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--not-found-keywords",
        type=str,
        help="Comma-separated keywords to detect 'not found' pages",
    )
    parser.add_argument(
        "--driver-path",
        type=str,
        help=f"Optional path to ChromeDriver executable (default: {DEFAULT_DRIVER_PATH})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Number of retries on failure per URL (default: 2)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    return parser.parse_args()


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
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
    
def should_skip_path(url: str, skip_patterns: List[str]) -> bool:
    parsed = urlparse(url)
    path = parsed.path

    for pattern in skip_patterns:
        if fnmatch(path, pattern):
            return True
    return False

def setup_driver(timeout: int, driver_path: Optional[str] = None) -> uc.Chrome:
    options = uc.ChromeOptions()

    # Disable image loading
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    # Additional options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Not using headless to simulate browser more naturally
    # options.add_argument("--headless=new")  # Do NOT enable this

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


def check_url(
    driver: uc.Chrome, url: str, delay: int, keywords: List[str], retries: int = 3
) -> Tuple[str, int]:
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            time.sleep(random.uniform(0, delay))

            title = driver.title
            source = driver.page_source
            logging.info("  [Title]: %s", title)

            # Check if WAF is still blocking (Cloudflare-style)
            if "one moment" in source.lower() or "one moment" in title.lower():
                logging.info("  [!] WAF block detected.")
                logging.info(
                    "  [~] Retrying due to WAF (attempt %d/%d)...", attempt + 1, retries
                )
                delay = min(delay + 2, 15)
                time.sleep(delay)
                if attempt >= retries:
                    return "waf_blocked", delay

            if is_not_found(title, source[:100], keywords):
                return "not_found", max(delay - 1, 1)

            return "ok", max(delay - 1, 1)

        except Exception as e:
            message = str(e)
            err = f"error: {e.__class__.__name__}: {message.splitlines()[0]}"
            logging.warning(f"  [!] Attempt {attempt} failed: {err}")

            if "ERR_NAME_NOT_RESOLVED" in message:
                logging.warning("  [!] Skipping retries due to DNS resolution failure.")
                return err, delay

            if attempt >= retries:
                return err, delay

    return "error: UnknownError", delay


def save_valid_url(output_file: str, url: str):
    with open(output_file, "a") as f:
        f.write(url + "\n")


def process_urls(
    urls: List[str],
    delay: int,
    timeout: int,
    output_file: Optional[str],
    keywords: List[str],
    driver_path: Optional[str] = None,
    retries: int = 3,
):
    driver = setup_driver(timeout, driver_path)
    try:
        # Memory-efficient status tracker (only last 3 statuses per prefix)
        common_path_status = defaultdict(lambda: deque(maxlen=3))
        skipped_prefixes = set()

        for idx, url in enumerate(urls, 1):
            common_path = get_common_prefix(url)
            
            # Skip URLs that match any of the skip patterns
            if should_skip_path(url, SKIP_PATTERNS):
                logging.info(f"[~] Skipping {url} (matched skip pattern)")
                continue

            # If we already skipped this prefix, skip this URL
            if common_path in skipped_prefixes:
                logging.info(f"[~] Skipping {url} (prefix {common_path} previously skipped)")
                continue

            # If 3 same consecutive results seen for this path, skip the rest
            recent = common_path_status[common_path]
            logging.info(f"[~] Recent statuses for {common_path}: {list(recent)}")
            if len(recent) == 3 and len(set(recent)) == 1:
                logging.info(f"[~] Skipping rest of URLs in: {common_path} (3x '{recent[0]}')")
                skipped_prefixes.add(common_path)
                continue

            logging.info(f"[{idx}/{len(urls)}] Visiting: {url}")
            status, delay = check_url(driver, url, delay, keywords, retries)

            # Track last 3 statuses
            common_path_status[common_path].append(status)

            if status == "not_found":
                logging.info("  [!] Page not found.")
            elif status == "ok":
                logging.info("  [+] Page OK.")
                if output_file:
                    save_valid_url(output_file, url)
            elif status == "waf_blocked":
                logging.info("  [!] WAF detected. Delay increased.")
            else:
                logging.info(f"  [!] {status}")

            logging.info(f"  [~] Next delay: {delay} seconds")

    finally:
        driver.quit()


def main():
    args = parse_args()
    setup_logging(args.verbose)

    keywords = (
        [kw.strip() for kw in args.not_found_keywords.split(",")]
        if args.not_found_keywords
        else DEFAULT_NOT_FOUND_KEYWORDS
    )

    urls = load_urls(args.input)
    process_urls(
        urls,
        delay=args.delay,
        timeout=args.timeout,
        output_file=args.output,
        keywords=keywords,
        driver_path=args.driver_path,
        retries=args.retries,
    )


if __name__ == "__main__":
    main()
