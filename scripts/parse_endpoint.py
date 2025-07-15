import undetected_chromedriver as uc
import time
import argparse
import sys
from typing import List, Optional

# Default detection keywords
DEFAULT_NOT_FOUND_KEYWORDS = ["404", "not found", "tidak ditemukan"]

def parse_args():
    parser = argparse.ArgumentParser(description="Check a list of URLs using Selenium.")
    parser.add_argument("-i", "--input", required=True, help="Input file with list of URLs")
    parser.add_argument("-o", "--output", help="Output file to save only valid (non-404) URLs")
    parser.add_argument("-d", "--delay", type=int, default=1, help="Delay between requests in seconds (default: 1)")
    parser.add_argument("--timeout", type=int, default=10, help="Page load timeout in seconds (default: 10)")
    parser.add_argument("--not-found-keywords", type=str,
                        help="Comma-separated keywords to detect 'not found' pages")
    return parser.parse_args()

def load_urls(filepath: str) -> List[str]:
    try:
        with open(filepath, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[!] File not found: {filepath}")
        sys.exit(1)

def setup_driver(timeout: int) -> uc.Chrome:
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(timeout)
    return driver

def is_not_found(title: str, source: str, keywords: List[str]) -> bool:
    combined = (title + " " + source).lower()
    return any(keyword.lower() in combined for keyword in keywords)

def check_url(driver: uc.Chrome, url: str, delay: int, not_found_keywords: List[str]) -> str:
    try:
        driver.get(url)
        time.sleep(delay)
        title = driver.title
        source = driver.page_source

        if is_not_found(title, source, not_found_keywords):
            return "not_found"
        return "ok"
    except Exception as e:
        return f"error: {e.__class__.__name__}: {str(e).splitlines()[0]}"

def save_valid_url(output_file: str, url: str):
    with open(output_file, "a") as f:
        f.write(url + "\n")

def process_urls(urls: List[str], delay: int, timeout: int, output_file: Optional[str], not_found_keywords: List[str]):
    driver = setup_driver(timeout)
    try:
        for index, url in enumerate(urls, 1):
            print(f"[{index}/{len(urls)}] Visiting: {url}")
            status = check_url(driver, url, delay, not_found_keywords)

            if status == "not_found":
                print("  [!] Page not found.")
            elif status == "ok":
                print("  [+] Page OK.")
                if output_file:
                    save_valid_url(output_file, url)
            else:
                print(f"  [!] Error: {status}")

    finally:
        driver.quit()

def main():
    args = parse_args()

    keywords = (
        [kw.strip() for kw in args.not_found_keywords.split(",")]
        if args.not_found_keywords
        else DEFAULT_NOT_FOUND_KEYWORDS
    )

    urls = load_urls(args.input)
    process_urls(urls, args.delay, args.timeout, args.output, keywords)

if __name__ == "__main__":
    main()
