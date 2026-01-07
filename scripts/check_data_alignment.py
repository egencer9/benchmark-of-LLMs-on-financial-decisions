import sys
import os
import pandas as pd

# Proje ana dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logger import log

def check_data_alignment():
    """
    Market ve Haber verilerinin tarihsel olarak örtüşüp örtüşmediğini kontrol eder.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    market_data_path = os.path.join(project_root, 'data', 'market_data.csv')
    news_data_path = os.path.join(project_root, 'data', 'news_data.csv')

    if not os.path.exists(market_data_path) or not os.path.exists(news_data_path):
        log.error("Veri dosyaları (market_data.csv veya news_data.csv) bulunamadı.")
        return

    log.info("Veri dosyaları analiz ediliyor...")
    try:
        market_df = pd.read_csv(market_data_path)
        news_df = pd.read_csv(news_data_path)
    except Exception as e:
        log.error(f"Dosya okuma hatası: {e}")
        return

    # Tarih dönüşümleri
    if 'Date' in market_df.columns:
        market_dates = set(pd.to_datetime(market_df['Date']).dt.date)
    else:
        log.error("Market verisinde 'Date' sütunu yok.")
        return

    if 'publishedAt' in news_df.columns:
        news_dates = set(pd.to_datetime(news_df['publishedAt']).dt.date)
    else:
        log.error("Haber verisinde 'publishedAt' sütunu yok.")
        return

    # Kesişim ve Farklar
    common_days = market_dates.intersection(news_dates)
    missing_news_days = market_dates - news_dates

    log.info(f"--- Veri Uyumluluk Raporu ---")
    log.info(f"Toplam Piyasa Günü: {len(market_dates)}")
    log.info(f"Haber Olan Gün Sayısı: {len(news_dates)}")
    log.info(f"Tam Eşleşen Gün Sayısı: {len(common_days)}")
    
    if missing_news_days:
        log.warning(f"Haber Verisi EKSİK Olan Günler ({len(missing_news_days)} gün):")
        for d in sorted(list(missing_news_days)):
            log.warning(f" - {d}")
    else:
        log.info("Harika! Tüm piyasa günleri için haber verisi mevcut.")

if __name__ == "__main__":
    check_data_alignment()