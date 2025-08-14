import os
import re
import json
import argparse
import pandas as pd
from urllib.parse import urlparse
from openpyxl.utils import get_column_letter

# --------------------------
# Constants
# --------------------------
_ILLEGAL_CHARS_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")

CRITICAL_SERVICES = {
    21: (
        "FTP",
        "File transfer protocol",
        "Often allows anonymous access or weak credentials",
    ),
    22: (
        "SSH",
        "Secure remote login",
        "Potential for brute-force or weak key authentication",
    ),
    23: ("Telnet", "Remote login (unencrypted)", "Transmits credentials in plain text"),
    25: ("SMTP", "Email transfer", "Can be abused for spam or information leakage"),
    53: (
        "DNS",
        "Domain name resolution",
        "May allow zone transfers or amplification attacks",
    ),
    69: (
        "TFTP",
        "Trivial file transfer",
        "No authentication; can be abused to exfiltrate files",
    ),
    110: ("POP3", "Email retrieval", "Unencrypted credentials and messages"),
    111: (
        "RPCbind",
        "Remote procedure call mapping",
        "Can reveal services and aid exploitation",
    ),
    135: ("MS RPC", "Windows RPC service", "Used in many Windows exploits"),
    137: ("NetBIOS-NS", "NetBIOS name service", "Information disclosure"),
    138: ("NetBIOS-DGM", "NetBIOS datagram service", "Information disclosure"),
    139: ("NetBIOS-SSN", "NetBIOS session service", "SMB exploits"),
    143: ("IMAP", "Email retrieval", "Potential for credential theft"),
    161: (
        "SNMP",
        "Network management",
        "Weak community strings may expose config data",
    ),
    162: (
        "SNMP Trap",
        "Network management alerting",
        "Can be abused for network enumeration",
    ),
    389: ("LDAP", "Directory services", "May expose sensitive user and system info"),
    445: ("SMB", "File sharing", "Common vector for ransomware and exploits"),
    465: (
        "SMTPS",
        "Secure mail transfer",
        "Weak encryption configs may be exploitable",
    ),
    500: ("IKE", "VPN key exchange", "May allow VPN enumeration or MITM attacks"),
    512: ("rexec", "Remote execution", "Unauthenticated code execution risk"),
    513: ("rlogin", "Remote login (unencrypted)", "Plain text credentials"),
    514: (
        "syslog/rsh",
        "Logging / remote shell",
        "Log injection or remote shell access",
    ),
    873: ("rsync", "File synchronization", "May allow anonymous file access"),
    902: ("VMware ESXi", "VMware remote services", "Remote management risk"),
    1080: ("SOCKS", "Proxy service", "Open proxy can be abused for anonymity"),
    1433: ("MSSQL", "Microsoft SQL database", "May expose sensitive database data"),
    1521: ("Oracle DB", "Oracle database", "May expose sensitive database data"),
    2049: ("NFS", "Network file system", "May allow file share access"),
    2222: (
        "Alt SSH",
        "Alternate secure remote login",
        "Potential brute-force or weak key authentication",
    ),
    2375: (
        "Docker API",
        "Docker remote API",
        "Unauthenticated remote container control",
    ),
    2376: (
        "Docker API TLS",
        "Docker remote API over TLS",
        "Potential misconfigurations",
    ),
    27017: ("MongoDB", "NoSQL database", "No auth by default in older versions"),
    27018: (
        "MongoDB Cluster",
        "NoSQL database cluster comms",
        "Data exposure or takeover risk",
    ),
    27019: ("MongoDB Config", "NoSQL database config server", "Data exposure risk"),
    3306: ("MySQL", "SQL database", "May expose sensitive data"),
    3389: ("RDP", "Remote desktop", "Often targeted for remote compromise"),
    5000: ("Web service", "Development/debug service", "May expose internal tools"),
    5001: ("Alt HTTPS", "Alternate secure web service", "May expose admin panels"),
    5002: (
        "Alt Web Service",
        "Alternate web admin panel",
        "Possible exposure of internal systems",
    ),
    5432: ("PostgreSQL", "SQL database", "May expose sensitive data"),
    5900: ("VNC", "Remote desktop", "No encryption; susceptible to MITM"),
    5984: ("CouchDB", "NoSQL database", "No auth in older versions"),
    6000: ("X11", "X Window System", "May allow remote GUI access"),
    6379: ("Redis", "In-memory database", "No authentication in default config"),
    7001: ("WebLogic", "Java application server", "Known RCE vulnerabilities"),
    7002: (
        "WebLogic SSL",
        "Java application server over SSL",
        "Known RCE vulnerabilities",
    ),
    8000: ("HTTP-alt", "Alternate web service", "May expose admin panels"),
    8080: ("HTTP-alt", "Alternate web service", "May expose admin panels"),
    8081: ("HTTP-alt", "Alternate admin panel", "Often used for management interfaces"),
    8088: ("HTTP-alt", "Alternate admin panel", "Possible sensitive dashboard"),
    8181: ("HTTPS-alt", "Alternate secure web service", "May expose admin panels"),
    8443: ("HTTPS-alt", "Alternate secure web service", "May expose admin panels"),
    9000: (
        "Admin Dashboard",
        "Web admin service",
        "May expose internal systems or debug tools",
    ),
    9200: ("Elasticsearch", "Search engine service", "No auth in default config"),
    10000: (
        "Webmin",
        "Web-based system admin",
        "Often targeted for privilege escalation",
    ),
    11211: ("Memcached", "Caching service", "No auth; data exposure risk"),
}

ENDPOINT_CATEGORIES = [
    {
        "name": "Sensitive or high-risk endpoint",
        "list": [
            "/admin",
            "/upload",
            "/debug",
            "/shell",
            "/login",
            "/register",
            "/signup",
            "/signin",
            "/edit",
            "/delete",
            "/remove",
            "/config",
            "/backup",
            "/restore",
            "/reset",
            "/change-password",
            "/passwd",
            "/filemanager",
            "/console",
            "/exec",
            "/command",
            "/cgi-bin",
            "/manage",
            "/dashboard",
            "/settings",
            "/admincp",
        ],
        "rank": 100,
    },
    {
        "name": "Authentication/Authorization endpoint",
        "list": [
            "/auth",
            "/login",
            "/logout",
            "/register",
            "/signup",
            "/signin",
            "/verify",
            "/token",
            "/session",
        ],
        "rank": 90,
    },
    {
        "name": "Internal/Admin API endpoint",
        "list": ["/admin-api", "/internal", "/private", "/config"],
        "rank": 85,
    },
    {
        "name": "Payment or billing-related endpoint",
        "list": [
            "/payment",
            "/checkout",
            "/order",
            "/invoice",
            "/billing",
            "/transaction",
        ],
        "rank": 80,
    },
    {
        "name": "File handling endpoint",
        "list": ["/download", "/file", "/view", "/document", "/attachment"],
        "rank": 75,
    },
    {
        "name": "Redirection or SSRF-prone endpoint",
        "list": ["/redirect", "/url", "/proxy", "/forward", "/next", "/return"],
        "rank": 70,
    },
    {
        "name": "Debug or logging endpoint",
        "list": ["/log", "/trace", "/stack", "/error", "/dump"],
        "rank": 65,
    },
    {
        "name": "Webhook/Callback endpoint",
        "list": ["/webhook", "/callback", "/callback-url"],
        "rank": 60,
    },
    {
        "name": "User/Account-related endpoint",
        "list": ["/user", "/profile", "/account"],
        "rank": 55,
    },
    {
        "name": "Versioned API endpoint",
        "list": [f"/v{i}" for i in range(1, 10)] + ["/latest"],
        "rank": 50,
    },
    {
        "name": "General API or Search/Analytics endpoint",
        "list": [
            "/api",
            "/graphql",
            "/soap",
            "/service",
            "/query",
            "/docs",
            "/swagger",
            "/openapi",
            "/search",
            "/report",
            "/analytics",
        ],
        "rank": 45,
    },
    {
        "name": "CMS-specific or backend-related endpoint",
        "list": ["/wp-admin", "/wp-json", "/drupal", "/joomla", "/laravel", "/strapi"],
        "rank": 40,
    },
    {
        "name": "Development or staging/test endpoint",
        "list": [
            "/test",
            "/dev",
            "/staging",
            "/mock",
            "/sandbox",
            "/qa",
            "/demo",
            "/sample",
        ],
        "rank": 30,
    },
    {"name": "Monitoring/Health endpoint", "list": ["/status", "/info"], "rank": 10},
]

SEVERITY_ORDER = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "info": 5,
    "unknown": 6,
}


# --------------------------
# Helpers
# --------------------------
def sanitize_excel(s):
    return _ILLEGAL_CHARS_RE.sub("", s) if isinstance(s, str) else s

def autosize_columns(ws):
    for col in ws.columns:
        max_len = max((len(str(cell.value)) for cell in col if cell.value), default=0)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max_len + 2

def port_reason(port):
    if port in CRITICAL_SERVICES:
        name, function, risk = CRITICAL_SERVICES[port]
        return f"{name} - {function}. Risk: {risk}"
    return "Standard port/service"

def endpoint_reason(path):
    path = path.lower()
    for category in ENDPOINT_CATEGORIES:
        if any(keyword in path for keyword in category["list"]):
            return category["name"], category["rank"]
    return "Generic or static-looking endpoint", 0

# --------------------------
# Loaders
# --------------------------
def load_subdomains(file_path):
    rows = [
        {"Subdomain": p[0], "IP": p[1]}
        for line in open(file_path)
        if (p := line.strip().split()) and len(p) >= 2
    ]
    return pd.DataFrame(rows)


def load_ports(file_path):
    rows = []
    for line in open(file_path):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) == 3:
            ip, port_str, service = parts
            port = int(port_str)
            rows.append(
                {
                    "IP": ip,
                    "Port": port,
                    "Service": service,
                    "Description": port_reason(port),
                }
            )
    return pd.DataFrame(rows)


def load_endpoints(file_path):
    rows = []
    for line in open(file_path, encoding="utf-8", errors="ignore"):
        url = line.strip().strip('"').strip("’")
        if not url:
            continue
        try:
            parsed = urlparse(url)
            reason, score = endpoint_reason(parsed.path or "/")
            rows.append(
                {
                    "URL (Endpoint)": sanitize_excel(url),
                    "Protocol": sanitize_excel(parsed.scheme.upper()),
                    "File Extension": sanitize_excel(
                        os.path.splitext(parsed.path or "/")[1].lower().lstrip(".")
                        or "none"
                    ),
                    "Reason to Test First": sanitize_excel(reason),
                    "Rank": score,
                }
            )
        except Exception:
            rows.append(
                {
                    "URL (Endpoint)": sanitize_excel(url),
                    "Protocol": "Unknown",
                    "File Extension": "error",
                    "Reason to Test First": "Could not parse URL",
                    "Rank": 0,
                }
            )
    return pd.DataFrame(rows).sort_values(by="Rank", ascending=False)


def load_vulnerabilities(file_path):
    rows = []
    for line in open(file_path):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(
            {
                "Template ID": data.get("template-id", ""),
                "Template Name": data.get("info", {}).get("name", ""),
                "Type": data.get("type", ""),
                "Severity": data.get("info", {}).get("severity", ""),
                "Host": data.get("host", ""),
                "Url": data.get("url", ""),
                "Matcher": data.get("matched-at", ""),
                "Results": ", ".join(data.get("extracted-results", []) or []),
            }
        )
    df = pd.DataFrame(rows)
    df["Severity Rank"] = df["Severity"].map(lambda s: SEVERITY_ORDER.get(s, 99))
    return df.sort_values(by="Severity Rank").drop(columns=["Severity Rank"])


# --------------------------
# Main
# --------------------------
def generate_dashboard(
    subdomain_file, port_file, endpoint_file, vuln_file, output_excel
):
    dfs = {
        "Domain": load_subdomains(subdomain_file),
        "Ports": load_ports(port_file),
        "Endpoints": load_endpoints(endpoint_file),
        "Vulnerabilities": load_vulnerabilities(vuln_file),
    }
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        for sheet, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
            autosize_columns(writer.book[sheet])
    print(f"[+] Excel dashboard generated: {output_excel}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Dashboard Excel with Domain, Ports, Endpoints, Vulnerabilities sheets"
    )
    parser.add_argument(
        "--subdomains", required=True, help="Subdomain file (subdomain IP)"
    )
    parser.add_argument("--ports", required=True, help="Port file (IP port service)")
    parser.add_argument(
        "--endpoints", required=True, help="Endpoint file with full URLs"
    )
    parser.add_argument(
        "--vulns", required=True, help="Nuclei JSONL vulnerability file"
    )
    parser.add_argument(
        "-o", "--output", default="pt_dashboard.xlsx", help="Output Excel filename"
    )
    args = parser.parse_args()

    generate_dashboard(
        args.subdomains, args.ports, args.endpoints, args.vulns, args.output
    )
