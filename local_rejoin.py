#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, json, subprocess, requests, sys
from colorama import Fore, Style, init
init(autoreset=True)

CONFIG_FILE = "config.json"
SERVER_LINKS_FILE = "Private_Link.txt"
ACCOUNTS_FILE = "Account.txt"
WEBHOOK_FILE = "Webhook.txt"
ANDROID_ID = "b419fa14320149db"

# ============ Fungsi utilitas ============
def msg(text, type="info"):
    print(text)

def prompt(text):
    return input(text+" ").strip()

def clear():
    os.system("clear" if os.name == "posix" else "cls")

def wait_back_menu():
    input("[Tekan Enter untuk kembali ke menu]")
    os.system("clear")
 
def run_cmd(cmd, check_success=True):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if check_success:
            return result.returncode == 0
        return result
    except Exception as e:
        print(f"Kesalahan saat menjalankan perintah {cmd}: {e}")
        return False
     
# ============ File IO ============
def load_pairs(path):
    if not os.path.exists(path):
        return []
    pairs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue
            a, b = line.split(",", 1)
            pairs.append((a.strip(), b.strip()))
    return pairs

def save_pairs(path, pairs):
    with open(path, "w", encoding="utf-8") as f:
        for a, b in pairs:
            f.write(f"{a},{b}\n")

def load_accounts():
    return load_pairs(ACCOUNTS_FILE)

def save_accounts(accs):
    save_pairs(ACCOUNTS_FILE, accs)

def load_server_links():
    return load_pairs(SERVER_LINKS_FILE)

def save_server_links(links):
    save_pairs(SERVER_LINKS_FILE, links)

# ============ Aksi Roblox ============
def get_custom_packages():
    # Kata kunci untuk mengenali paket
    keywords = ["roblox", "fluxus","codex","delta","arceus"]

    result = subprocess.run(
        "pm list packages",
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    pkgs = []
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        pkg = line.split(":", 1)[1].strip()
        # Simpan jika nama berisi salah satu kata kunci
        if any(keyword in pkg.lower() for keyword in keywords):
            pkgs.append(pkg)
    return pkgs

def kill_roblox_process(package):
    try:
        subprocess.run(["pkill", "-f", package], check=False)
        print(f"[✓] Sudah kill {package}")
    except Exception as e:
        print(f"[!] Kesalahan saat kill {package}: {e}")
    time.sleep(2)

def format_server_link(link):
    link = link.strip()
    if not link:
        return ""
    if "roblox.com" in link or link.startswith("roblox://"):
        return link
    if link.isdigit():
        return f"roblox://placeID={link}"
    return ""

def launch_roblox(package, server_link):
    if not server_link:
        return
    try:
        subprocess.run([
            "am", "start", "-n",
            f"{package}/com.roblox.client.startup.ActivitySplash",
            "-d", server_link,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        subprocess.run([
            "am", "start", "-n",
            f"{package}/com.roblox.client.ActivityProtocolLaunch",
            "-d", server_link,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        msg(f"[!] Kesalahan membuka Roblox: {e}", "err")

# ============ Config & Direktori reconnect ============
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(cfg):
    json.dump(cfg, open(CONFIG_FILE,"w",encoding="utf-8"), indent=2)

import os

def find_reconnect_dirs(bases=None):
    if bases is None:
        bases = [
            "/sdcard/Android/data",
            "/storage/emulated/0"
        ]
    
    results = []
    for base in bases:
        if not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            if "Workspace" in dirs:
                workspace_dir = os.path.join(root, "Workspace")
                reconnect_dir = os.path.join(workspace_dir, "Reconnect")
                if not os.path.exists(reconnect_dir):
                    try:
                        os.makedirs(reconnect_dir, exist_ok=True)
                        print(Fore.LIGHTGREEN_EX + f"Sudah membuat direktori: {reconnect_dir}")
                    except Exception as e:
                        print(Fore.LIGHTRED_EX + f"Kesalahan membuat direktori {reconnect_dir}: {e}")
                        continue
                results.append(reconnect_dir)
    return results

def find_autoexecute_dirs(bases=None):
    if bases is None:
        bases = [
            "/sdcard/Android/data",
            "/storage/emulated/0"
        ]
    results = []
    for base in bases:
        if not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            # Jika ada direktori "Autoexecute" atau "Autoexec"
            for dirname in ["Autoexecute", "Autoexec"]:
                if dirname in dirs:
                    results.append(os.path.join(root, dirname))
    return results

# ============ Heartbeat ============
def read_heartbeat(path):
    try:
        if not os.path.exists(path):
            return (False, 1e9, "", "Tidak menemukan file heartbeat")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        status = data.get("status", "")
        ts = float(data.get("timestamp", 0))
        user = data.get("user", "")
        age = time.time() - ts

        if status.lower() != "online":
            return (False, age, user, "Status bukan 'online'")
        if abs(age) > 60:
            return (False, age, user, f"Heartbeat terlalu lama ({age:.0f}s)")
        return (True, age, user, "OK")
    except Exception as e:
        return (False, 1e9, "", f"Kesalahan membaca JSON: {e}")

# ============ Webhook ============
def set_webhook(url, user_id=""):
    with open(WEBHOOK_FILE, "w", encoding="utf-8") as f:
        f.write(url.strip() + "\n" + user_id.strip())

def get_webhook():
    if not os.path.exists(WEBHOOK_FILE):
        return "", ""
    lines = open(WEBHOOK_FILE, "r", encoding="utf-8").read().splitlines()
    url = lines[0].strip() if len(lines) > 0 else ""
    uid = lines[1].strip() if len(lines) > 1 else ""
    return url, uid

def send_webhook(msgtxt):
    url, uid = get_webhook()
    if not url:
        return
    try:
        if uid:
            content = f"<@{uid}> {msgtxt}"
        else:
            content = msgtxt
        requests.post(url, json={"content": content}, timeout=5)
    except:
        pass

def disable_bloatware_apps():
    print(Fore.LIGHTBLUE_EX + "Sedang menonaktifkan aplikasi yang tidak diperlukan (daftar aman)...")
    apps_to_disable = [
        "com.wsh.toolkit", "com.wsh.appstorage", "com.wsh.launcher2", 
        "com.og.toolcenter", "com.og.gamecenter",
        "com.wsh.appstore", "com.android.tools", 
        "net.sourceforge.opencamera",
        # Aplikasi galeri dari OEM , "com.og.launcher"
        "com.sec.android.gallery3d", "com.miui.gallery", "com.coloros.gallery3d",
        "com.vivo.gallery", "com.motorola.gallery", "com.transsion.gallery",
        "com.sonyericsson.album", "com.lge.gallery", "com.htc.album", "com.huawei.photos",
        "com.android.gallery3d", "com.android.gallery",
        # Jam/Alarm OEM (untuk menghindari duplikat dengan jam default)
        "com.sec.android.app.clockpackage", "com.miui.clock", "com.coloros.alarmclock",
        "com.vivo.alarmclock", "com.motorola.timeweatherwidget",
        "com.huawei.clock", "com.lge.clock", "com.htc.alarmclock",
        # Lainnya yang jarang digunakan
        "com.android.dreams.basic", "com.android.dreams.phototable",
        "com.android.wallpaperbackup", "com.android.wallpapercropper"
    ]
    for package_name in apps_to_disable:
        if run_cmd(["pm", "disable-user", "--user", "0", package_name], check_success=False):
            print(Fore.LIGHTGREEN_EX + f"Sudah menonaktifkan: {package_name}")
        else:
            print(Fore.LIGHTYELLOW_EX + f"Lewati atau tidak dapat menonaktifkan: {package_name}")

def set_android_id():
    global ANDROID_ID
    user_input = input(f"Masukkan Android ID baru (Enter untuk menggunakan default: {ANDROID_ID}): ").strip()
    if user_input:
        ANDROID_ID = user_input

    print(Fore.LIGHTYELLOW_EX + f"Sedang mengatur Android ID menjadi {ANDROID_ID}...", end=" ")
    if run_cmd(["settings", "put", "secure", "android_id", ANDROID_ID], check_success=True):
        print(Fore.LIGHTGREEN_EX + "Selesai")
        return True
    else:
        print(Fore.LIGHTRED_EX + "Tidak dapat mengatur Android ID")
        return False

def disable_animations():
    print(Fore.LIGHTYELLOW_EX + "Sedang mematikan efek animasi Android...", end=" ")
    animation_settings = [
        ["settings", "put", "global", "window_animation_scale", "0"],
        ["settings", "put", "global", "transition_animation_scale", "0"],
        ["settings", "put", "global", "animator_duration_scale", "0"]
    ]
    success = True
    for cmd in animation_settings:
        if not run_cmd(cmd, check_success=True):
            print(Fore.LIGHTRED_EX + f"Tidak dapat mematikan {cmd[3]}")
            success = False
    if success:
        print(Fore.LIGHTGREEN_EX + "Berhasil mematikan semua efek animasi")
    return success

# ============ FUNGSI MENU ============
# /1: Auto Rejoin (Diperbarui dengan Restart Berkala)
def auto_rejoin():
    cfg = load_config()
    reconnect_dir = cfg.get("reconnect_dir")
    
    # Muat interval restart
    restart_intervals = cfg.get("restart_intervals", {}) 
    # Kamus untuk melacak waktu restart terakhir: { "package_name": timestamp }
    last_restart_track = {} 

    if not reconnect_dir or not os.path.exists(reconnect_dir):
        found = find_reconnect_dirs()
        if not found:
            reconnect_dir = prompt("Tidak menemukan. Masukkan jalur Reconnect secara manual:")
        elif len(found) == 1:
            reconnect_dir = found[0]
        else:
            print("Menemukan beberapa direktori:")
            for i, d in enumerate(found):
                print(f"{i+1}. {d}")
            idx = int(input("Pilih nomor: ")) - 1
            reconnect_dir = found[idx]
        cfg["reconnect_dir"] = reconnect_dir
        save_config(cfg)

    accounts = load_accounts()  # (package, username)
    links = dict(load_server_links())
    for pkg in list(links.keys()):
        links[pkg] = format_server_link(links[pkg])

    # Inisialisasi waktu pelacakan untuk semua akun ke waktu saat ini
    # sehingga mereka tidak restart segera saat membuka tool
    for pkg, _ in accounts:
        last_restart_track[pkg] = time.time()

    msg("[i] Memulai auto rejoin lokal...", "info")
    
    # Periksa info interval
    print(Fore.LIGHTCYAN_EX + "--- Konfigurasi Auto Restart ---")
    for pkg, mins in restart_intervals.items():
        if mins > 0:
            print(f"> {pkg}: {mins} menit")
    print("-----------------------------")

    try:
        while True:
            clear()
            msg("[i] Memulai siklus cek baru...", "info")
            current_time = time.time()

            for pkg, username in accounts:
                # --- CEK 1: Restart Berkala ---
                interval_minutes = restart_intervals.get(pkg, 0)
                
                # Siapkan waktu mulai jika belum dilacak
                if pkg not in last_restart_track:
                    last_restart_track[pkg] = current_time

                # Logika: Jika interval > 0 DAN waktu yang berlalu > interval * 60
                if interval_minutes > 0:
                    elapsed = current_time - last_restart_track[pkg]
                    if elapsed >= (interval_minutes * 60):
                        msg(f"[!!!] RESTART TERJADWAL: {username} ({interval_minutes}m interval)", "warn")
                        kill_roblox_process(pkg)
                        link = links.get(pkg, "")
                        launch_roblox(pkg, link)
                        
                        # Perbarui waktu pelacakan
                        last_restart_track[pkg] = time.time()
                        send_webhook(f"♻️ **Restart Terjadwal** dieksekusi untuk **{username}** setelah {interval_minutes} menit.")
                        
                        # Lewati cek heartbeat pada giliran ini karena baru saja restart
                        time.sleep(5) 
                        continue 

                # --- CEK 2: Heartbeat (Rejoin Normal) ---
                hb_file = os.path.join(reconnect_dir, f"reconnect_status_{username}.json")
                online, age, uname, reason = read_heartbeat(hb_file)
                if online:
                    msg(f"[✓] {username} online (age={age:.0f}s)", "ok")
                else:
                    msg(f"[*] {username} OFFLINE → {reason} → rejoin {pkg}", "err")
                    kill_roblox_process(pkg)
                    link = links.get(pkg, "")
                    launch_roblox(pkg, link)
                    
                    # Reset timer restart pada crash/rejoin sehingga tidak double restart
                    last_restart_track[pkg] = time.time() 
                    send_webhook(f"⚠️ **{username} OFFLINE** ({reason}) → rejoined {pkg}")
                
                time.sleep(5)
            
            msg(f"[i] Tidur 200s sebelum siklus berikutnya...", "info")
            time.sleep(200)
    except KeyboardInterrupt:
        msg("[i] Menghentikan auto rejoin.")

# /2: tambah username secara manual (auto detect package)
def user_id_menu():
    accounts = load_accounts()
    pkgs = get_custom_packages()
    if not pkgs:
        msg("[!] Tidak menemukan paket Roblox mana pun.", "err")
        wait_back_menu()
        return

    if len(pkgs) == 1:
        pkg = pkgs[0]
        print(Fore.LIGHTGREEN_EX + f"Otomatis mendeteksi paket: {pkg}")
    else:
        print("Menemukan beberapa paket Roblox:")
        for i, p in enumerate(pkgs):
            print(f"{i+1}. {p}")
        idx = int(input("Pilih nomor: ")) - 1
        pkg = pkgs[idx]

    username = prompt("Masukkan username:")
    accounts.append((pkg, username))
    save_accounts(accounts)
    msg(f"[i] Sudah menyimpan Username untuk paket {pkg}.", "ok")
    wait_back_menu()


# /3: atur link umum (auto detect packages)
def set_common_link():
    pkgs = get_custom_packages()
    if not pkgs:
        msg("[!] Tidak menemukan paket Roblox mana pun.", "err")
        wait_back_menu()
        return

    link = prompt("Masukkan ID Game/Link server umum:")
    formatted = format_server_link(link)
    if not formatted:
        msg("[!] Link tidak valid.", "err")
        wait_back_menu()
        return

    save_server_links([(pkg, formatted) for pkg in pkgs])
    msg(f"[i] Sudah menyimpan link umum untuk {len(pkgs)} paket.", "ok")
    wait_back_menu()


# /4: tetapkan link pribadi (pilih package dari daftar detect)
def set_package_link():
    pkgs = get_custom_packages()
    if not pkgs:
        msg("[!] Tidak menemukan paket Roblox mana pun.", "err")
        wait_back_menu()
        return

    print("Daftar paket Roblox:")
    for i, p in enumerate(pkgs):
        print(f"{i+1}. {p}")
    idx = int(input("Pilih nomor paket untuk menetapkan link: ")) - 1
    pkg = pkgs[idx]

    link = prompt(f"Masukkan link untuk paket {pkg}:")
    formatted = format_server_link(link)
    if not formatted:
        msg("[!] Link tidak valid.", "err")
        wait_back_menu()
        return

    links = load_server_links()
    links = [(p, l) for p, l in links if p != pkg]  # hapus link lama dari pkg
    links.append((pkg, formatted))
    save_server_links(links)
    msg(f"[i] Sudah menyimpan link pribadi untuk {pkg}.", "ok")
    wait_back_menu()

# /5: hapus
def delete_entry():
    t = prompt("Hapus (1=File User, 2=File Link server, 3=Keduanya):")
    if t == "1":
        if os.path.exists(ACCOUNTS_FILE):
            os.remove(ACCOUNTS_FILE)
            msg("[i] Sudah menghapus seluruh Account.txt.", "ok")
        else:
            msg("[!] Account.txt tidak ada.", "err")
    elif t == "2":
        if os.path.exists(SERVER_LINKS_FILE):
            os.remove(SERVER_LINKS_FILE)
            msg("[i] Sudah menghapus seluruh Private_Link.txt.", "ok")
        else:
            msg("[!] Private_Link.txt tidak ada.", "err")
    elif t == "3":
        if os.path.exists(ACCOUNTS_FILE):
            os.remove(ACCOUNTS_FILE)
            msg("[i] Sudah menghapus seluruh Account.txt.", "ok")
        else:
            msg("[!] Account.txt tidak ada.", "err")
        if os.path.exists(SERVER_LINKS_FILE):
            os.remove(SERVER_LINKS_FILE)
            msg("[i] Sudah menghapus seluruh Private_Link.txt.", "ok")
        else:
            msg("[!] Private_Link.txt tidak ada.", "err")
    else:
        msg("[!] Pilihan tidak valid.", "err")
    wait_back_menu()

# /6: webhook
def set_webhook_menu():
    url = prompt("Masukkan URL webhook:")
    user_id = prompt("Masukkan ID User Discord untuk ping (dapat dibiarkan kosong):")
    set_webhook(url, user_id)
    msg("[i] Sudah menyimpan webhook dan ID user.", "ok")
    wait_back_menu()

# /7: gunakan UID dari appStorage.json → API ambil username
def find_uid_from_appstorage():
    pkgs = get_custom_packages()
    accounts = []
    for pkg in pkgs:
        fpath = f'/data/data/{pkg}/files/appData/LocalStorage/appStorage.json'
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            uid = str(data.get("UserId", ""))
        except:
            uid = ""

        username = ""
        if uid:
            try:
                r = requests.get(f"https://users.roblox.com/v1/users/{uid}", timeout=5)
                if r.status_code == 200:
                    username = r.json().get("name", "")
            except:
                pass

        if username:
            accounts.append((pkg, username))
            msg(f"Menemukan username {username} untuk {pkg}", "ok")
        else:
            msg(f"Tidak menemukan UID/username untuk {pkg}", "err")

    if accounts:
        save_accounts(accounts)
        msg("[i] Sudah menyimpan username dari appStorage.", "ok")
        link = prompt("Masukkan link umum untuk paket:")
        formatted = format_server_link(link)
        if formatted:
            save_server_links([(pkg, formatted) for pkg, _ in accounts])
            msg("[i] Sudah menyimpan link untuk appStorage.", "ok")

    wait_back_menu()

# /8: lihat daftar
def show_saved():
    print("--- Account.txt ---")
    for a in load_accounts():
        print(a)
    print("--- Private_Link.txt ---")
    for l in load_server_links():
        print(l)
    wait_back_menu()

# /9: Optimalkan mesin dan ubah android 
def optimize_android_menu():
    while True:
        print("\n===== OPTIMALKAN MESIN =====")
        print("1. Semua")
        print("2. Nonaktifkan bloatware")
        print("3. Ubah Android ID")
        print("4. Matikan animasi")
        print("5. Kembali")

        choice = input("Pilih opsi (1-5): ").strip()

        if choice == "1":
            if input("Apakah Anda yakin ingin menjalankan SEMUA? (y/n): ").lower() == "y":
                disable_bloatware_apps()
                set_android_id()
                disable_animations()
                print(Fore.LIGHTGREEN_EX + "[✓] Optimalkan Android selesai.")
        elif choice == "2":
            if input("Apakah Anda yakin ingin menonaktifkan bloatware? (y/n): ").lower() == "y":
                disable_bloatware_apps()
        elif choice == "3":
            set_android_id()
        elif choice == "4":
            disable_animations()
        elif choice == "5":
            print("Kembali ke menu utama...")
            wait_back_menu()
            break
        else:
            print(Fore.LIGHTYELLOW_EX + "⚠ Pilihan tidak valid, silakan masukkan 1-5.")

# /10: Tambahkan script ke folder autoexecute
def add_autoexecute_script():
    dirs = find_autoexecute_dirs()
    auto_dir = None

    if not dirs:
        print(Fore.LIGHTRED_EX + "Tidak menemukan direktori Autoexecute. Silakan periksa kembali!")
        return
    elif len(dirs) == 1:
        auto_dir = dirs[0]
    else:
        print("Menemukan beberapa direktori Autoexecute:")
        for i, d in enumerate(dirs):
            print(f"{i+1}. {d}")
        idx = int(input("Pilih nomor: ")) - 1
        auto_dir = dirs[idx]

    print("""
Pilih jenis script:
1. Script Check Online (buat file checkonline.lua)
2. Masukkan script secara manual (autoexecuteN.lua)
    """)
    choice = input("Masukkan pilihan: ").strip()

    if choice == "1":
        filename = os.path.join(auto_dir, "checkonline.txt")
        script_content = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/last-ghost/FPS/refs/heads/dev/checkonline.lua"))()'
    elif choice == "2":
        # Cari nomor berikutnya untuk file autoexecuteN.lua
        existing = [f for f in os.listdir(auto_dir) if f.startswith("autoexecute") and f.endswith(".txt")]
        nums = []
        for f in existing:
            try:
                n = int(f.replace("autoexecute", "").replace(".txt", ""))
                nums.append(n)
            except:
                pass
        next_num = max(nums) + 1 if nums else 1
        filename = os.path.join(auto_dir, f"autoexecute{next_num}.txt")

        print(Fore.LIGHTBLUE_EX + f"Masukkan script Anda (ketik 'end' pada baris terpisah untuk mengakhiri):")
        lines = []
        while True:
            line = input()
            if line.strip().lower() == "end":
                break
            lines.append(line)
        script_content = "\n".join(lines)
    else:
        print(Fore.LIGHTRED_EX + "Pilihan tidak valid.")
        return

    with open(filename, "w", encoding="utf-8") as f:
        f.write(script_content + "\n")

    print(Fore.LIGHTGREEN_EX + f"Sudah menyimpan script ke {filename}")
    wait_back_menu()

# /11: Export, Import Config
def export_import_config():
    print("\n===== EXPORT / IMPORT CONFIG =====")
    print("1. Export config (tulis ke file + kirim ke webhook)")
    print("2. Import config (tempel JSON, masukkan URL, atau Enter untuk baca file lokal)")
    print("3. Kembali")
    choice = input("Pilih: ").strip()

    if choice == "1":
        data = {}

        # ambil config.json
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data["config"] = json.load(f)
            except:
                data["config"] = {}
        else:
            data["config"] = {}

        # ambil Account.txt
        data["accounts"] = load_accounts()

        # ambil Private_Link.txt
        data["links"] = load_server_links()

        # ambil Webhook.txt
        url, uid = get_webhook()
        data["webhook"] = {"url": url, "uid": uid}

        try:
            # Tetap tulis file lokal untuk backup
            json_text = json.dumps(data, ensure_ascii=False)
            with open("localrejoinconfig.json", "w", encoding="utf-8") as f:
                f.write(json_text)
            
            msg("[✓] Sudah export config → localrejoinconfig.json", "ok")

            # Kirim file config ke webhook
            if not url:
                msg("[!] Tidak menemukan URL webhook untuk mengirim. Hanya export ke file.", "err")
            else:
                msg("[i] Sedang mengirim backup config ke webhook...", "info")
                try:
                    # Kirim file json sebagai lampiran
                    files = {
                        'file': ('localrejoinconfig.json', json_text, 'application/json')
                    }
                    payload_json = {
                        "content": f"Backup config dari tool localrejoin. User: <@{uid}>" if uid else "Backup config dari tool localrejoin."
                    }
                    r = requests.post(url, files=files, data={"payload_json": json.dumps(payload_json)}, timeout=10)
                    
                    if 200 <= r.status_code < 300:
                        msg("[✓] Sudah mengirim backup config ke webhook berhasil.", "ok")
                    else:
                        msg(f"[!] Mengirim webhook gagal. Status: {r.status_code}, Response: {r.text}", "err")
                except Exception as e:
                    msg(f"[!] Kesalahan saat mengirim config ke webhook: {e}", "err")

        except Exception as e:
            msg(f"[!] Kesalahan export: {e}", "err")

        wait_back_menu()

    elif choice == "2":
        pasted = prompt("Tempel JSON, masukkan URL, atau Enter untuk baca file localrejoinconfig.json:")
        data = None
        
        try:
            pasted = pasted.strip()
            if not pasted:
                # 1. Tekan Enter -> Baca file lokal
                with open("localrejoinconfig.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                msg("[i] Sudah membaca config dari localrejoinconfig.json", "info")
            
            elif pasted.startswith("http://") or pasted.startswith("https://"):
                # 2. Masukkan URL -> Unduh dari link
                try:
                    msg("[i] Sedang mengunduh config dari URL...", "info")
                    r = requests.get(pasted, timeout=10)
                    r.raise_for_status()  # Lempar kesalahan jika status code bukan 2xx
                    data = r.json()
                    msg("[✓] Unduh dan analisis JSON dari URL berhasil.", "ok")
                except requests.exceptions.RequestException as req_e:
                    msg(f"[!] Kesalahan saat mengunduh URL: {req_e}", "err")
                    wait_back_menu()
                    return
                except json.JSONDecodeError as json_e:
                    msg(f"[!] Konten dari URL bukan JSON valid: {json_e}", "err")
                    wait_back_menu()
                    return
            
            elif pasted.startswith("{") and pasted.endswith("}"):
                # 3. Tempel JSON -> Baca langsung
                data = json.loads(pasted)
                msg("[i] Sudah menganalisis JSON yang ditempel.", "info")
            
            else:
                msg("[!] Input tidak valid. Bukan URL, JSON, atau kosong.", "err")
                wait_back_menu()
                return

        except Exception as e:
            msg(f"[!] Kesalahan menganalisis JSON atau membaca file: {e}", "err")
            wait_back_menu()
            return

        if data is None:
            msg("[!] Tidak dapat memuat data config.", "err")
            wait_back_menu()
            return
            
        try:
            # Tulis config (pertahankan logika lama)
            if "config" in data:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(data["config"], f, indent=2, ensure_ascii=False)

            if "accounts" in data:
                save_accounts(data["accounts"])

            if "links" in data:
                save_server_links(data["links"])

            if "webhook" in data and isinstance(data["webhook"], dict):
                set_webhook(data["webhook"].get("url", ""), data["webhook"].get("uid", ""))

            msg("[✓] Sudah import config berhasil!", "ok")
        except Exception as e:
            msg(f"[!] Kesalahan saat import data: {e}", "err")

        wait_back_menu()

    elif choice == "3":
        return
    else:
        msg("[!] Pilihan tidak valid.", "err")

# /12: Matikan nyalakan startup otomatis tool
def manage_startup():
    # gunakan path absolut karena saat berjalan di bawah su maka ~ akan menjadi /root
    startup_dir = "/data/data/com.termux/files/home/.termux/boot"
    startup_file = os.path.join(startup_dir, "startup.sh")

    print("\n===== STARTUP OTOMATIS =====")
    print("1. Nyalakan auto start saat boot mesin")
    print("2. Matikan auto start")
    print("3. Kembali")
    choice = input("Pilih: ").strip()

    if choice == "1":
        try:
            os.makedirs(startup_dir, exist_ok=True)
            script_content = """#!/data/data/com.termux/files/usr/bin/bash
# tunggu 20s agar sistem boot selesai
sleep 20

# jalankan local_rejoin.py dengan hak root
su -c "export PATH=$PATH:/data/data/com.termux/files/usr/bin && \\
       export TERM=xterm-256color && \\
       cd /sdcard/Download && \\
       python local_rejoin.py --auto" >> ~/local_rejoin.log 2>&1
"""
            with open(startup_file, "w", encoding="utf-8") as f:
                f.write(script_content)

            os.chmod(startup_file, 0o755)
            print(Fore.LIGHTGREEN_EX + f"[✓] Sudah menyalakan auto start. File: {startup_file}")
        except Exception as e:
            print(Fore.LIGHTRED_EX + f"[!] Kesalahan saat menyalakan startup: {e}")
        wait_back_menu()

    elif choice == "2":
        try:
            if os.path.exists(startup_file):
                os.remove(startup_file)
                print(Fore.LIGHTGREEN_EX + "[✓] Sudah mematikan auto start.")
            else:
                print(Fore.LIGHTYELLOW_EX + "[i] Startup belum dinyalakan atau file tidak ada.")
        except Exception as e:
            print(Fore.LIGHTRED_EX + f"[!] Kesalahan saat mematikan startup: {e}")
        wait_back_menu()

    elif choice == "3":
        return
    else:
        msg("[!] Pilihan tidak valid.", "err")

# /13: Atur Periodic Restart (Auto Reset)
def restart_interval_menu():
    cfg = load_config()
    current_intervals = cfg.get("restart_intervals", {})

    print("\n===== PERIODIC RESTART (AUTO RESET) =====")
    print("Fitur: Otomatis matikan dan buka ulang game setelah interval waktu tertentu (terlepas dari online atau offline).")
    print("Masukkan 0 untuk mematikan fitur ini.")
    print("-----------------------------------------")
    print("1. Atur waktu untuk SEMUA paket")
    print("2. Atur waktu untuk SETIAP paket secara individual")
    print("3. Kembali")
    
    choice = input("Pilih: ").strip()

    if choice == "1":
        try:
            minutes = int(input("Masukkan jumlah menit (Contoh: 30, 60, 0 untuk mematikan): "))
        except ValueError:
            msg("[!] Silakan masukkan angka bulat.", "err")
            wait_back_menu()
            return

        pkgs = get_custom_packages()
        if not pkgs:
            msg("[!] Tidak menemukan paket apa pun.", "err")
            return

        # Perbarui untuk semua paket yang ditemukan
        for pkg in pkgs:
            current_intervals[pkg] = minutes
        
        cfg["restart_intervals"] = current_intervals
        save_config(cfg)
        msg(f"[✓] Sudah mengatur waktu restart {minutes} menit untuk {len(pkgs)} paket.", "ok")
        wait_back_menu()

    elif choice == "2":
        pkgs = get_custom_packages()
        if not pkgs:
            msg("[!] Tidak menemukan paket apa pun.", "err")
            wait_back_menu()
            return

        print("\nDaftar paket:")
        for i, p in enumerate(pkgs):
            # Tampilkan waktu saat ini jika ada
            curr_val = current_intervals.get(p, 0)
            print(f"{i+1}. {p} (Saat ini: {curr_val} menit)")
        
        try:
            idx = int(input("Pilih nomor urut paket: ")) - 1
            if 0 <= idx < len(pkgs):
                target_pkg = pkgs[idx]
                minutes = int(input(f"Masukkan jumlah menit restart untuk {target_pkg} (0 untuk mematikan): "))
                
                current_intervals[target_pkg] = minutes
                cfg["restart_intervals"] = current_intervals
                save_config(cfg)
                msg(f"[✓] Sudah memperbarui {target_pkg} -> {minutes} menit.", "ok")
            else:
                msg("[!] Nomor urut tidak valid.", "err")
        except ValueError:
            msg("[!] Silakan masukkan angka.", "err")
        wait_back_menu()

    elif choice == "3":
        return
    else:
        msg("[!] Pilihan tidak valid.", "err")

# ============ Menu ============
def menu():
    while True:
        clear()
        print("""
======== MENU ========
1 Auto rejoin
2 User ID
3 Atur umum 1 ID Game/Link server
4 Tetapkan ID Game/Link pribadi untuk setiap paket
5 Hapus User ID atau Link server
6 Atur webhook Discord
7 Otomatis cari User ID dari appStorage.json
8 Lihat daftar yang disimpan
9 Optimalkan mesin, ubah AndroidID, Matikan Animasi
10 Tambahkan script ke Auto Execute
11 Export, Import Config
12 Kelola Startup Otomatis
13 Atur Auto Restart (Interval Reset)
14 Keluar tool
======================
""")
        choice = input("Pilih: ").strip()
        if choice == "1":
            auto_rejoin()
        elif choice == "2":
            user_id_menu()
        elif choice == "3":
            set_common_link()
        elif choice == "4":
            set_package_link()
        elif choice == "5":
            delete_entry()
        elif choice == "6":
            set_webhook_menu()
        elif choice == "7":
            find_uid_from_appstorage()
        elif choice == "8":
            show_saved()
        elif choice == "9":
            optimize_android_menu()
        elif choice == "10":
            add_autoexecute_script()
        elif choice == "11":
            export_import_config()
        elif choice == "12":
            manage_startup()
        elif choice == "13":
            restart_interval_menu()
        elif choice == "14":
            break
        else:
            msg("[!] Pilihan tidak valid.", "err")

# ============ Entry ============
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        auto_rejoin()
    else:
        menu()
