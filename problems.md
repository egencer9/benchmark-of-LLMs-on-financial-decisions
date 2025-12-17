# Proje Problemleri ve Çözüm Yolları

Bu doküman, `nasdaq-llm-trader` projesinde karşılaşılan ve loglarda tespit edilen teknik sorunları ve bunların nasıl çözüleceğini açıklamaktadır.

## 1. Problem: API Kota Aşımı Hatası (Error 429)

### Belirtiler

Loglarda sürekli olarak aşağıdaki gibi bir hata görülmektedir:
`ERROR | llm_agent:_get_gemini_decision:76 - Error calling Gemini API: 429 You exceeded your current quota...`

Bu hata, Gemini API'nin ücretsiz kullanım katmanının "dakika başına istek" limitine takıldığımızı göstermektedir. Paralel çalışma mantığı, kısa bir süre içinde çok fazla istek göndererek bu kotayı anında doldurmaktadır.

### Kök Neden

`llm_agent.py` içerisindeki `ThreadPoolExecutor`, tüm API isteklerini aynı anda göndermeye çalışır. Ancak Gemini gibi servislerin ücretsiz katmanları, genellikle dakika başına 10-15 istek gibi limitlere sahiptir. Paralel yapı, bu limitleri göz ardı ettiği için API sunucusu istekleri reddetmekte ve program, hata durumunda tanımlanan sahte (dummy) yanıta geri dönmektedir.

Bu durum, simülasyonun gerçek yapay zeka kararlarıyla değil, sürekli aynı sahte yanıtla çalışmasına neden olmaktadır.

## 2. Problem: Takip Edilmeyen Hisse Senedi Uyarısı

### Belirtiler

Loglarda sıkça şu uyarı görülmektedir:
`WARNING | backtester:run_backtest:121 - LLM returned decision for untracked ticker MSFT. Ignoring.`

### Kök Neden

Bu sorun, doğrudan 1. Problemin bir sonucudur. API kota hatası nedeniyle program sahte (dummy) bir yanıt kullanır. Bu sahte yanıt, statik olarak `AAPL` ve `MSFT` için kararlar içerir.

Ancak, simülasyonun o günkü veri setinde (`current_prices`) `MSFT` için bir fiyat bilgisi bulunmuyorsa (örneğin, o güne ait veri eksikse), backtest motoru bu hisse için bir işlem yapamaz ve "takip edilmeyen hisse" uyarısı verir. Yani, sahte yanıtın içeriği ile o günkü mevcut piyasa verisi arasında bir uyumsuzluk oluşmaktadır.

Bu, kendi başına bir bug olmasa da, kota sorunu çözülmediği sürece kafa karıştırıcı uyarılara neden olan bir semptomdur.

## Çözüm Stratejisi

1.  **API Kota Sorununu Çözmek:** `llm_agent.py` içinde, API isteklerini gönderen fonksiyonlara "yeniden deneme" (retry) mekanizması eklenecektir. Bir 429 kota hatası alındığında, program hemen pes etmek yerine, API'nin önerdiği süre kadar bekleyip isteği birkaç kez daha tekrarlayacaktır.

2.  **Dinamik Sahte Yanıt:** Hata durumlarında kullanılan sahte yanıt fonksiyonu (`_get_dummy_response`), artık statik olmak yerine, o gün işlem gören hisselerin bir listesini parametre olarak alacak ve sadece o hisseler için bir sahte yanıt üretecektir.
