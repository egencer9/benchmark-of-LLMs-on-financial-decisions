"""
NASDAQ Batch Runner — 08.05.2026 - 03.06.2026
Tüm modelleri 3 modda (Aggressive, Balanced, Conservative) test eder.
Önce yüksek kapasiteli modeller çalıştırılır.
Daha önce tamamlanmış testler atlanır.
Bir modelin API'si 404 verirse o model tamamen atlanır (zaman kaybı önlenir).
"""
import os
import sys
import yaml
import subprocess
import re

# ─── Geçersiz (404) modeller için kalıcı kara liste ─────────────────────────
# Buradaki model_name'ler OpenRouter'dan 404 aldığı bilinen ve zaten geçersiz
# olan slug'lardır. Batch başlamadan önce bu modeller pas geçilir.
KNOWN_BROKEN_MODELS = {
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3.7-sonnet",   # slug kaldırıldı
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
}

# Yüksek kapasiteli modellere öncelik vermek için anahtar kelimeler
PRIORITY_KEYWORDS = [
    "claude-sonnet-4", "o3", "o1", "gpt-4o",
    "gemini-2.5", "deepseek-r1", "deepseek-chat",
    "llama-4", "qwen3",
]

def _safe_filename(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', s)

def get_model_priority(model_name: str) -> int:
    model_lower = model_name.lower()
    for i, kw in enumerate(PRIORITY_KEYWORDS):
        if kw in model_lower:
            return i
    return len(PRIORITY_KEYWORDS)

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    config_path = os.path.join(root_dir, 'config.yaml')

    with open(config_path, 'r', encoding='utf-8') as f:
        yaml_config = yaml.safe_load(f)

    models = yaml_config.get('openrouter_models', [])

    model_items = []
    for idx, m in enumerate(models):
        # Bilinen bozuk modelleri baştan atla
        if m['model_name'] in KNOWN_BROKEN_MODELS:
            print(f"⛔ KARA LİSTE: {m['alias']} ({m['model_name']}) → atlandı")
            continue
        m = dict(m)
        m['original_index'] = idx
        m['priority'] = get_model_priority(m['model_name'])
        model_items.append(m)

    # Önceliğe göre sırala (0 = en yüksek)
    model_items.sort(key=lambda x: (x['priority'], x['alias']))

    exchange    = "NASDAQ"
    start_date  = "2026-05-15"
    end_date    = "2026-06-12"
    initial_cash = 100000
    start_str   = start_date.replace("-", "")
    end_str     = end_date.replace("-", "")
    approaches  = ["Aggressive", "Balanced", "Conservative"]

    results_dir = os.path.join(root_dir, 'data', 'results', exchange)
    os.makedirs(results_dir, exist_ok=True)

    total_runs  = len(model_items) * len(approaches)
    current_run = 0

    python_exec = os.path.join(root_dir, 'venv', 'bin', 'python')
    if not os.path.exists(python_exec):
        python_exec = sys.executable

    print(f"\n🚀 Batch backtest başlıyor: {exchange} | {start_date} → {end_date}")
    print(f"   Planlanan test: {total_runs}  ({len(model_items)} model × {len(approaches)} mod)")
    print("=" * 60)

    # Runtime 404 blacklist — çalışma sırasında 404 alınan modeller buraya eklenir
    runtime_broken: set[str] = set()

    for m in model_items:
        alias      = m['alias']
        model_idx  = m['original_index']
        model_name = m['model_name']
        safe_alias = _safe_filename(alias)

        for approach in approaches:
            current_run += 1
            label = f"[{current_run}/{total_runs}] {alias} | {approach}"

            # Runtime 404 kara listesinde mi?
            if model_name in runtime_broken:
                print(f"{label} → ⛔ RUNTIME KARA LİSTE (404 daha önce alındı) — atlandı")
                continue

            # Çıktı dosyası zaten var mı?
            out_file = f"{exchange}_{safe_alias}_{approach}_{start_str}_{end_str}.json"
            out_path = os.path.join(results_dir, out_file)
            if os.path.exists(out_path):
                print(f"{label} → ✅ ZATEN MEVCUT — atlandı")
                continue

            # Eski typo dosyası var mı? (örn. _2026063.json)
            typo_file = f"{exchange}_{safe_alias}_{approach}_{start_str}_2026063.json"
            if os.path.exists(os.path.join(results_dir, typo_file)):
                print(f"{label} → ✅ ZATEN MEVCUT (typo) — atlandı")
                continue

            print(f"\n{label} → ▶️  ÇALIŞTIRILIYOR...")

            cmd = [
                python_exec,
                os.path.join(root_dir, "src", "main.py"),
                "--model", str(model_idx),
                "--exchange", exchange,
                "--start-date", start_date,
                "--end-date", end_date,
                "--cash", str(initial_cash),
                "--trading-approach", approach,
            ]

            result = subprocess.run(cmd, cwd=root_dir, capture_output=False)

            if result.returncode != 0:
                # Çıkış kodu sıfır değilse log'a bak: 404 mü yoksa başka bir hata mı?
                # main.py 404 alırsa 0 ile de çıkabilir (HOLD defaultu); bu yüzden
                # sonuç dosyasının oluşup oluşmadığını kontrol ediyoruz.
                if not os.path.exists(out_path):
                    print(f"{label} → ❌ HATA (çıkış kodu {result.returncode}) — model kara listeye alınıyor")
                    runtime_broken.add(model_name)
                else:
                    print(f"{label} → ⚠️  Uyarı ile tamamlandı (çıkış kodu {result.returncode}) ama dosya oluştu")
            else:
                if os.path.exists(out_path):
                    print(f"{label} → 🎉 BAŞARILI")
                else:
                    # Dosya oluşmadıysa büyük ihtimalle 404 — kara listeye al
                    print(f"{label} → ⚠️  Tamamlandı ama çıktı dosyası YOK → model kara listeye alınıyor")
                    runtime_broken.add(model_name)

            print("-" * 50)

    print("\n✅ Tüm batch testleri tamamlandı!")
    if runtime_broken:
        print(f"⛔ Runtime'da 404 alınan ve atlanan modeller: {runtime_broken}")

if __name__ == "__main__":
    main()
