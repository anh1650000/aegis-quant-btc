import { ref } from "vue";

export function useCurrency(initialRate = 25716) {
  const saved = typeof window !== "undefined" ? window.localStorage.getItem("aegis_currency") : null;
  const currency = ref(saved === "VND" ? "VND" : "USDT");
  const vndRate = ref(initialRate);

  function setCurrency(next) {
    currency.value = next === "VND" ? "VND" : "USDT";
    if (typeof window !== "undefined") {
      window.localStorage.setItem("aegis_currency", currency.value);
    }
  }

  function toggleCurrency() {
    setCurrency(currency.value === "USDT" ? "VND" : "USDT");
  }

  function setVndRate(rate) {
    const num = Number(rate);
    if (Number.isFinite(num) && num > 10000) {
      vndRate.value = num;
    }
  }

  function formatMoney(usdValue, options = {}) {
    const { decimals = 2, compact = false } = options;
    if (usdValue === null || usdValue === undefined || Number.isNaN(Number(usdValue))) {
      return "—";
    }
    const val = Number(usdValue);

    if (currency.value === "VND") {
      const vnd = val * vndRate.value;
      if (compact) {
        if (Math.abs(vnd) >= 1e9) {
          return `${(vnd / 1e9).toFixed(2)} tỷ ₫`;
        }
        if (Math.abs(vnd) >= 1e6) {
          return `${(vnd / 1e6).toFixed(1)} tr ₫`;
        }
      }
      return `${Math.round(vnd).toLocaleString("en-US")} ₫`;
    }

    if (compact) {
      if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
      if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
    }
    return `$${val.toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })}`;
  }

  function formatAltMoney(usdValue, decimals = 2) {
    if (usdValue === null || usdValue === undefined || Number.isNaN(Number(usdValue))) {
      return "";
    }
    const val = Number(usdValue);
    if (currency.value === "VND") {
      return `$${val.toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}`;
    }
    return `${Math.round(val * vndRate.value).toLocaleString("en-US")} ₫`;
  }

  return {
    currency,
    vndRate,
    setCurrency,
    toggleCurrency,
    setVndRate,
    formatMoney,
    formatAltMoney,
  };
}
