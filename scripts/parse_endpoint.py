import sys
import time
import argparse
from typing import List, Optional

import undetected_chromedriver as uc

# Default keywords that indicate "Not Found" pages
DEFAULT_NOT_FOUND_KEYWORDS = ["404", "not found", "tidak ditemukan"]
DEFAULT_DRIVER_PATH = "/usr/local/bin/chromedriver"

def parse_args():
    parser = argparse.ArgumentParser(description="Check URLs using Selenium (undetected_chromedriver).")
    parser.add_argument("-i", "--input", required=True, help="Input file with list of URLs")
    parser.add_argument("-o", "--output", help="File to save valid (non-404) URLs")
    parser.add_argument("-d", "--delay", type=int, default=1, help="Delay between requests in seconds (default: 1)")
    parser.add_argument("--timeout", type=int, default=10, help="Page load timeout in seconds (default: 10)")
    parser.add_argument("--not-found-keywords", type=str,
                        help="Comma-separated keywords to detect 'not found' pages")
    parser.add_argument("--driver-path", type=str,
                        help=f"Optional path to ChromeDriver executable (default: {DEFAULT_DRIVER_PATH})")
    parser.add_argument("--retries", type=int, default=3,
                        help="Number of retries on failure per URL (default: 3)")
    return parser.parse_args()

def load_urls(filepath: str) -> List[str]:
    try:
        with open(filepath, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[!] File not found: {filepath}")
        sys.exit(1)

def setup_driver(timeout: int, driver_path: Optional[str] = None) -> uc.Chrome:
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Use default path unless overridden
    path_to_use = driver_path if driver_path else DEFAULT_DRIVER_PATH

    try:
        driver = uc.Chrome(
            options=options,
            driver_executable_path=path_to_use
        )
        driver.set_page_load_timeout(timeout)
        return driver
    except Exception as e:
        print(f"[!] ERROR during driver setup using path '{path_to_use}':", e)
        sys.exit(1)

def is_not_found(title: str, source: str, keywords: List[str]) -> bool:
    content = f"{title} {source}".lower()
    return any(keyword.lower() in content for keyword in keywords)

def check_url(driver: uc.Chrome, url: str, delay: int, keywords: List[str], retries: int = 3) -> str:
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            time.sleep(delay)
            title = driver.title
            source = driver.page_source

            if is_not_found(title, source, keywords):
                return "not_found"
            return "ok"

        except Exception as e:
            message = str(e)
            err = f"error: {e.__class__.__name__}: {message.splitlines()[0]}"
            print(f"  [!] Attempt {attempt} failed: {err}")

            # Skip retries if it's a DNS resolution error
            if "ERR_NAME_NOT_RESOLVED" in message:
                print("  [!] Skipping retries due to DNS resolution failure.")
                return err

            if attempt < retries:
                time.sleep(delay)  # short delay before retrying
            else:
                return err

    return "error: UnknownError"

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
    retries: int = 3
):
    driver = setup_driver(timeout, driver_path)
    try:
        for idx, url in enumerate(urls, 1):
            print(f"[{idx}/{len(urls)}] Visiting: {url}")
            status = check_url(driver, url, delay, keywords, retries)

            if status == "not_found":
                print("  [!] Page not found.")
            elif status == "ok":
                print("  [+] Page OK.")
                if output_file:
                    save_valid_url(output_file, url)
    finally:
        driver.quit()

def main():
    args = parse_args()

    keywords = (
        [kw.strip() for kw in args.not_found_keywords.split(",")]
        if args.not_found_keywords else DEFAULT_NOT_FOUND_KEYWORDS
    )

    urls = load_urls(args.input)
    process_urls(
        urls,
        delay=args.delay,
        timeout=args.timeout,
        output_file=args.output,
        keywords=keywords,
        driver_path=args.driver_path,
        retries=args.retries
    )

if __name__ == "__main__":
    main()
