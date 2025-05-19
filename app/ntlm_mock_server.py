from flask import Flask, request, Response
import base64
import uuid
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

# MOCK_HOSTNAME = "team.dms.mas.gov.sg"
MOCK_HOSTNAME = "localhost"  
MOCK_NTLM_TYPE2_TOKEN = (
    "TlRMTVNTUAACAAAACAAIADgAAAAGgokCgmS2NZAaeckAAAAAAAAAAKIAogBAAAAACgA5OAAAAA9NQVNXT1JMRAIAEABNAEEAUwBXAE8AUgBMAEQAAQAYAFcATQBQAEQATQBTAFcARgBFADAAMAAyAAQAFABtAGEAcwAuAGcAbwB2AC4AcwBnAAMALgBXAE0AUABEAE0AUwBXAEYARQAwADAAMgAuAG0AYQBzAC4AZwBvAHYALgBzAGcABQAUAG0AYQBzAC4AZwBvAHYALgBzAGcABwAIAM+R4/bnv9sBAAAAAA=="
)
MOCK_SHAREPOINT_VERSION = "16.0.0.5478"
MOCK_FORM_DIGEST_TIMEOUT_SECONDS = 1800


def gmt_now():
    return datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')


def form_digest_value():
    fake_digest = "0x" + uuid.uuid4().hex + uuid.uuid4().hex
    timestamp = datetime.now(timezone.utc).strftime('%d %b %Y %H:%M:%S -0000')
    return f"{fake_digest},{timestamp}"


@app.route('/sites/<site>/_api/contextinfo', methods=['POST'])
def handle_context_info(site):
    auth = request.headers.get("Authorization", "")
    req_guid = str(uuid.uuid4())
    now_gmt = gmt_now()

    print(f"\n[Request] site={site}, Auth={auth[:40]}...") # Keep for debugging

    if "TlRMTVNTUAAD" in auth:  # Expecting Type 3
        # ... (existing 200 OK logic - this should be fine if Type 3 is correctly identified)
        # (ensure this block is correctly indented under the if)
        digest = form_digest_value()
        xml = f"""<?xml version="1.0" encoding="utf-8"?>
<d:GetContextWebInformation xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
 xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
    <d:FormDigestTimeoutSeconds m:type="Edm.Int32">{MOCK_FORM_DIGEST_TIMEOUT_SECONDS}</d:FormDigestTimeoutSeconds>
    <d:FormDigestValue>{digest}</d:FormDigestValue>
    <d:LibraryVersion>16.0.5478.1000</d:LibraryVersion>
    <d:SiteFullUrl>https://{MOCK_HOSTNAME}/sites/{site}</d:SiteFullUrl>
    <d:SupportedSchemaVersions m:type="Collection(Edm.String)">
        <d:element>14.0.0.0</d:element>
        <d:element>15.0.0.0</d:element>
    </d:SupportedSchemaVersions>
    <d:WebFullUrl>https://{MOCK_HOSTNAME}/sites/{site}</d:WebFullUrl>
</d:GetContextWebInformation>"""
        headers = {
            "Content-Type": "application/xml;charset=utf-8",
            "Cache-Control": "private, max-age=0",
            # "Transfer-Encoding": "chunked", # Let Flask/Gunicorn handle this
            "Expires": (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime('%a, %d %b %Y %H:%M:%S GMT'), # Corrected from utcnow()
            "Last-Modified": now_gmt,
            "X-SharePointHealthScore": "0",
            "X-SP-SERVERSTATE": "ReadOnly=0",
            "DATASERVICEVERSION": "3.0",
            "SPClientServiceRequestDuration": "27",
            "SPRequestGuid": req_guid,
            "request-id": req_guid,
            "X-FRAME-OPTIONS": "SAMEORIGIN",
            "Content-Security-Policy": "frame-ancestors 'self';",
            "Persistent-Auth": "true",
            "X-Powered-By": "ASP.NET (Mock)",
            "MicrosoftSharePointTeamServices": MOCK_SHAREPOINT_VERSION,
            "X-Content-Type-Options": "nosniff",
            "X-MS-InvokeApp": "1; RequireReadOnly",
            "Date": now_gmt,
            "Connection": "keep-alive", # Added from your log
        }
        return Response(xml, status=200, headers=headers)


    elif "TlRMTVNTUAAB" in auth:  # NTLM Type 1 received
        # This is what curl does. Spring boot doesn't do this with current code.
        # This block should remain as is for curl compatibility.
        print("NTLM Type 1 received, sending Type 2 challenge.")
        headers_type1_response = [
            ("WWW-Authenticate", f"NTLM {MOCK_NTLM_TYPE2_TOKEN}"),
            ("WWW-Authenticate", "Negotiate"),
            ("SPRequestGuid", req_guid),
            ("request-id", req_guid),
            ("X-FRAME-OPTIONS", "SAMEORIGIN"),
            ("Content-Security-Policy", "frame-ancestors 'self';"),
            ("SPRequestDuration", "1"),
            ("SPIisLatency", "0"),
            ("X-Powered-By", "ASP.NET (Mock)"),
            ("MicrosoftSharePointTeamServices", MOCK_SHAREPOINT_VERSION),
            ("X-Content-Type-Options", "nosniff"),
            ("X-MS-InvokeApp", "1; RequireReadOnly"),
            ("Date", now_gmt),
            ("Content-Length", "0"),
            ("Set-Cookie", "MAS_intranet_cookie=fake_type1_flow; path=/; Httponly; Secure"), # Distinguish cookie if needed
            ("Connection", "keep-alive"),
        ]
        return Response("", status=401, headers=headers_type1_response)

    else:  # No NTLM Auth header, or unrecognized. Treat as anonymous initial request from Spring.
        print("Anonymous request or no valid NTLM Type1/Type3, sending Type 2 challenge directly for WebClient.")
        headers_for_anonymous_challenge = [
            ("WWW-Authenticate", f"NTLM {MOCK_NTLM_TYPE2_TOKEN}"), # Send full Type 2 token
            ("WWW-Authenticate", "Negotiate"),
            ("SPRequestGuid", req_guid),
            ("request-id", req_guid),
            ("X-FRAME-OPTIONS", "SAMEORIGIN"),
            ("Content-Security-Policy", "frame-ancestors 'self';"),
            ("SPRequestDuration", "1"), # Mock values
            ("SPIisLatency", "0"), # Mock values
            ("X-Powered-By", "ASP.NET (Mock)"),
            ("MicrosoftSharePointTeamServices", MOCK_SHAREPOINT_VERSION),
            ("X-Content-Type-Options", "nosniff"),
            ("X-MS-InvokeApp", "1; RequireReadOnly"),
            ("Date", now_gmt),
            ("Content-Length", "0"), # Mocking empty body for 401
            # ("Set-Cookie", "MAS_intranet_cookie=fake_anon_flow; path=/; Httponly; Secure"), # Optional
            ("Connection", "keep-alive"),
        ]
        return Response("", status=401, headers=headers_for_anonymous_challenge)


if __name__ == '__main__':
    print("🚀 Running NTLM mock server on http://localhost:8181")
    app.run(host="0.0.0.0", port=8181, debug=True)
    # print(f"🚀 Starting mock NTLM SharePoint at https://{MOCK_HOSTNAME}:443")

    # Run with self-signed cert
    # Generate with:
    # openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=team.dms.mas.gov.sg"
    # app.run(host="0.0.0.0", port=443, ssl_context=('cert.pem', 'key.pem'), debug=True)
