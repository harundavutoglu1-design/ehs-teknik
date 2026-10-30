import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import qrcode  # İnternet bağımlılığını bitiren yerel kütüphane
from io import BytesIO

# Sayfa Yapılandırması
st.set_page_config(page_title="EHS Güvenlik Teknik Servis & Cari Otomasyonu", page_icon="🛠️", layout="wide")

# =====================================================================
# 1. VERİ TABANI SİMÜLASYONU
# =====================================================================
if 'cariler' not in st.session_state:
    st.session_state.cariler = pd.DataFrame([
        {"Cari ID": 1001, "Müşteri Adı": "Ahmet Yılmaz", "Telefon": "0532 111 2233", "Bakiye (TL)": 0.0},
        {"Cari ID": 1002, "Müşteri Adı": "Mehmet Demir", "Telefon": "0544 333 4455", "Bakiye (TL)": 1500.0}
    ])
if 'servis_kayitlari' not in st.session_state:
    st.session_state.servis_kayitlari = pd.DataFrame(columns=[
        "Servis ID", "Müşteri Adı", "Telefon", "Cihaz", "Müşteri Şikayeti", "Durum", "Tarih"
    ])

# 🔗 URL PARAMETRE YAKALAYICI
try:
    if hasattr(st, "query_params"):
        query_params = st.query_params
    else:
        query_params = st.experimental_get_query_params()
except Exception:
    query_params = {}

is_customer_mode = False
if "mod" in query_params:
    val = query_params["mod"]
    is_customer_mode = (val == "musteri" if not isinstance(val, list) else "musteri" in val)

# =====================================================================
# 📱 MÜŞTERI EKRANI (Ortak QR Okutunca Açılan Panel)
# =====================================================================
if is_customer_mode:
    st.title("📱 EHS Güvenlik - Dijital Arıza Bildirim Formu")
    st.write("Lütfen cihazınızdaki arıza bilgilerini ve iletişim detaylarınızı doldurunuz.")
    st.write("---")

    with st.form("musteri_ariza_formu"):
        m_isim = st.text_input("Adınız Soyadınız / Firma Ünvanınız")
        m_tel = st.text_input("Telefon Numaranız")
        m_cihaz = st.text_input("Cihazınızın Marka ve Modeli")
        m_sikayet = st.text_area("Cihazdaki Arıza / Şikayetiniz Nedir?")
        gonder_btn = st.form_submit_button("🚀 Arıza Kaydını Teknik Servise Gönder")

        if gonder_btn:
            if m_isim and m_tel and m_cihaz and m_sikayet:
                yeni_s_id = len(st.session_state.servis_kayitlari) + 7001
                yeni_talep = pd.DataFrame([{
                    "Servis ID": yeni_s_id,
                    "Müşteri Adı": m_isim,
                    "Telefon": m_tel,
                    "Cihaz": m_cihaz,
                    "Müşteri Şikayeti": m_sikayet,
                    "Durum": "Bekliyor",
                    "Tarih": datetime.date.today().strftime("%Y-%m-%d")
                }])
                st.session_state.servis_kayitlari = pd.concat([st.session_state.servis_kayitlari, yeni_talep],
                                                              ignore_index=True)
                st.success(f"🎉 Arıza kaydınız başarıyla alındı! Takip Numaranız: **#{yeni_s_id}**")
                st.balloons()
            else:
                st.error("⚠️ Lütfen formdaki tüm alanları eksiksiz doldurunuz.")

# =====================================================================
# 🏢 GENEL YÖNETİM PANELİ (Personel & Cari Paneli)
# =====================================================================
else:
    st.sidebar.title("🏢 EHS Güvenlik Panel Menüsü")
    sayfa = st.sidebar.radio("Gitmek İstediğiniz Panel:",
                             ["📊 Genel Durum & Servis", "👥 Cari / Müşteri Yönetimi", "📷 EHS Güvenlik Sabit QR Kodu"])

    # SAYFA 1: SERVİS YÖNETİMİ
    if sayfa == "📊 Genel Durum & Servis":
        st.title("🛠️ EHS Güvenlik Teknik Servis Paneli")
        st.write("Müşterilerden gelen arıza taleplerini yönetebilir ve durumlarını güncelleyebilirsiniz.")
        st.write("---")

        if not st.session_state.servis_kayitlari.empty:
            col1, col2 = st.columns(2)
            col1.metric("Toplam Servis Kaydı", len(st.session_state.servis_kayitlari))
            col2.metric("Bekleyen Arıza Talebi", len(
                st.session_state.servis_kayitlari[st.session_state.servis_kayitlari["Durum"] == "Bekliyor"]))

        st.subheader("📋 Gelen Servis Kayıtları")
        if st.session_state.servis_kayitlari.empty:
            st.info("Henüz sisteme girilmiş bir arıza veya servis kaydı bulunmamaktadır.")
        else:
            guncellenen_df = st.data_editor(
                st.session_state.servis_kayitlari,
                column_config={
                    "Durum": st.column_config.SelectboxColumn("Durum", options=["Bekliyor", "İşlemde", "Tamamlandı",
                                                                                "İptal Edildi"], required=True)
                },
                disabled=["Servis ID", "Müşteri Adı", "Telefon", "Cihaz", "Müşteri Şikayeti", "Tarih"],
                hide_index=True,
                use_container_width=True
            )
            if st.button("💾 Servis Durumlarını Kaydet"):
                st.session_state.servis_kayitlari = guncellenen_df
                st.success("Servis kayıtları başarıyla güncellendi!")

    # SAYFA 2: CARİ YÖNETİMİ
    elif sayfa == "👥 Cari / Müşteri Yönetimi":
        st.title("👥 Cari ve Müşteri Yönetim Paneli")
        st.write("Sistemdeki müşterileri listeleyebilir, yeni müşteri ekleyebilir veya silebilirsiniz.")
        st.write("---")

        sekme_listele, sekme_ekle, sekme_sil = st.tabs(["📋 Cari Listesi", "➕ Yeni Müşteri Ekle", "❌ Müşteri Sil"])

        with sekme_listele:
            st.subheader("Mevcut Cari Hesaplar")
            guncel_cariler = st.data_editor(
                st.session_state.cariler,
                disabled=["Cari ID"],
                hide_index=True,
                use_container_width=True
            )
            if st.button("💾 Cari Bilgilerini ve Bakiyeleri Güncelle"):
                st.session_state.cariler = guncel_cariler
                st.success("Cari kartları başarıyla güncellendi!")

        with sekme_ekle:
            st.subheader("Yeni Cari Kart Oluştur")
            with st.form("yeni_cari_formu", clear_on_submit=True):
                c_adi = st.text_input("Müşteri Adı Soyadı / Firma Ünvanı")
                c_tel = st.text_input("Telefon Numarası")
                c_bakiye = st.number_input("Açılış Bakiyesi (TL)", min_value=0.0, step=100.0)
                ekle_btn = st.form_submit_button("💾 Cariyi Kaydet")

                if ekle_btn:
                    if c_adi and c_tel:
                        yeni_id = st.session_state.cariler[
                                      "Cari ID"].max() + 1 if not st.session_state.cariler.empty else 1001
                        yeni_cari = pd.DataFrame(
                            [{"Cari ID": yeni_id, "Müşteri Adı": c_adi, "Telefon": c_tel, "Bakiye (TL)": c_bakiye}])
                        st.session_state.cariler = pd.concat([st.session_state.cariler, yeni_cari], ignore_index=True)
                        st.success(f"✔️ {c_adi} başarıyla sisteme eklendi. (Cari ID: {yeni_id})")
                        st.rerun()
                    else:
                        st.error("⚠️ Adı ve Telefon alanları boş bırakılamaz.")

        with sekme_sil:
            st.subheader("Sistemden Cari Kart Sil")
            if st.session_state.cariler.empty:
                st.warning("Silinecek müşteri bulunamadı.")
            else:
                silinecek_musteri = st.selectbox(
                    "Silmek istediğiniz müşteriyi seçiniz:",
                    options=st.session_state.cariler["Müşteri Adı"].tolist()
                )
                if st.button("❌ Seçilen Cariyi Tamamen Sil", type="primary"):
                    st.session_state.cariler = st.session_state.cariler[
                        st.session_state.cariler["Müşteri Adı"] != silinecek_musteri]
                    st.success(f"🗑️ {silinecek_musteri} sistemden başarıyla kaldırıldı.")
                    st.rerun()

    # -----------------------------------------------------------------
    # SAYFA 3: %100 YEREL VE ÇEVRİMDIŞI QR KOD ÜRETİCİ
    # -----------------------------------------------------------------
    elif sayfa == "📷 EHS Güvenlik Sabit QR Kodu":
        st.title("📷 EHS Güvenlik İletişim & Arıza Bildirim QR Kodu")
        st.write("Dış API'lere bağımlı olmayan, tamamen lokal çalışan güvenli QR kod motoru.")
        st.write("---")

        ana_url = "http://localhost:8501"
        sabit_form_url = f"{ana_url}?mod=musteri"

        st.info(f"🔗 Müşterilerinizin Yönlendirileceği Link: {sabit_form_url}")

        # QR Kodu bellekte sıfırdan oluşturma mantığı
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(sabit_form_url)
        qr.make(fit=True)

        # Görseli RAM üzerinde Byte formatına çevirip Streamlit'e besleme
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        byte_im = buf.getvalue()

        col_qr, col_bilgi = st.columns(2)
        with col_qr:
            st.image(byte_im, caption="EHS Güvenlik İletişim QR Kodu", width=300)
        with col_bilgi:
            st.subheader("💡 QR Kod Neden Artık Görünüyor?")
            st.markdown(
                "- Tarayıcınız veya internet servis sağlayıcınız dış kaynaklı (Google/QuickChart vb.) dinamik resim oluşturma isteklerini engelliyordu.")
            st.markdown(
                "- Yeni güncellemeyle QR kod **doğrudan bilgisayarınızın içinde üretilir**, harici internet sitelerine bağlantı kurma ihtiyacını tamamen ortadan kaldırır.")