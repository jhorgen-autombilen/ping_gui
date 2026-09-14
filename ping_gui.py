"""Simple domain ping GUI."""

import platform
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk


class PingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ping")
        self.geometry("640x420")
        self.minsize(480, 320)

        self._queue: queue.Queue[str] = queue.Queue()
        self._ping_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self._build_ui()
        self.after(80, self._drain_queue)

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 8}

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="Domain:").pack(side="left")

        self.domain_var = tk.StringVar(value="google.com")
        self.entry = ttk.Entry(top, textvariable=self.domain_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.entry.bind("<Return>", lambda _event: self.start_ping())
        self.entry.focus()

        self.ping_button = ttk.Button(top, text="Ping", command=self.start_ping)
        self.ping_button.pack(side="left")

        self.stop_button = ttk.Button(top, text="Stop", command=self.stop_ping, state="disabled")
        self.stop_button.pack(side="left", padx=(6, 0))

        self.output = tk.Text(self, wrap="word", font=("Consolas", 10), state="disabled")
        scrollbar = ttk.Scrollbar(self, command=self.output.yview)
        self.output.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.output.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def start_ping(self) -> None:
        host = self.domain_var.get().strip()
        if not host:
            messagebox.showwarning("Ping", "Enter a domain or IP address.")
            return
        if self._ping_thread and self._ping_thread.is_alive():
            return

        self._stop_event.clear()
        self._set_running(True)
        self._clear_output()
        self._append(f"Pinging {host}...\n\n")

        self._ping_thread = threading.Thread(target=self._run_ping, args=(host,), daemon=True)
        self._ping_thread.start()

    def stop_ping(self) -> None:
        self._stop_event.set()

    def _run_ping(self, host: str) -> None:
        count_flag = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", count_flag, "4", host]

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower() == "windows" else 0,
            )
        except FileNotFoundError:
            self._queue.put("Could not find the ping command on this system.\n")
            self._queue.put("__DONE__")
            return
        except OSError as exc:
            self._queue.put(f"Failed to start ping: {exc}\n")
            self._queue.put("__DONE__")
            return

        assert process.stdout is not None
        try:
            for line in process.stdout:
                if self._stop_event.is_set():
                    process.terminate()
                    self._queue.put("\nStopped.\n")
                    break
                self._queue.put(line)
            process.wait(timeout=5)
        except Exception as exc:
            self._queue.put(f"\nError: {exc}\n")
        finally:
            if process.poll() is None:
                process.kill()
            self._queue.put("__DONE__")

    def _drain_queue(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item == "__DONE__":
                self._set_running(False)
            else:
                self._append(item)
        self.after(80, self._drain_queue)

    def _set_running(self, running: bool) -> None:
        self.ping_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.entry.configure(state="disabled" if running else "normal")

    def _clear_output(self) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _append(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")


if __name__ == "__main__":
    app = PingApp()
    app.mainloop()
