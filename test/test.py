import sys
import os
import google.generativeai as genai

# Projenin ana dizinini Python yoluna ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GEMINI_API_KEY
from src.logger import log

def run_test():
    """
    Bu script, Gemini API bağlantısını ve model bilgilerini kontrol etmek için
    basit bir test gerçekleştirir.
    """
    log.info("--- Gemini API Test Script ---")

    if not GEMINI_API_KEY:
        log.error("GEMINI_API_KEY bulunamadı. Lütfen .env dosyanızı kontrol edin.")
        return

    try:
        # API anahtarını yapılandır
        genai.configure(api_key=GEMINI_API_KEY)
        log.info("Gemini API anahtarı başarıyla yapılandırıldı.")

        # Kullanacağımız modeli tanımla
        model_name = 'gemini-2.5-flash-lite'
        model = genai.GenerativeModel(model_name)
        log.info(f"Model '{model_name}' başarıyla yüklendi.")

        # Modele basit bir soru sorarak test et
        log.info("Modele test sorusu gönderiliyor: 'AI nedir?'")
        response = model.generate_content("AI nedir?")
        
        log.info("Modelden yanıt alındı:")
        log.info(f"---\n{response.text}\n---")

        # Modelin token limitleri gibi bilgilerini al (isteğe bağlı)
        model_info = genai.get_model(f'models/{model_name}')
        log.info(f"Model Bilgileri: {model_name}")
        log.info(f" - Input Token Limiti: {model_info.input_token_limit}")
        log.info(f" - Output Token Limiti: {model_info.output_token_limit}")

    except Exception as e:
        log.error(f"Test sırasında bir hata oluştu: {e}", exc_info=True)

if __name__ == "__main__":
    run_test()
