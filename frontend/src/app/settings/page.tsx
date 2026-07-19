"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Settings, Eye, EyeOff, Loader2, Save, CheckCircle, AlertTriangle } from "lucide-react";

export default function SettingsPage() {
  const [form, setForm] = useState({
    MISTRAL_API_KEY: "",
    OPENAI_API_KEY: "",
    ANTHROPIC_API_KEY: "",
    GOOGLE_API_KEY: "",
    GITHUB_TOKEN: "",
  });

  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    api.config
      .get()
      .then((data) => {
        setForm({
          MISTRAL_API_KEY: data.MISTRAL_API_KEY || "",
          OPENAI_API_KEY: data.OPENAI_API_KEY || "",
          ANTHROPIC_API_KEY: data.ANTHROPIC_API_KEY || "",
          GOOGLE_API_KEY: data.GOOGLE_API_KEY || "",
          GITHUB_TOKEN: data.GITHUB_TOKEN || "",
        });
      })
      .catch((err) => {
        setError(err.message || "Failed to load configuration settings.");
      })
      .finally(() => setLoading(false));
  }, []);

  const toggleVisibility = (key: string) => {
    setVisibleKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleInputChange = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const res = await api.config.save(form);
      setSuccess(res.message || "Settings updated successfully!");
      // Reload configurations to get fresh masked fields
      const freshData = await api.config.get();
      setForm({
        MISTRAL_API_KEY: freshData.MISTRAL_API_KEY || "",
        OPENAI_API_KEY: freshData.OPENAI_API_KEY || "",
        ANTHROPIC_API_KEY: freshData.ANTHROPIC_API_KEY || "",
        GOOGLE_API_KEY: freshData.GOOGLE_API_KEY || "",
        GITHUB_TOKEN: freshData.GITHUB_TOKEN || "",
      });
    } catch (err: any) {
      setError(err.message || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  const fields = [
    {
      key: "GITHUB_TOKEN",
      label: "GitHub Personal Access Token (Optional)",
      placeholder: "ghp_...",
      description: "Optional for public repositories. Required to clone private repositories and automatically open Pull Requests.",
    },
    {
      key: "MISTRAL_API_KEY",
      label: "Mistral AI API Key",
      placeholder: "your_mistral_api_key",
      description: "Primary LLM key used for the LangGraph code fixing pipeline.",
    },
    {
      key: "OPENAI_API_KEY",
      label: "OpenAI API Key (Optional)",
      placeholder: "sk-...",
      description: "Fallback LLM provider key.",
    },
    {
      key: "ANTHROPIC_API_KEY",
      label: "Anthropic Claude API Key (Optional)",
      placeholder: "sk-ant-...",
      description: "Fallback LLM provider key.",
    },
    {
      key: "GOOGLE_API_KEY",
      label: "Google Gemini API Key (Optional)",
      placeholder: "AIzaSy...",
      description: "Fallback LLM provider key.",
    },
  ];

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <div className="mb-8 text-center">
        <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-brand-600/20 border border-brand-500/30 mb-4">
          <Settings className="h-7 w-7 text-brand-400" />
        </div>
        <h1 className="section-title text-3xl">Configuration Settings</h1>
        <p className="section-subtitle mt-2">
          Configure API credentials and tokens dynamically. Saved values are kept on the shared persistent volume.
        </p>
      </div>

      {loading ? (
        <div className="card flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-brand-400" />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="card space-y-6">
          <div className="space-y-4">
            {fields.map(({ key, label, placeholder, description }) => {
              const isVisible = !!visibleKeys[key];
              const value = form[key as keyof typeof form];
              const isPlaceholder = value === "••••••••";

              return (
                <div key={key} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="label mb-0">{label}</label>
                    {isPlaceholder && (
                      <span className="text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-500/20 px-2 py-0.5 rounded-full font-medium">
                        Configured
                      </span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type={isVisible ? "text" : "password"}
                      className="input pr-10"
                      placeholder={placeholder}
                      value={value}
                      onFocus={(e) => {
                        e.target.select();
                      }}
                      onChange={(e) => handleInputChange(key, e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => !isPlaceholder && toggleVisibility(key)}
                      disabled={isPlaceholder}
                      className={`absolute right-3 top-1/2 -translate-y-1/2 transition-colors ${
                        isPlaceholder ? "text-slate-700 cursor-not-allowed" : "text-slate-500 hover:text-slate-300"
                      }`}
                      title={isPlaceholder ? "Saved secret keys cannot be revealed for security" : isVisible ? "Hide Key" : "Show Key"}
                    >
                      {isVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  <p className="text-xs text-slate-500">{description}</p>
                </div>
              );
            })}
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm bg-red-900/20 border border-red-700/30 rounded-lg p-3">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 text-emerald-400 text-sm bg-emerald-900/20 border border-emerald-700/30 rounded-lg p-3">
              <CheckCircle className="h-4 w-4 shrink-0" />
              {success}
            </div>
          )}

          <button
            type="submit"
            className="btn-primary w-full justify-center py-3 text-base"
            disabled={saving}
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Save Settings
              </>
            )}
          </button>
        </form>
      )}
    </div>
  );
}
