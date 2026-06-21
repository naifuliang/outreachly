import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { SUPPORTED_LANGUAGES } from "./i18n";

interface Health {
  status: string;
  version: string;
  locales: string[];
}

export default function App() {
  const { t, i18n } = useTranslation();
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((data: Health) => setHealth(data))
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  const phases = ["p0", "p1", "p2", "p3", "p4", "p5", "p6"] as const;

  return (
    <div className="container">
      <header className="top">
        <div>
          <h1>{t("app.name")}</h1>
          <p className="tagline">{t("app.tagline")}</p>
        </div>
        <div className="lang-switch" aria-label={t("nav.language")}>
          {SUPPORTED_LANGUAGES.map((lng) => (
            <button
              key={lng}
              className={i18n.resolvedLanguage === lng ? "active" : ""}
              onClick={() => void i18n.changeLanguage(lng)}
            >
              {lng === "zh" ? "中文" : "EN"}
            </button>
          ))}
        </div>
      </header>

      <p>{t("home.intro")}</p>

      <section className="panel status">
        <strong>{t("home.backendStatus")}</strong>
        <p>
          {loading ? (
            t("home.checking")
          ) : health ? (
            <>
              <span className="dot ok" />
              {t("home.online", { version: health.version })}
            </>
          ) : (
            <>
              <span className="dot bad" />
              {t("home.offline")}
            </>
          )}
        </p>
      </section>

      <section className="panel">
        <strong>{t("home.roadmap")}</strong>
        <ul className="phases">
          {phases.map((p) => (
            <li key={p}>{t(`phases.${p}`)}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
