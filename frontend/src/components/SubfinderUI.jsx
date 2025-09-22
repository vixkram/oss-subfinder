import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const PROJECT_NAME = "oss-subfinder";
const PROJECT_TAGLINE = "Open-source subdomain reconnaissance.";
const PROJECT_BADGE = "Security Research";
const GITHUB_URL = "https://github.com/vixkram/oss-subfinder";

const DONATION_WALLETS = [
  {
    currency: "Bitcoin",
    symbol: "BTC",
    address: "bc1qlz8thfq9k02y86lr49w5mqty2c93dz4ptjz4cn",
  },
  {
    currency: "Ethereum",
    symbol: "ETH",
    address: "0x278881E9Edaa585174b1708447B1C07934530ded",
  },
  {
    currency: "Litecoin",
    symbol: "LTC",
    address: "ltc1q9qr39kdxv3ulmszw48jgp7p8jqq0metdjzxp4m",
  },
];

const API_BASE_URL = (import.meta.env.VITE_BACKEND_URL ?? "").replace(/\/$/, "");

const resolveApiUrl = (path) => {
  if (!path.startsWith("/")) {
    return API_BASE_URL ? `${API_BASE_URL}/${path}` : path;
  }
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
};

const GitHubIcon = ({ className = "", ...props }) => (
  <svg
    aria-hidden="true"
    focusable="false"
    viewBox="0 0 24 24"
    width="20"
    height="20"
    className={className}
    {...props}
  >
    <path
      fill="currentColor"
      d="M12 .5C5.648.5.5 5.648.5 12.034c0 5.108 3.308 9.438 7.91 10.963.578.11.79-.252.79-.56 0-.275-.01-1.004-.015-1.972-3.219.7-3.898-1.552-3.898-1.552-.526-1.34-1.286-1.696-1.286-1.696-1.052-.72.08-.706.08-.706 1.164.082 1.777 1.196 1.777 1.196 1.034 1.77 2.713 1.259 3.374.963.105-.757.405-1.259.737-1.549-2.567-.293-5.267-1.295-5.267-5.762 0-1.273.452-2.313 1.194-3.129-.12-.294-.518-1.476.112-3.075 0 0 .973-.312 3.188 1.195a11.12 11.12 0 0 1 2.903-.39c.986.005 1.98.133 2.907.39 2.213-1.507 3.185-1.195 3.185-1.195.632 1.599.233 2.781.114 3.075.744.816 1.193 1.856 1.193 3.129 0 4.48-2.705 5.465-5.283 5.751.417.36.788 1.075.788 2.168 0 1.565-.014 2.828-.014 3.214 0 .311.208.676.797.559 4.6-1.527 7.904-5.856 7.904-10.962C23.5 5.648 18.352.5 12 .5Z"
    />
  </svg>
);

const buttonVariants = {
  primary:
    "bg-[var(--button-primary-bg)] text-[var(--button-primary-text)] border-[var(--button-primary-border)] hover:bg-[var(--button-primary-hover-bg)]",
  secondary:
    "bg-[var(--button-secondary-bg)] text-[var(--button-secondary-text)] border-[var(--button-secondary-border)] hover:bg-[var(--button-secondary-hover-bg)]",
  muted:
    "bg-[var(--button-muted-bg)] text-[var(--button-muted-text)] border-[var(--button-muted-border)] hover:bg-[var(--button-muted-hover-bg)]",
};

const Button = ({ variant = "secondary", className = "", ...props }) => (
  <button
    className={`inline-flex h-10 items-center justify-center rounded border px-4 text-xs font-semibold uppercase tracking-[0.15em] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/60 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
      buttonVariants[variant] ?? buttonVariants.secondary
    } ${className}`}
    {...props}
  />
);

const Panel = ({ className = "", children }) => (
  <div
    className={`rounded-lg border p-5 ${className}`}
    style={{
      background: "var(--panel-bg)",
      borderColor: "var(--panel-border)",
      boxShadow: "var(--panel-shadow)",
    }}
  >
    {children}
  </div>
);

const Input = ({ className = "", ...props }) => (
  <input
    className={`h-10 w-full rounded border px-3 text-sm focus:border-sky-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/50 focus-visible:ring-offset-2 ${className}`}
    style={{
      background: "var(--input-bg)",
      borderColor: "var(--input-border)",
      color: "var(--text-primary)",
    }}
    {...props}
  />
);

const SectionHeading = ({ label, className = "" }) => (
  <p className={`text-[11px] font-semibold uppercase tracking-[0.25em] text-[var(--text-muted)] ${className}`}>{label}</p>
);

const LoadingIndicator = ({ label = "Scanning…" }) => (
  <div className="loading-indicator" role="status" aria-live="polite">
    <span className="loading-spinner" aria-hidden="true" />
    <span className="loading-label">{label}</span>
  </div>
);

const formatTimestamp = (value) => {
  if (!value) {
    return "Unknown";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
};

const formatTimestampCompact = (value) => {
  if (!value) {
    return "—";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

function summarizeTopIp(results) {
  const counts = new Map();
  for (const item of results) {
    for (const ip of item.ips || []) {
      counts.set(ip, (counts.get(ip) || 0) + 1);
    }
  }
  let best = null;
  for (const [ip, count] of counts.entries()) {
    if (!best || count > best.count) {
      best = { ip, count };
    }
  }
  return best;
}

function normalizeResultEntry(raw) {
  if (!raw || typeof raw !== "object") {
    return {
      name: "",
      ips: [],
      cname: "",
      http_status: null,
      tls: false,
      server: "",
    };
  }

  const coerceIps = (value) => {
    if (Array.isArray(value)) {
      return value.map((item) => String(item || "").trim()).filter(Boolean);
    }
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (!trimmed) {
        return [];
      }
      if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
        try {
          const parsed = JSON.parse(trimmed);
          if (Array.isArray(parsed)) {
            return parsed.map((item) => String(item || "").trim()).filter(Boolean);
          }
        } catch (error) {
          console.debug("Unable to parse JSON-encoded IP list", error);
        }
      }
      return trimmed
        .split(/[\s,]+/)
        .map((item) => item.trim())
        .filter(Boolean);
    }
    return [];
  };

  return {
    name: String(raw.name ?? "").trim(),
    ips: coerceIps(raw.ips),
    cname: raw.cname ? String(raw.cname) : "",
    http_status:
      typeof raw.http_status === "number"
        ? raw.http_status
        : raw.http_status === null || raw.http_status === undefined
        ? null
        : Number.isNaN(Number(raw.http_status))
        ? null
        : Number(raw.http_status),
    tls: Boolean(raw.tls),
    server: raw.server ? String(raw.server) : "",
  };
}

function StageSummary({ domain, stages, searchingDomain, results, loading, lastUpdated }) {
  if (!domain && !searchingDomain) {
    return null;
  }

  const lastStage = stages[stages.length - 1];
  const sawCache = stages.some((stage) => stage.stage === "cache_hit");
  const sawLiveStart = stages.some((stage) => stage.stage === "started");
  const statusLabel = loading
    ? "Running"
    : lastStage?.stage === "done"
    ? "Complete"
    : lastStage?.stage === "error"
    ? "Error"
    : results.length
    ? "Ready"
    : "Idle";
  const sourceLabel = sawCache
    ? "Cache replay"
    : sawLiveStart
    ? loading
      ? "Streaming"
      : "Live run"
    : results.length
    ? "Recent results"
    : "—";

  const liveCount = results.filter((item) => Number(item.http_status) && Number(item.http_status) < 400).length;
  const tlsCount = results.filter((item) => item.tls).length;
  const topIp = summarizeTopIp(results);
  const scanName = searchingDomain || domain;

  let detailText = "Enter a domain to begin scanning.";
  if (loading) {
    detailText = `Streaming ${scanName} — hosts appear as they resolve.`;
  } else if (lastStage?.stage === "error") {
    detailText = "Scan interrupted. Press refresh to retry.";
  } else if (!results.length && scanName) {
    detailText = `No discoveries stored for ${scanName} yet.`;
  } else {
    detailText = null;
  }

  return (
    <Panel className="summary-panel space-y-3">
      <SectionHeading label="Scan summary" />
      <div className="summary-meta">
        {[
          { label: "Status", value: statusLabel },
          { label: "Source", value: sourceLabel },
          {
            label: "Updated",
            value: lastUpdated ? formatTimestamp(lastUpdated) : "—",
          },
        ].map((item) => (
          <div key={item.label} className="summary-meta-item">
            <span className="summary-meta-label">{item.label}</span>
            <span className="summary-meta-value">{item.value}</span>
          </div>
        ))}
      </div>
      <div className="summary-statline">
        {[
          { label: "Hosts", value: results.length || "—" },
          { label: "HTTP < 400", value: liveCount || "—" },
          { label: "TLS", value: tlsCount || "—" },
          {
            label: "Top IP",
            value: topIp ? topIp.ip : "—",
            sub: topIp ? `${topIp.count} hosts` : "",
          },
        ].map((item) => (
          <span key={item.label} className="summary-statline-item">
            <span className="summary-statline-label">{item.label}</span>
            <span className="summary-statline-value">{item.value}</span>
            {item.sub && <span className="summary-statline-sub">{item.sub}</span>}
          </span>
        ))}
      </div>
      {detailText && <p className="summary-description">{detailText}</p>}
    </Panel>
  );
}

function ResultsTable({ results, loading }) {
  if (!results.length) {
    return (
      <Panel className="border-dashed">
        <p className="text-sm text-slate-400">
          {loading ? "Awaiting streamed entries…" : "Run a scan to populate this table."}
        </p>
      </Panel>
    );
  }

  return (
    <div
      className="results-table overflow-hidden rounded border"
      style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)" }}
    >
      <div className="max-h-[60vh] overflow-auto">
        <table
          className="min-w-[980px] text-sm"
          style={{ borderColor: "var(--table-border)" }}
        >
          <thead
            className="sticky top-0 text-xs uppercase"
            style={{ background: "var(--table-head-bg)", color: "var(--text-muted)" }}
          >
            <tr>
              <th className="px-4 py-3 text-left">Hostname</th>
              <th className="px-4 py-3 text-left">IPs</th>
              <th className="px-4 py-3 text-left">CNAME</th>
              <th className="px-4 py-3 text-left">HTTP</th>
              <th className="px-4 py-3 text-left">TLS</th>
              <th className="px-4 py-3 text-left">Server</th>
            </tr>
          </thead>
          <tbody
            className="divide-y"
            style={{
              background: "var(--table-row-bg)",
              color: "var(--text-primary)",
              borderColor: "var(--table-border)",
              "--tw-divide-y-reverse": "0",
              "--tw-divide-y-color": "var(--table-border)",
            }}
          >
            {results.map((row) => {
              const scheme = row.tls ? "https" : row.http_status ? "http" : "https";
              const url = `${scheme}://${row.name}`;
              return (
                <tr key={row.name}>
                  <td className="px-4 py-3 font-mono text-xs sm:text-sm">
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                    className="host-link whitespace-nowrap text-sky-300 hover:text-sky-200"
                    >
                      {row.name}
                    </a>
                  </td>
                  <td className="px-4 py-3">
                    {row.ips?.length ? (
                  <div className="flex flex-wrap gap-1 font-mono text-[11px] text-slate-300">
                    {row.ips.map((ip) => (
                      <span key={ip} className="ip-chip rounded px-2 py-0.5">
                        {ip}
                      </span>
                    ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-500">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-300">
                    <span className="break-all">{row.cname || "—"}</span>
                  </td>
                  <td className="px-4 py-3 text-xs">{row.http_status ?? "—"}</td>
                  <td className="px-4 py-3 text-xs">{row.tls ? "Yes" : "No"}</td>
                  <td className="px-4 py-3 text-xs text-slate-300">
                    <span className="break-all">{row.server || "—"}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HistoryPanel({ domain, runs, meta, onSelect }) {
  return (
    <Panel>
      <SectionHeading label="Scan history" />
      <p className="mt-2 text-xs text-slate-500">
        {domain ? `Most recent runs for ${domain}.` : "Run a scan to populate history."}
      </p>
      {meta?.total !== undefined && (
        <p className="mt-3 text-xs text-slate-500">
          {meta.total ?? 0} hosts · cached {meta.cached ? formatTimestampCompact(meta.cached) : "now"}
        </p>
      )}
      {runs?.length ? (
        <ul className="mt-4 space-y-2 text-sm">
          {runs.map((run) => (
            <li key={`${run.timestamp}-${run.total}`}>
              <button
                type="button"
                className="list-tile flex w-full items-center justify-between rounded border px-3 py-2 text-left"
                onClick={() => onSelect?.(run.domain)}
              >
                <span className="font-mono text-xs">{formatTimestampCompact(run.timestamp)}</span>
                <span className="text-xs text-slate-500">{run.total ?? 0} hosts</span>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-xs text-slate-500">No stored runs yet.</p>
      )}
    </Panel>
  );
}

function RecentScans({ items, onSelect, onHide, collapsible = false }) {
  return (
    <Panel>
      <div className="flex items-center justify-between gap-2">
        <SectionHeading label="Recent scans" />
        {collapsible && (
          <button
            type="button"
            className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 hover:text-slate-200"
            onClick={onHide}
          >
            Hide
          </button>
        )}
      </div>
      {items?.length ? (
        <ul className="mt-4 space-y-2 text-sm text-slate-200">
          {items.map((item) => (
            <li key={`${item.domain}-${item.timestamp}`}>
              <button
                type="button"
                className="list-tile flex w-full items-center justify-between rounded border px-3 py-2 text-left"
                onClick={() => onSelect?.(item.domain)}
              >
                <span className="truncate pr-2 font-semibold">{item.domain}</span>
                <span className="shrink-0 text-xs text-slate-500">
                  {item.total ?? 0} hosts · {formatTimestampCompact(item.timestamp)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-xs text-slate-500">No shared scans yet.</p>
      )}
    </Panel>
  );
}

function InfoPanel({ title, loading, error, children }) {
  if (!loading && !error && !children) {
    return null;
  }
  return (
    <Panel>
      <SectionHeading label={title} />
      {loading && <p className="mt-3 text-xs text-slate-500">Loading…</p>}
      {error && <p className="mt-3 text-xs text-rose-400">{error}</p>}
      {children && <div className="mt-3 space-y-2 text-sm text-slate-200">{children}</div>}
    </Panel>
  );
}

function DonationPanel({ wallets, copiedSymbol, onCopy }) {
  if (!wallets?.length) {
    return null;
  }

  return (
    <Panel className="donation-panel">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <SectionHeading label="Support" />
        <p className="donation-panel-tagline">Keep oss-subfinder free by sponsoring development.</p>
      </div>
      <ul className="donation-wallets">
        {wallets.map((wallet) => (
          <li key={wallet.symbol} className="donation-wallet">
            <div className="donation-wallet-header">
              <span className="donation-wallet-symbol">{wallet.symbol}</span>
              <span className="donation-wallet-currency">{wallet.currency}</span>
            </div>
            <code className="donation-wallet-address">{wallet.address}</code>
            <button
              type="button"
              className="donation-copy-btn"
              onClick={() => onCopy(wallet)}
            >
              {copiedSymbol === wallet.symbol ? "Copied" : "Copy"}
            </button>
          </li>
        ))}
      </ul>
      <p className="donation-panel-note">
        Contributions power ongoing maintenance and new features—thank you for helping keep oss-subfinder free and open.
      </p>
    </Panel>
  );
}

export default function SubfinderUI() {
  const [domain, setDomain] = useState("");
  const [results, setResults] = useState([]);
  const [stages, setStages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [whoisState, setWhoisState] = useState({ loading: false, data: null, error: null });
  const [searchingDomain, setSearchingDomain] = useState("");
  const [historyRuns, setHistoryRuns] = useState([]);
  const [historyMeta, setHistoryMeta] = useState(null);
  const [recentScans, setRecentScans] = useState([]);
  const [recentLoaded, setRecentLoaded] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [copiedDonation, setCopiedDonation] = useState(null);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [recentVisible, setRecentVisible] = useState(false);
  const [theme, setTheme] = useState(() => {
    if (typeof window === "undefined") {
      return "dark";
    }
    return localStorage.getItem("oss-subfinder-theme") || "dark";
  });

  const collator = useMemo(() => new Intl.Collator(undefined, { sensitivity: "base" }), []);
  const resultsStoreRef = useRef(new Map());
  const flushTimeoutRef = useRef(null);

  const eventSourceRef = useRef(null);
  const copyTimeoutRef = useRef(null);

  const cleanupStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setLoading(false);
  }, []);

  useEffect(() => cleanupStream, [cleanupStream]);

  useEffect(() => {
    const body = document.body;
    const next = theme === "light" ? "theme-light" : "theme-dark";
    body.classList.remove("theme-light", "theme-dark");
    body.classList.add(next);
    localStorage.setItem("oss-subfinder-theme", theme);
  }, [theme]);

  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
      if (flushTimeoutRef.current) {
        clearTimeout(flushTimeoutRef.current);
      }
    };
  }, []);

  const syncResultsFromStore = useCallback(() => {
    const snapshot = Array.from(resultsStoreRef.current.values()).sort((a, b) =>
      collator.compare(a.name, b.name)
    );
    setResults(snapshot);
  }, [collator]);

  const scheduleResultsFlush = useCallback(() => {
    if (flushTimeoutRef.current) {
      return;
    }
    flushTimeoutRef.current = setTimeout(() => {
      flushTimeoutRef.current = null;
      syncResultsFromStore();
    }, 120);
  }, [syncResultsFromStore]);

  const flushResultsNow = useCallback(() => {
    if (flushTimeoutRef.current) {
      clearTimeout(flushTimeoutRef.current);
      flushTimeoutRef.current = null;
    }
    syncResultsFromStore();
  }, [syncResultsFromStore]);

  const clearResults = useCallback(() => {
    if (flushTimeoutRef.current) {
      clearTimeout(flushTimeoutRef.current);
      flushTimeoutRef.current = null;
    }
    resultsStoreRef.current = new Map();
    setResults([]);
  }, []);

  const fetchRecent = useCallback(async () => {
    try {
      const res = await fetch(resolveApiUrl(`/api/recent?limit=12`));
      if (!res.ok) {
        throw new Error(`Recent scans request failed (${res.status})`);
      }
      const data = await res.json();
      setRecentScans(Array.isArray(data.recent) ? data.recent : []);
    } catch (error) {
      console.debug("Unable to load recent scans", error);
      setRecentScans([]);
    } finally {
      setRecentLoaded(true);
    }
  }, []);

  const fetchHistoryForDomain = useCallback(async (value, options = {}) => {
    const { hydrateResults = false } = options;
    if (!value) {
      setHistoryRuns([]);
      setHistoryMeta(null);
      if (hydrateResults) {
        clearResults();
        setLastUpdated(null);
      }
      return;
    }
    try {
      const res = await fetch(resolveApiUrl(`/api/history?domain=${encodeURIComponent(value)}`));
      if (!res.ok) {
        throw new Error(`History request failed (${res.status})`);
      }
      const data = await res.json();
      const runs = Array.isArray(data.runs) ? data.runs : [];
      const meta = { cached: data.cached, total: data.total };
      setHistoryRuns(runs);
      setHistoryMeta(meta);
      if (hydrateResults) {
        const entries = Array.isArray(data.results) ? data.results : [];
        const normalized = entries.map(normalizeResultEntry).filter((item) => item.name);
        const shouldHydrate =
          normalized.length > 0 ||
          (typeof meta.total === "number" && meta.total > 0) ||
          resultsStoreRef.current.size === 0;
        if (shouldHydrate) {
          resultsStoreRef.current = new Map(normalized.map((item) => [item.name, item]));
          flushResultsNow();
        }
        if (meta.cached) {
          setLastUpdated(meta.cached);
        } else if (resultsStoreRef.current.size === 0) {
          setLastUpdated(null);
        }
      }
    } catch (error) {
      console.debug("Unable to load history", error);
      setHistoryRuns([]);
      setHistoryMeta(null);
      if (hydrateResults && resultsStoreRef.current.size === 0) {
        clearResults();
        setLastUpdated(null);
      }
    }
  }, [clearResults, flushResultsNow]);

  useEffect(() => {
    void fetchRecent();
  }, [fetchRecent]);

  const handleCopyDonation = useCallback(async (wallet) => {
    if (!wallet?.address) {
      return;
    }
    if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) {
      console.debug("Clipboard unavailable for donations");
      return;
    }
    try {
      await navigator.clipboard.writeText(wallet.address);
      setCopiedDonation(wallet.symbol);
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
      copyTimeoutRef.current = setTimeout(() => {
        setCopiedDonation(null);
        copyTimeoutRef.current = null;
      }, 2200);
    } catch (error) {
      console.debug("Unable to copy donation address", error);
    }
  }, [copyTimeoutRef, setCopiedDonation]);

  const handleSearch = useCallback(
    (refresh = false, overrideDomain) => {
      const targetValue = (overrideDomain ?? domain).trim();
      if (!targetValue) {
        return;
      }
      cleanupStream();
      setHasInteracted(true);
      setRecentVisible(true);
      setErrorMessage(null);
      setStages([]);
      if (!overrideDomain) {
        setHistoryRuns([]);
        setHistoryMeta(null);
      }
      setWhoisState({ loading: false, data: null, error: null });
      if (!overrideDomain || refresh) {
        clearResults();
      }
      setSearchingDomain(targetValue);
      setLoading(true);
      setLastUpdated(null);

      const url = resolveApiUrl(`/api/search?domain=${encodeURIComponent(targetValue)}${refresh ? "&refresh=1" : ""}`);
      const es = new EventSource(url);
      eventSourceRef.current = es;

      const recordUpdate = (value) => {
        if (value) {
          setLastUpdated(value);
        } else {
          setLastUpdated(new Date().toISOString());
        }
      };

      es.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.stage) {
            setStages((prev) => [...prev, payload]);
            recordUpdate(payload.cached_at);
            if (payload.stage === "started") {
              setSearchingDomain(targetValue);
            }
            if (payload.stage === "done") {
              setLoading(false);
              setSearchingDomain("");
              cleanupStream();
              void fetchHistoryForDomain(targetValue, { hydrateResults: true });
              void fetchRecent();
              flushResultsNow();
            }
            if (payload.stage === "error") {
              setErrorMessage(payload.error ?? "Search failed");
              setSearchingDomain("");
            }
          } else if (payload.type === "entry") {
            const normalized = normalizeResultEntry(payload);
            if (normalized.name) {
              const existing = resultsStoreRef.current.get(normalized.name) || {};
              resultsStoreRef.current.set(normalized.name, { ...existing, ...normalized });
              scheduleResultsFlush();
            }
            recordUpdate();
          }
        } catch (err) {
          console.error("Failed to parse event", err);
        }
      };

      es.onerror = () => {
        setErrorMessage("Stream interrupted. You can retry the scan.");
        setSearchingDomain("");
        cleanupStream();
        recordUpdate();
      };
    },
    [
      cleanupStream,
      clearResults,
      domain,
      fetchHistoryForDomain,
      fetchRecent,
      flushResultsNow,
      scheduleResultsFlush,
    ]
  );

  const handleStop = useCallback(() => {
    setSearchingDomain("");
    cleanupStream();
  }, [cleanupStream]);

  const handleWhois = useCallback(async () => {
    setRecentVisible(true);
    const target = domain.trim();
    if (!target) {
      return;
    }
    setWhoisState({ loading: true, data: null, error: null });
    try {
      const res = await fetch(resolveApiUrl(`/api/whois?domain=${encodeURIComponent(target)}`));
      if (!res.ok) {
        throw new Error(`WHOIS request failed (${res.status})`);
      }
      const data = await res.json();
      setWhoisState({ loading: false, data, error: null });
    } catch (error) {
      setWhoisState({ loading: false, data: null, error: error.message });
    }
  }, [domain]);

  const downloadCsv = useCallback(() => {
    if (!results.length) {
      return;
    }
    const header = ["name", "ips", "cname", "http_status", "tls", "server"];
    const rows = results.map((item) => [
      item.name,
      (item.ips || []).join(" "),
      item.cname || "",
      item.http_status ?? "",
      item.tls ? "true" : "false",
      item.server || "",
    ]);
    const csvContent = [header, ...rows]
      .map((line) => line.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `oss-subfinder-${domain || "results"}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [domain, results]);

  const handleSelectDomain = useCallback(
    (value) => {
      if (!value) {
        return;
      }
      setHasInteracted(true);
      setRecentVisible(true);
      setDomain(value);
      void fetchHistoryForDomain(value, { hydrateResults: true });
      setTimeout(() => {
        handleSearch(false, value);
      }, 0);
    },
    [fetchHistoryForDomain, handleSearch]
  );

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const activeScanName = searchingDomain || domain.trim();
  const loadingLabel = activeScanName ? `Scanning ${activeScanName}` : "Scanning…";
  const showScanSections = hasInteracted || loading || stages.length > 0 || results.length > 0;
  const showRecentPanel = recentVisible || showScanSections;
  const showSidebarPanels =
    showScanSections || showRecentPanel ||
    Boolean(whoisState.loading || whoisState.error || whoisState.data);

  return (
    <div className="space-y-10">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="text-center sm:text-left">
          <p className="text-xs uppercase tracking-[0.45em] text-slate-500">{PROJECT_BADGE}</p>
          <div className="mt-2 flex items-center justify-center gap-3 sm:justify-start">
            <h1 className="text-3xl font-semibold text-slate-100">{PROJECT_NAME}</h1>
            <a
              className="icon-link"
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="View oss-subfinder on GitHub"
            >
              <GitHubIcon />
            </a>
          </div>
          <p className="mt-1 text-sm text-slate-500">{PROJECT_TAGLINE}</p>
        </div>
        <Button variant="muted" onClick={toggleTheme} className="self-center px-3 py-2 text-[11px] sm:self-auto">
          {theme === "dark" ? "Light Mode" : "Dark Mode"}
        </Button>
      </header>

      <div
        className={`grid gap-6 ${
          showSidebarPanels ? "lg:grid-cols-[minmax(0,2.6fr)_minmax(0,1fr)]" : ""
        }`}
      >
        <div className="space-y-5">
          <Panel>
            <div className="flex flex-col gap-3 md:flex-row md:items-center">
              <Input
                placeholder="example.com"
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    handleSearch(false);
                  }
                }}
                className="md:flex-1"
              />
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => handleSearch(false)} disabled={!domain.trim()} variant="primary">
                  Start
                </Button>
                <Button onClick={() => handleSearch(true)} disabled={!domain.trim()}>
                  Refresh
                </Button>
                <Button onClick={handleStop} disabled={!loading} variant="muted">
                  Stop
                </Button>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
              <Button
                variant="muted"
                className="border-none px-3"
                onClick={handleWhois}
                disabled={!domain.trim() || whoisState.loading}
              >
            {whoisState.loading ? "WHOIS…" : "WHOIS"}
              </Button>
              <Button variant="muted" className="border-none px-3" onClick={downloadCsv} disabled={!results.length}>
                Export CSV
              </Button>
            </div>
            {errorMessage && <p className="mt-3 text-xs text-rose-400">{errorMessage}</p>}
            {loading && <LoadingIndicator label={loadingLabel} />}
          </Panel>

          {!showScanSections && !recentVisible && recentScans.length > 0 && (
            <div className="flex justify-center sm:justify-end">
              <Button
                variant="muted"
                className="border-none px-3 text-[11px]"
                onClick={() => setRecentVisible(true)}
              >
                Show recent scans
              </Button>
            </div>
          )}

          {showScanSections && (
            <StageSummary
              domain={domain.trim()}
              searchingDomain={searchingDomain}
              stages={stages}
              results={results}
              loading={loading}
              lastUpdated={lastUpdated}
            />
          )}

          {showScanSections && (
            <div className="space-y-4">
              <SectionHeading label="Results" />
              <ResultsTable results={results} loading={loading} />
            </div>
          )}

          {showScanSections && (
            <HistoryPanel
              domain={domain.trim()}
              runs={historyRuns}
              meta={historyMeta}
              onSelect={handleSelectDomain}
            />
          )}
        </div>

        {showSidebarPanels && (
          <div className="space-y-5">
            {showRecentPanel && (
              <RecentScans
                items={recentScans}
                onSelect={handleSelectDomain}
                collapsible={!showScanSections}
                onHide={() => setRecentVisible(false)}
              />
            )}

            <InfoPanel title="WHOIS" loading={whoisState.loading} error={whoisState.error}>
              {whoisState.data && (
                <>
                  <p>Registrar: {whoisState.data.registrar || "—"}</p>
                  <p>Created: {whoisState.data.created || "—"}</p>
                  <p>Expires: {whoisState.data.expires || "—"}</p>
                  {whoisState.data.status?.length ? (
                    <p className="break-words font-mono text-[11px] text-slate-300">{whoisState.data.status.join(", ")}</p>
                  ) : null}
                  <details className="rounded border border-slate-800 bg-slate-950/80 p-3">
                    <summary className="cursor-pointer text-xs text-slate-400">Raw WHOIS</summary>
                    <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-slate-300">
                      {whoisState.data.raw || "—"}
                    </pre>
                  </details>
                </>
              )}
            </InfoPanel>
          </div>
        )}
      </div>

      <DonationPanel wallets={DONATION_WALLETS} copiedSymbol={copiedDonation} onCopy={handleCopyDonation} />

      <footer className="app-footer">
        <a
          className="app-footer-brand-link"
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="oss-subfinder GitHub repository"
        >
          <GitHubIcon className="app-footer-brand-icon" />
          <span>{PROJECT_NAME}</span>
        </a>
        <p className="app-footer-tagline">{PROJECT_TAGLINE}</p>
        <p className="app-footer-meta">MIT License · FastAPI · Postgres · React</p>
      </footer>
    </div>
  );
}
