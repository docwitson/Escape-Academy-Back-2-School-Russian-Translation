"""Academy-styled installer: one screen, no console, background file operations."""
import os
import queue
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from engine import apply, inspect, load_manifest

BG, PAPER, STUB = '#1a303b', '#f3ead5', '#eadfc5'
INK, MUTED, ACCENT, LINE = '#24363d', '#68716e', '#89394d', '#ccbea1'
REPOSITORY_URL = 'https://github.com/docwitson/Escape-Academy-Back-2-School-Russian-Translation'


def discover():
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
            roots.append(Path(winreg.QueryValueEx(key, 'SteamPath')[0]))
    except OSError: pass
    for drive in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
        for name in ['Steam', 'SteamLibrary', 'Games/Steam', 'Program Files (x86)/Steam']:
            p = Path(drive + ':/') / name
            if (p / 'steamapps').is_dir(): roots.append(p)
    for root in list(roots):
        libraries = root / 'steamapps/libraryfolders.vdf'
        if libraries.exists():
            roots.extend(Path(p.replace('\\\\', '\\')) for p in re.findall(r'"path"\s+"([^"]+)"', libraries.read_text(errors='replace')))
    for root in roots:
        path = root / 'steamapps/common/EscapeAcademy2Back2School'
        if (path / 'EscapeAcademy2Back2School.exe').exists(): return str(path)
    return ''


class App:
    def __init__(self):
        self.root = tk.Tk(); self.root.title('Escape Academy 2 • Русификатор')
        self.root.geometry('1000x680'); self.root.resizable(False, False); self.root.configure(bg=BG)
        icon = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'academy.ico'
        if icon.exists(): self.root.iconbitmap(str(icon))
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.payload = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'payload'
        self.package = load_manifest(self.payload) if (self.payload / 'package.json').exists() else dict(version='0.2.0', game_build='26497480')
        self.busy = False; self.events = queue.Queue()
        sheet = tk.Canvas(self.root, width=1000, height=680, bg=BG, highlightthickness=0)
        sheet.pack(fill='both', expand=True); self.sheet = sheet
        sheet.create_rectangle(20, 20, 980, 660, fill=PAPER, outline='')
        sheet.create_rectangle(20, 20, 322, 660, fill=STUB, outline='')
        sheet.create_rectangle(34, 34, 966, 646, outline=LINE)
        sheet.create_line(322, 46, 322, 634, fill='#a79b82', dash=(3, 6))
        for y in (20, 660):
            sheet.create_oval(307, y-15, 337, y+15, fill=BG, outline=BG)
        sheet.create_text(171, 75, text='ESCAPE', fill=INK, font=('Georgia', 28, 'bold'))
        sheet.create_text(171, 122, text='ACADEMY', fill=INK, font=('Georgia', 28, 'bold'))
        sheet.create_text(171, 171, text='BACK 2 SCHOOL', fill=ACCENT, font=('Segoe UI', 12, 'bold'))
        art = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'assets/ticket-art.png'
        if art.exists():
            self.art = tk.PhotoImage(file=str(art))
            sheet.create_image(171, 348, image=self.art)
        sheet.create_line(70, 558, 272, 558, fill=LINE)
        sheet.create_text(171, 590, text='Версия ' + self.package['version'].split('-')[0], fill=INK, font=('Segoe UI', 12, 'bold'))
        sheet.create_text(171, 619, text='Текст и субтитры', fill=MUTED, font=('Segoe UI', 11))
        sheet.create_text(650, 70, text='БИЛЕТ НА ПОЕЗД', fill=ACCENT, font=('Segoe UI', 11, 'bold'))
        sheet.create_text(650, 114, text='RU — ЭСКЕЙП АКАДЕМИЯ', fill=INK, font=('Segoe UI', 20, 'bold'))
        sheet.create_text(650, 158, text='ПЕРЕВОД НА РУССКИЙ', fill=MUTED, font=('Segoe UI', 10, 'bold'))
        sheet.create_rectangle(354, 197, 946, 292, fill='#e6dcc5', outline='')
        sheet.create_rectangle(354, 197, 358, 292, fill=ACCENT, outline='')
        sheet.create_text(376, 219, anchor='w', text='ТОЛЬКО STEAM-СБОРКА ' + self.package['game_build'], fill=ACCENT, font=('Segoe UI', 12, 'bold'))
        sheet.create_text(376, 249, anchor='w', text='Закрой игру перед установкой.', fill=INK, font=('Segoe UI', 12))
        sheet.create_text(376, 274, anchor='w', text='После установки выбери English в игре.', fill=INK, font=('Segoe UI', 12))
        sheet.create_text(354, 332, anchor='w', text='ПАПКА С ИГРОЙ', fill=MUTED, font=('Segoe UI', 10, 'bold'))
        self.path = tk.StringVar(value=discover())
        self.entry = tk.Entry(sheet, textvariable=self.path, bg='#fbf6e9', fg=INK, insertbackground=INK, relief='flat', font=('Segoe UI', 10), highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT)
        sheet.create_window(354, 356, anchor='nw', window=self.entry, width=478, height=46)
        self.browse = self.button(sheet, 'Обзор…', self.choose, '#e6dcc5', INK)
        sheet.create_window(844, 356, anchor='nw', window=self.browse, width=102, height=46)
        self.message = tk.StringVar(value='Папка найдена. Всё готово к установке.' if self.path.get() else 'Выбери папку установленной игры.')
        status = tk.Label(sheet, textvariable=self.message, bg=PAPER, fg=MUTED, font=('Segoe UI', 11), wraplength=590, justify='left', anchor='w')
        sheet.create_window(354, 423, anchor='nw', window=status, width=592, height=50)
        style = ttk.Style(); style.theme_use('clam')
        style.configure('Academy.Horizontal.TProgressbar', troughcolor='#e6dcc5', background=ACCENT, borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)
        self.progress = ttk.Progressbar(sheet, style='Academy.Horizontal.TProgressbar', maximum=100)
        self.progress_item = sheet.create_window(354, 548, anchor='nw', window=self.progress, width=592, height=5, state='hidden')
        self.install = self.button(sheet, 'Установить перевод', lambda: self.start('install'), ACCENT, '#fff8ea')
        sheet.create_window(354, 486, anchor='nw', window=self.install, width=354, height=48)
        self.remove = self.button(sheet, 'Удалить перевод', lambda: self.start('remove'), '#e6dcc5', INK)
        sheet.create_window(722, 486, anchor='nw', window=self.remove, width=224, height=48)
        sheet.create_text(650, 590, text='Сохранения и настройки не изменяются.', fill=MUTED, font=('Segoe UI', 10))
        notice = tk.Label(sheet, text='Лицензии компонентов', bg=PAPER, fg=MUTED, font=('Segoe UI', 9), cursor='hand2')
        sheet.create_window(650, 637, window=notice)
        notice.bind('<Button-1>', lambda event: self.show_notices())
        github = tk.Label(sheet, text='GitHub · Сообщить об ошибке', bg=PAPER, fg=ACCENT, font=('Segoe UI', 10), cursor='hand2')
        sheet.create_window(650, 611, window=github)
        github.bind('<Button-1>', lambda event: self.open_repository())
        self.root.after(100, self.poll)

    def button(self, parent, text, command, bg, fg):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground='#d9c6a5', activeforeground=INK,
                         relief='flat', borderwidth=0, padx=16, pady=12, font=('Segoe UI', 11, 'bold'), cursor='hand2')
    def choose(self):
        selected = filedialog.askdirectory(title='Выбери папку EscapeAcademy2Back2School', initialdir=self.path.get() or None)
        if selected: self.path.set(selected)
    def open_repository(self):
        import webbrowser
        webbrowser.open(REPOSITORY_URL)
    def show_notices(self):
        from tkinter.scrolledtext import ScrolledText
        window = tk.Toplevel(self.root); window.title('Лицензии компонентов'); window.geometry('760x500')
        text = ScrolledText(window, wrap='word'); text.pack(fill='both', expand=True)
        text.insert('1.0', (self.payload / 'THIRD_PARTY_NOTICES.txt').read_text(encoding='utf-8')); text.configure(state='disabled')
    def start(self, action):
        if self.busy: return
        self.busy = True; self.progress['value'] = 0
        self.sheet.itemconfigure(self.progress_item, state='normal')
        for widget in [self.install, self.remove, self.browse, self.entry]: widget.configure(state='disabled')
        self.message.set('Проверяем игру…')
        path = self.path.get()
        def work():
            try:
                apply(path, self.payload, action, lambda n, t: self.events.put(('progress', n, t)))
                self.events.put(('done', 100, 'Готово! Выбери English в игре.' if action == 'install' else 'Готово. Английский оригинал восстановлен.'))
            except PermissionError:
                self.events.put(('error', 0, 'Нет доступа к папке. Закрой игру и попробуй запустить установщик от имени администратора.'))
            except Exception as exc: self.events.put(('error', 0, str(exc)))
        threading.Thread(target=work, daemon=True).start()
    def poll(self):
        try:
            while True:
                kind, value, text = self.events.get_nowait(); self.message.set(text); self.progress['value'] = value
                if kind != 'progress':
                    self.busy = False
                    for widget in [self.install, self.remove, self.browse, self.entry]: widget.configure(state='normal')
        except queue.Empty: pass
        self.root.after(100, self.poll)
    def close(self):
        if not self.busy: self.root.destroy()


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        import json
        game = Path(sys.argv[sys.argv.index('--self-test') + 1]).resolve()
        output = Path(sys.argv[sys.argv.index('--result') + 1])
        try:
            if not (game / '.installer-test').is_file(): raise ValueError('Self-test requires isolated fixture marker')
            payload = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'payload'
            if not (payload.parent / 'assets/ticket-art.png').is_file(): raise ValueError('Ticket illustration missing from package')
            states = [apply(game, payload, action, check_process=False) for action in ['install', 'install', 'remove']]
            if states != ['russian', 'russian', 'original']: raise ValueError(str(states))
            output.write_text(json.dumps(dict(ok=True, states=states)), encoding='utf-8')
        except Exception as exc:
            output.write_text(json.dumps(dict(ok=False, error=str(exc))), encoding='utf-8')
            raise
    else:
        App().root.mainloop()
