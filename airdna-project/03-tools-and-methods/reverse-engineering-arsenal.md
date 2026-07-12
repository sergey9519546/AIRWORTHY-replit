# Reverse Engineering Arsenal — Detailed Tools

> Tools for each stage of reverse engineering an API or web app

---

## STAGE 4: Authentication & Session Analysis

| Tool | What It Does |
|---|---|
| **Burp Suite Intruder** | Brute-force auth endpoints, test rate limits |
| **jwt.io** | Decode/inspect JWT tokens |
| **jwt_tool** | JWT fuzzing, claim manipulation |
| **Postman** | Replay captured requests with different auth |
| **mitmproxy** | Intercept and modify auth headers in transit |

## STAGE 5: Request Crafting & Replay

| Tool | What It Does |
|---|---|
| **curl** | Manual request crafting |
| **httpie** | Human-friendly HTTP client |
| **Postman** | GUI request builder with collections |
| **Insomnia** | Alternative REST client |
| **Burp Repeater** | Manual request replay and modification |

## STAGE 6: Frontend / JavaScript Reverse Engineering

| Tool | What It Does |
|---|---|
| **Chrome DevTools Sources** | Set breakpoints, step through JS |
| **source-map-visualizer** | Reconstruct original source from source maps |
| **js-beautify** | Format minified JS |
| **AST Explorer** | Parse and analyze JS AST |
| **webpack-bundle-analyzer** | Visualize bundle contents |

## STAGE 7: Data Format & Protocol Analysis

| Tool | What It Does |
|---|---|
| **protobuf-inspector** | Decode Protocol Buffers |
| **Wireshark** | Deep packet inspection |
| **Charles Proxy** | SSL traffic inspection |
| **Fiddler** | HTTP debugging proxy |

## STAGE 8: API Testing & Fuzzing

| Tool | What It Does |
|---|---|
| **Burp Intruder** | Automated parameter fuzzing |
| **ffuf** | Fast web fuzzer |
| **Arjun** | Hidden parameter discovery |
| **Kiterunner** | API endpoint brute-forcer |
| **Nuclei** | Template-based vulnerability scanning |

## STAGE 9: Documentation & Knowledge Management

| Tool | What It Does |
|---|---|
| **mitmproxy2swagger** | Auto-generate OpenAPI from traffic captures |
| **Postman** | Auto-generate docs from collections |
| **Swagger UI** | Visualize and test OpenAPI specs |
| **Redoc** | Generate beautiful API docs |

## LAYER 1: Server & Framework Fingerprinting

| Technique | What It Reveals |
|---|---|
| HTTP headers | Server (nginx, Apache), framework (Express, Django) |
| Error pages | Framework version, stack traces |
| Cookie format | Session management (JWT, PHPSESSID, etc.) |
| URL patterns | REST, GraphQL, RPC |

## LAYER 2: Infrastructure & Attack Surface Mapping

| Tool | What It Does |
|---|---|
| **nmap** | Port scanning, service detection |
| **Shodan** | Internet-wide device search |
| **Censys** | Certificate and host search |
| **SecurityTrails** | DNS history, subdomains |

## LAYER 3: Source Code & Config Exposure

| Technique | What It Looks For |
|---|---|
| `.env` files | API keys, database credentials |
| `.git` directory | Source code exposure |
| `package.json` | Dependency versions |
| `docker-compose.yml` | Infrastructure setup |
| Source maps | Original source code |

## LAYER 4: Cookie & Token Analysis

| What to Check | Why |
|---|---|
| JWT claims | User roles, permissions, expiry |
| Session cookies | Session fixation, hijacking |
| CSRF tokens | Cross-site request forgery |
| API keys | Rate limits, scopes |

## LAYER 5: DNS & Network Intelligence

| Tool | What It Reveals |
|---|---|
| **dig** | DNS records (A, CNAME, MX, TXT) |
| **whois** | Domain registration, IP blocks |
| **crt.sh** | Certificate transparency logs |
| **Sublist3r** | Subdomain enumeration |

## LAYER 6: Error-Based Backend Discovery

| Technique | What It Reveals |
|---|---|
| Trigger 404/500 errors | Framework, version |
| Invalid JSON | Parser type |
| SQL injection | Database type |
| Path traversal | File system structure |

## LAYER 7: JavaScript Bundle Mining

| What to Extract | How |
|---|---|
| API endpoints | Regex for `/api/`, `/v2/`, etc. |
| API keys | Look for key patterns |
| Environment variables | `process.env.*` references |
| Route definitions | React Router, Vue Router configs |
| GraphQL schemas | `__schema` introspection |

## LAYER 8: Cloud & Service Detection

| Tool | What It Detects |
|---|---|
| **Wappalyzer** | Tech stack (frameworks, CDN, analytics) |
| **BuiltWith** | Detailed tech profiling |
| **WhatRuns** | Browser extension for tech detection |
| **CloudPing** | AWS region detection |

## BACKEND EXTRACTION CHECKLIST

```
[ ] Server type (nginx, Apache, Caddy)
[ ] Framework (Express, Django, Rails, Flask)
[ ] Language (Node.js, Python, Ruby, Go)
[ ] Database (PostgreSQL, MySQL, MongoDB, Redis)
[ ] Cache (Redis, Memcached)
[ ] CDN (Cloudflare, Akamai, CloudFront)
[ ] Auth method (JWT, OAuth, session cookies)
[ ] API style (REST, GraphQL, gRPC)
[ ] Deployment (Docker, K8s, serverless)
[ ] CI/CD (GitHub Actions, GitLab CI, Jenkins)
[ ] Monitoring (New Relic, Datadog, Sentry)
[ ] Analytics (GA4, Segment, Mixpanel)
```
