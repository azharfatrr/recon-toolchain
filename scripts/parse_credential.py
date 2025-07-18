import os
import re
import argparse

# Original credential-related patterns
CREDENTIAL_PATTERNS = [
    ("username assignment", r"username\s*[:=]\s*['\"]?[\w@.-]+['\"]?"),
    ("password assignment", r"password\s*[:=]\s*['\"]?[\w@.-]+['\"]?"),
    ("email assignment",    r"email\s*[:=]\s*['\"]?[\w.-]+@[\w.-]+['\"]?"),
    ("token assignment",    r"token\s*[:=]\s*['\"][a-zA-Z0-9_\-\.]{8,}['\"]"),
    ("input field",         r"<input[^>]+type=['\"]?(password|email)['\"]?[^>]*>"),
    ("JSON.stringify",      r"JSON\.stringify\s*\(\s*{[^}]*['\"]?(username|password)['\"]?\s*:"),
]

# Secret scanning patterns from your dictionary
SECRET_PATTERNS = {
    'google_api': r'AIza[0-9A-Za-z-_]{35}',
    'firebase': r'AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}',
    'google_oauth': r'ya29\.[0-9A-Za-z\-_]+',
    'amazon_aws_access_key_id': r'A[SK]IA[0-9A-Z]{16}',
    'amazon_mws_auth_token': r'amzn\.mws\.[0-9a-f\-]{36}',
    'amazon_aws_url': r's3\.amazonaws.com[/]+|[a-zA-Z0-9_-]*\.s3\.amazonaws.com',
    'amazon_aws_url2': r"([a-zA-Z0-9-._]+\.s3\.amazonaws\.com|s3://[a-zA-Z0-9-._]+|s3-[a-zA-Z0-9-._/]+|s3.amazonaws.com/[a-zA-Z0-9-._]+|s3.console.aws.amazon.com/s3/buckets/[a-zA-Z0-9-._]+)",
    'facebook_access_token': r'EAACEdEose0cBA[0-9A-Za-z]+',
    'mailgun_api_key': r'key-[0-9a-zA-Z]{32}',
    'github_access_token': r'[a-zA-Z0-9_-]*:[a-zA-Z0-9_\-]+@github\.com*',
    'rsa_private_key': r'-----BEGIN RSA PRIVATE KEY-----',
    'ssh_dsa_private_key': r'-----BEGIN DSA PRIVATE KEY-----',
    'ssh_dc_private_key': r'-----BEGIN EC PRIVATE KEY-----',
    'pgp_private_block': r'-----BEGIN PGP PRIVATE KEY BLOCK-----',
    'SSH_privKey': r'[-]+BEGIN [^\s]+ PRIVATE KEY[-]+[\s\S]*?[-]+END [^\s]+ PRIVATE KEY[-]+',
    'json_web_token': r'ey[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$',
}

def scan_file(file_path, exclude_keywords):
    matches = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_number, line in enumerate(f, 1):
                # Scan original patterns
                for label, pattern in CREDENTIAL_PATTERNS:
                    if any(ex in label.lower() for ex in exclude_keywords):
                        continue
                    for match in re.findall(pattern, line, re.IGNORECASE):
                        matches.append((label, line_number, match.strip()))

                # Scan secret patterns
                for label, pattern in SECRET_PATTERNS.items():
                    if any(ex in label.lower() for ex in exclude_keywords):
                        continue
                    for match in re.findall(pattern, line, re.IGNORECASE):
                        matches.append((label, line_number, str(match).strip()))
    except Exception:
        pass  # Skip unreadable files
    return matches

def main():
    parser = argparse.ArgumentParser(description="Scan files for secrets and credentials.")
    parser.add_argument("--input", "-i", required=True, help="Input folder to scan")
    parser.add_argument("--output", "-o", help="Optional output file to write findings")
    parser.add_argument("--exclude", "-e", nargs="*", default=[], help="Exclude keywords (e.g., aws password slack)")
    args = parser.parse_args()

    excluded_keys = [e.lower() for e in args.exclude]
    all_results = []

    print(f"[*] Scanning: {args.input}")
    if excluded_keys:
        print(f"[*] Excluding patterns containing: {excluded_keys}\n")

    for root, _, files in os.walk(args.input):
        for file in files:
            path = os.path.join(root, file)
            results = scan_file(path, excluded_keys)
            if results:
                all_results.append((path, results))
                print(f"[!] Found in: {path}")
                for label, line_number, match in results:
                    print(f"    - Line {line_number}: {label}: {match[:120]}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as out:
            for path, results in all_results:
                out.write(f"[!] Found in: {path}\n")
                for label, line_number, match in results:
                    out.write(f"    - Line {line_number}: {label}: {match[:120]}\n")
        print(f"\n[*] Results written to: {args.output}")

if __name__ == "__main__":
    main()
