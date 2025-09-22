# 🔍 oss-subfinder

> **Production-ready subdomain reconnaissance for security professionals**

Open-source subdomain discovery platform combining passive intelligence gathering with real-time DNS enumeration. Built with FastAPI streaming, async DNS resolution, and a modern React interface for instant deployment and scalable reconnaissance workflows. Explore a live deployment at [oss-subfinder.vikk.dev](https://oss-subfinder.vikk.dev/).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/react-%2320232a.svg?style=flat&logo=react&logoColor=%2361DAFB)](https://reactjs.org/)

---

## 🎯 Key Features

<table>
<tr>
<td width="50%">

### 🚀 **Real-Time Discovery**
- Live streaming results via Server-Sent Events
- Instant UI updates as subdomains are discovered
- Progress tracking with detailed stage information

### 🔍 **Passive Intelligence**
- Certificate Transparency (crt.sh) integration
- Curated wordlist-based enumeration
- SecLists compatibility and sampling

</td>
<td width="50%">

### ⚡ **High-Performance DNS**
- MassDNS integration with graceful fallbacks
- Async DNS resolution with configurable concurrency
- Smart retry mechanisms and error handling

### 📊 **Rich Metadata**
- HTTP/TLS probing with status detection
- CNAME chain resolution and mapping
- WHOIS enrichment and CSV export

</td>
</tr>
</table>

### 🏗️ **Production Features**
- **PostgreSQL Persistence** – Scan history and caching survive restarts
- **Rate Limiting** – Built-in protection against abuse
- **Docker Ready** – Single-command deployment with Docker Compose
- **RESTful API** – Comprehensive endpoints for integration

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              React Frontend                                 │
│                        (shadcn/ui + Tailwind CSS)                           │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │ SSE/REST API (/api/*)
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ⚡ FastAPI Backend                                  │
│                        (Streaming + Async I/O)                              │
└──┬────────────────────┬─────────────────────┬────────────────────────────┬──┘
   │                    │                     │                            │
   ▼                    ▼                     ▼                            ▼
┌──────────┐    ┌─────────────────┐    ┌─────────────┐    ┌─────────────────────┐
│ MassDNS  │    │   PostgreSQL    │    │  aiodns/    │    │   WHOIS + crt.sh    │
│ Binary   │    │   Database      │    │ dnspython   │    │   HTTP Clients      │
│(optional)│    │   (History)     │    │ (Fallback)  │    │   (Passive Intel)   │
└──────────┘    └─────────────────┘    └─────────────┘    └─────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
docker >= 20.10
docker-compose >= 2.0

# Optional (for Makefile commands)
make
```

### 🐳 One-Command Launch

```bash
# Clone and start the entire stack
git clone https://github.com/vixkram/oss-subfinder.git
cd oss-subfinder

make build && make run
```

**That's it!** 🎉 Your subfinder is now running at:
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 🎮 Development Mode

For active frontend development:

```bash
# Start with hot-reload frontend
docker-compose --profile frontend up frontend-dev
```

**Development URLs**:
- **Frontend (Hot Reload)**: http://localhost:5173
- **Backend**: http://localhost:8000

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| **Database** | | |
| `POSTGRES_DSN` | `postgresql://subfinder:subfinder@postgres:5432/subfinder` | PostgreSQL connection string |
| `ENABLE_HISTORY` | `true` | Enable/disable result persistence |
| **Performance** | | |
| `RESOLVER_CONCURRENCY` | `50` | Parallel DNS lookups (aiodns) |
| `PROBE_CONCURRENCY` | `20` | Concurrent HTTP/TLS probes |
| `HTTP_TIMEOUT` | `10` | HTTP probe timeout (seconds) |
| **MassDNS** | | |
| `MASSDNS_BIN` | `/opt/massdns/massdns` | Path to MassDNS binary |
| `MASSDNS_RESOLVERS_FILE` | `app/resolvers.txt` | DNS resolver list |
| **Wordlists** | | |
| `BRUTEFORCE_WORDS` | `www,mail,ftp,admin...` | Comma-separated base words |
| `SECLISTS_WORDLIST` | `""` | Path to SecLists DNS wordlist |
| `SECLISTS_MIN_WORDS` | `500` | Max words from SecLists |
| **External Services** | | |
| `CRTSH_TIMEOUT` | `30` | Certificate Transparency timeout |
| `CRTSH_USER_AGENT` | `oss-subfinder/1.0` | User-Agent for crt.sh |
| **Rate Limiting** | | |
| `RATE_LIMIT_REQUESTS` | `60` | Requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Window size (seconds) |

### 📝 Custom Configuration

```bash
# Create your environment file
cp .env.example .env
vim .env  # Edit your settings

# Launch with custom config
docker-compose --env-file .env up
```

---

## 📚 API Reference

### 🔥 Core Endpoints

| Endpoint | Method | Description | Response Type |
|----------|--------|-------------|---------------|
| `/api/search` | GET | **Live subdomain discovery** | Server-Sent Events |
| `/api/history/{domain}` | GET | Historical scan results | JSON |
| `/api/recent` | GET | Recent scan activity | JSON |
| `/api/status/{host}` | GET | Single host probe | JSON |
| `/api/whois/{domain}` | GET | WHOIS information | JSON |

### 🎯 Example Usage

```bash
# Start a real-time scan
curl -N "http://localhost:8000/api/search?domain=example.com&include_bruteforce=true"

# Get scan history
curl "http://localhost:8000/api/history/example.com"

# Probe specific host
curl "http://localhost:8000/api/status/www.example.com"
```

**📖 Detailed API documentation**: [`docs/api.md`](docs/api.md)

---

## 🧪 Testing & Development

### Running Tests

```bash
# Run the full test suite
make test

# Run specific test categories
docker-compose run --rm backend pytest tests/unit/
docker-compose run --rm backend pytest tests/integration/
```

### 🛠️ Local Development (No Docker)

```bash
# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r backend/requirements.txt

# Start local database (Docker)
docker-compose up postgres -d

# Run backend locally
export POSTGRES_DSN=postgresql://subfinder:subfinder@localhost:5432/subfinder
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 📋 Development Profiles

| Profile | Command | Use Case |
|---------|---------|----------|
| **default** | `make run` | FastAPI backend + Postgres + MassDNS helper |
| **frontend** | `docker-compose --profile frontend up frontend-dev` | Vite playground proxied to the backend |
| **demo** | `docker-compose --profile demo up` | Launch configuration used for [oss-subfinder.vikk.dev](https://oss-subfinder.vikk.dev/) |

---

## 🔒 Security & Ethics

### ⚖️ Legal Compliance

> **⚠️ IMPORTANT**: Always ensure you have proper authorization before scanning domains you don't own.

- ✅ **Obtain explicit permission** for scanning third-party domains
- ✅ **Comply with Terms of Service** for external services (crt.sh, WHOIS providers)
- ✅ **Respect rate limits** and implement appropriate delays
- ✅ **Follow local laws** and regulations regarding network reconnaissance

### 🛡️ Responsible Usage

| ✅ Recommended | ❌ Avoid |
|----------------|---------|
| Own domains and assets | Unauthorized third-party domains |
| Reasonable request rates | Aggressive scanning patterns |
| Caching external API responses | Overwhelming external services |
| Proper error handling | Ignoring service limits |

### 🚨 Disclaimer

The maintainers of oss-subfinder assume **no responsibility** for misuse of this tool. Users are solely responsible for ensuring their usage complies with applicable laws and regulations.

---

## 📈 Performance Tuning

### 🎯 Optimization Guidelines

```bash
# High-performance configuration
export RESOLVER_CONCURRENCY=100
export PROBE_CONCURRENCY=50
export HTTP_TIMEOUT=5

# Conservative configuration (slower, gentler)
export RESOLVER_CONCURRENCY=20
export PROBE_CONCURRENCY=10
export HTTP_TIMEOUT=15
```

### 📊 Scaling Considerations

- **MassDNS**: Provides significantly better performance for large wordlists
- **Database**: Consider PostgreSQL tuning for high-volume scanning
- **Rate Limiting**: Adjust based on your infrastructure capacity

---

## 🤝 Contributing

We welcome contributions that make oss-subfinder more reliable, performant, and user-friendly!

### 🔄 Development Workflow

1. **Fork** the repository and create a feature branch
2. **Develop** your changes with appropriate tests
3. **Test** thoroughly: `make test`
4. **Document** any API or configuration changes
5. **Submit** a focused pull request with detailed description

### 📋 Contribution Guidelines

- **Code Quality**: Include type hints and comprehensive tests
- **Documentation**: Update README and API docs for user-facing changes
- **Compatibility**: Maintain backward compatibility where possible
- **Performance**: Consider impact on scanning performance

**📖 Detailed guidelines**: [`docs/contributing.md`](docs/contributing.md)

---

## 🗂️ Project Structure

```
oss-subfinder/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Configuration and utilities
│   │   ├── models/         # Database models
│   │   └── services/       # Business logic
│   ├── tests/              # Test suites
│   └── requirements.txt    # Python dependencies
├── frontend/               # React application
│   ├── src/
│   │   └── components/     # React components
│   ├── public/            # Static assets
│   └── package.json       # Node.js dependencies
├── docs/                   # Documentation
├── docker-compose.yml      # Container orchestration
└── Makefile               # Development commands
```

---

## 📄 License

Released under the [MIT License](LICENSE) - see the file for details.

---

## 🙋‍♂️ Support & Community

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/vixkram/oss-subfinder/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/vixkram/oss-subfinder/discussions)
- 📚 **Documentation**: [`docs/`](docs/) directory

---

<div align="center">

**Built with ❤️ for the security community**

[⭐ Star this repo](https://github.com/vixkram/oss-subfinder) • [🍴 Fork it](https://github.com/vixkram/oss-subfinder/fork) • [📖 Docs](docs/) • [🐛 Issues](https://github.com/vixkram/oss-subfinder/issues)

</div>
