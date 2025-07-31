import os
import pandas as pd
from urllib.parse import urlparse

# --------------------------
# Reason logic for ports
# --------------------------
def port_reason(port, service):
    critical_ports = [22, 23, 3306, 5432, 21]
    if port in critical_ports:
        return "Critical service or sensitive port"
    if service.lower() in ["ftp", "ssh", "mysql", "postgresql"]:
        return "Common service with known risks"
    return "Standard port/service"

# --------------------------
# Reason logic for endpoints
# --------------------------
def endpoint_reason(path):
    path = path.lower()

    high_keywords = [
        '/admin', '/upload', '/debug', '/shell', '/login', '/register',
        '/signup', '/signin', '/edit', '/delete', '/remove', '/config',
        '/backup', '/restore', '/reset', '/change-password', '/passwd',
        '/filemanager', '/console', '/exec', '/command', '/cgi-bin',
        '/manage', '/dashboard', '/settings', '/admincp'
    ]
    auth_keywords = ['/auth', '/login', '/logout', '/register', '/signup', '/signin', '/verify', '/token', '/session']
    user_keywords = ['/user', '/profile', '/account']
    internal_api_keywords = ['/admin-api', '/internal', '/private', '/config']
    monitoring_keywords = ['/status', '/info']
    integration_keywords = ['/webhook', '/callback', '/callback-url']
    versioned_api_keywords = ['/v1', '/v2', '/v3', '/v4', '/v5', '/v6', '/v7', '/v8', '/v9', '/latest']
    generic_api_keywords = ['/api', '/graphql', '/soap', '/service', '/query', '/docs', '/swagger', '/openapi', '/search', '/report', '/analytics']
    file_keywords = ['/download', '/file', '/view', '/document', '/attachment']
    payment_keywords = ['/payment', '/checkout', '/order', '/invoice', '/billing', '/transaction']
    security_keywords = ['/redirect', '/url', '/proxy', '/forward', '/next', '/return']
    debug_keywords = ['/log', '/trace', '/stack', '/error', '/dump']
    dev_keywords = ['/test', '/dev', '/staging', '/mock', '/sandbox', '/qa', '/demo', '/sample']
    cms_keywords = ['/wp-admin', '/wp-json', '/drupal', '/joomla', '/laravel', '/strapi']

    categories = [
        (high_keywords, "Sensitive or high-risk endpoint", 100),
        (auth_keywords, "Authentication/Authorization endpoint", 90),
        (internal_api_keywords, "Internal/Admin API endpoint", 85),
        (payment_keywords, "Payment or billing-related endpoint", 80),
        (file_keywords, "File handling endpoint", 75),
        (security_keywords, "Redirection or SSRF-prone endpoint", 70),
        (debug_keywords, "Debug or logging endpoint", 65),
        (integration_keywords, "Webhook/Callback endpoint", 60),
        (user_keywords, "User/Account-related endpoint", 55),
        (versioned_api_keywords, "Versioned API endpoint", 50),
        (generic_api_keywords, "General API or Search/Analytics endpoint", 45),
        (cms_keywords, "CMS-specific or backend-related endpoint", 40),
        (dev_keywords, "Development or staging/test endpoint", 30),
        (monitoring_keywords, "Monitoring/Health endpoint", 10),
    ]

    for keywords, reason, score in categories:
        if any(k in path for k in keywords):
            return reason, score

    return "Generic or static-looking endpoint", 0


# --------------------------
# Load subdomains
# --------------------------
def load_subdomains(file_path):
    rows = []
    with open(file_path) as f:
        for line in f:
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 2:
                    rows.append({
                        "Subdomain": parts[0],
                        "IP": parts[1]
                    })
    return pd.DataFrame(rows)

# --------------------------
# Load ports
# --------------------------
def load_ports(file_path):
    rows = []
    with open(file_path) as f:
        for line in f:
            if not line.strip() or line.strip().startswith("#"):
                continue
            parts = line.strip().split()
            if len(parts) == 3:
                ip, port, service = parts
                port = int(port)
                reason = port_reason(port, service)
                rows.append({
                    "IP": ip,
                    "Port": port,
                    "Service": service,
                    "Reason to Test First": reason
                })
    return pd.DataFrame(rows)

# --------------------------
# Load endpoints
# --------------------------
def load_endpoints(file_path):
    rows = []
    with open(file_path) as f:
        for line in f:
            url = line.strip().strip('"').strip("’")
            if url:
                try:
                    parsed = urlparse(url)
                    protocol = parsed.scheme.upper()
                    path = parsed.path or "/"
                    ext = os.path.splitext(path)[1].lower().lstrip(".") or "none"
                    reason = endpoint_reason(path)

                    rows.append({
                        "URL (Endpoint)": url,
                        "Protocol": protocol,
                        "File Extension": ext,
                        "Reason to Test First": reason[0],
                        "Notes": reason[1],
                    })
                except Exception:
                    rows.append({
                        "URL (Endpoint)": url,
                        "Protocol": "Unknown",
                        "File Extension": "error",
                        "Reason to Test First": "Could not parse URL",
                        "Notes": "0"
                    })
    df = pd.DataFrame(rows)
    return df.sort_values(by="File Extension")

# --------------------------
# Main function
# --------------------------
def generate_dashboard(subdomain_file, port_file, endpoint_file, output_excel):
    domain_df = load_subdomains(subdomain_file)
    port_df = load_ports(port_file)
    endpoint_df = load_endpoints(endpoint_file)

    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        domain_df.to_excel(writer, sheet_name="Domain", index=False)
        port_df.to_excel(writer, sheet_name="Ports", index=False)
        endpoint_df.to_excel(writer, sheet_name="Endpoints", index=False)

    print(f"[+] Excel dashboard generated: {output_excel}")

# --------------------------
# CLI
# --------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate Dashboard Excel with Domain, Ports, Endpoints sheets")
    parser.add_argument("--subdomains", required=True, help="Subdomain file (subdomain IP)")
    parser.add_argument("--ports", required=True, help="Port file (IP port service)")
    parser.add_argument("--endpoints", required=True, help="Endpoint file with full URLs")
    parser.add_argument("-o", "--output", default="pt_dashboard.xlsx", help="Output Excel filename")
    args = parser.parse_args()

    generate_dashboard(args.subdomains, args.ports, args.endpoints, args.output)
