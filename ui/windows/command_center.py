"""Mainwindowcommand main-window behavior."""

from __future__ import annotations

import importlib

_legacy = importlib.import_module("ui._legacy")
globals().update({key: value for key, value in vars(_legacy).items() if not key.startswith("__")})

class _MainWindowCommandMixin:
    def _handle_ui_command(self, action: str):
        action = str(action or "").strip().lower()
        if action in {"quit jarvis", "quit_jarvis"}:
            self._request_quit()
            return True
        if action == "open_command_center":
            self._set_command_center(True)
            return True
        if action == "close_command_center":
            self._set_command_center(False)
            return True
        handlers = {
            "open_settings": self._show_settings,
            "compact_mode": self._toggle_compact_mode,
            "fullscreen": self._toggle_fullscreen,
            "show_shortcuts": self._toggle_shortcuts_overlay,
        }
        handler = handlers.get(action)
        if handler:
            handler()
            return True
        return False

    def _set_command_center(self, is_open: bool, announce: bool = True):
        """Switch between the focused conversation and full control surface."""
        was_open = bool(getattr(self, "_command_center_open", False))
        self._command_center_open = bool(is_open)
        self._command_transition_id = getattr(self, "_command_transition_id", 0) + 1
        transition_id = self._command_transition_id
        if hasattr(self, "_mission"):
            self._mission.set_command_center_open(is_open)
        if hasattr(self, "_right_panel"):
            self._right_panel.setFixedWidth(_RIGHT_W)
            self._right_panel.setVisible(is_open)
        if hasattr(self, "_focus_dialogue"):
            self._focus_dialogue.setVisible(not is_open)
        if hasattr(self, "_splitter"):
            if is_open:
                self._splitter.setSizes([_LEFT_W, max(420, self.width() - _LEFT_W - _RIGHT_W), _RIGHT_W])
            else:
                self._splitter.setSizes([0, max(720, self.width()), 0])

        reveal_widgets = [
            getattr(self, "_header", None),
            getattr(self, "_left_panel", None),
            getattr(self, "_right_panel", None),
            getattr(self, "_command_bar", None),
        ]
        if is_open:
            for widget in reveal_widgets:
                if widget is not None:
                    widget.show()
            if not was_open:
                for delay, widget in zip((0, 90, 180, 270), reveal_widgets):
                    if widget is not None:
                        self._reveal_widget(widget, delay, transition_id)
        else:
            for widget in reveal_widgets:
                if widget is not None:
                    widget.hide()
            if hasattr(self, "_focus_dialogue") and was_open:
                self._reveal_widget(self._focus_dialogue, 80, transition_id)

        if hasattr(self, "_tool_progress"):
            if is_open and self._tool_progress._tmr.isActive():
                self._tool_progress.show()
            elif not is_open:
                self._tool_progress.hide()
        if announce and hasattr(self, "_popup_manager"):
            self._show_toast(
                "Command Center open" if is_open else "Focus view restored",
                "info",
            )
        if announce and is_open and not was_open:
            self._announce_command_center_modules()

    def _reveal_widget(self, widget: QWidget, delay_ms: int = 0, transition_id: int | None = None):
        """Reveal a module with a short, stagger-friendly opacity transition."""
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(230)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        self._command_reveal_animations = getattr(self, "_command_reveal_animations", [])
        self._command_reveal_animations.append(animation)

        def _finish():
            if widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)
            try:
                self._command_reveal_animations.remove(animation)
            except ValueError:
                pass

        animation.finished.connect(_finish)

        def _start():
            if (
                transition_id is not None
                and transition_id != getattr(self, "_command_transition_id", transition_id)
            ):
                _finish()
                return
            animation.start()

        QTimer.singleShot(max(0, int(delay_ms)), _start)

    def _announce_command_center_modules(self):
        announcement = (
            "Command Center online. Status header ready. System overview ready. "
            "Mission control ready. Command rail ready."
        )
        if self.on_text_command:
            prompt = (
                "[UI EVENT] The Command Center modules are appearing now. "
                f'Say exactly: "{announcement}"'
            )
            threading.Thread(target=self.on_text_command, args=(prompt,), daemon=True).start()
        else:
            self._log.append_log(f"JARVIS: {announcement}")

    def _toggle_left_panel(self):
        sizes = self._splitter.sizes()
        if sizes[0] > 10:
            self._left_target_w = sizes[0]
            self._splitter.setSizes([0, sizes[1] + sizes[0], sizes[2]])
        else:
            self._splitter.setSizes([self._left_target_w, sizes[1] - self._left_target_w, sizes[2]])

    def _toggle_right_panel(self):
        sizes = self._splitter.sizes()
        if sizes[2] > 10:
            self._right_target_w = sizes[2]
            self._splitter.setSizes([sizes[0], sizes[1] + sizes[2], 0])
        else:
            self._splitter.setSizes([sizes[0], sizes[1] - self._right_target_w, self._right_target_w])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._toggle_left_panel()
        elif event.key() == Qt.Key.Key_Right and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._toggle_right_panel()
        else:
            super().keyPressEvent(event)

    def _dismiss_overlays(self):
        for ov in (self._shortcuts_overlay, self._settings_overlay):
            if ov and ov.isVisible():
                ov.hide()
                return

    def _show_toast(self, message: str, toast_type: str = "info"):
        try:
            ToastManager.show_toast(self.centralWidget(), message, toast_type)
        except Exception:
            pass

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cw = self.centralWidget()
        if getattr(self, "_startup_backdrop", None) is not None:
            self._startup_backdrop.setGeometry(cw.rect())
        if self._overlay and self._overlay.isVisible():
            self._overlay._center_in_parent()
        if getattr(self, "_intro_overlay", None) is not None:
            self._intro_overlay.setGeometry(cw.rect())
        if self._name_overlay and self._name_overlay.isVisible():
            ow, oh = 420, 310
            self._name_overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
        if hasattr(self, "_voice_overlay") and self._voice_overlay and self._voice_overlay.isVisible():
            ow, oh = 420, 380
            self._voice_overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )

    def _update_metrics(self):
        snap = _get_metrics()
        if hasattr(snap, "snapshot"):
            snap = snap.snapshot()
        if not isinstance(snap, dict):
            snap = {}

        # CPU
        cpu = float(snap.get("cpu", -1.0))
        if cpu <= 0:
            try:
                import psutil as _psu
                cpu = _psu.cpu_percent(interval=None)
            except Exception:
                cpu = 0.0
        self._bar_cpu.set_value(cpu, "{:.0f}%".format(cpu))
        if hasattr(self, '_spark_cpu'):
            self._spark_cpu.set_value("{:.0f}".format(cpu), cpu / 100.0, "%")

        # MEM
        mem = float(snap.get("mem", -1.0))
        if mem <= 0:
            try:
                import psutil as _psu
                mem = _psu.virtual_memory().percent
            except Exception:
                mem = 0.0
        self._bar_mem.set_value(mem, "{:.0f}%".format(mem))
        if hasattr(self, '_spark_mem'):
            self._spark_mem.set_value("{:.0f}".format(mem), mem / 100.0, "%")

        # NET
        net = float(snap.get("net", -1.0))
        if net < 0:
            net_str = "N/A"
            net_pct = 0
            self._bar_net.set_value(net_pct, net_str)
            if hasattr(self, '_spark_net'):
                self._spark_net.set_value(net_str, 0.0, "")
        elif net < 1.0:
            net_str = f"{net*1024:.0f}KB/s"
            net_pct = min(100, net * 10)
            self._bar_net.set_value(net_pct, net_str)
            if hasattr(self, '_spark_net'):
                self._spark_net.set_value(net_str, net_pct / 100.0, "")
        else:
            net_str = f"{net:.1f}MB/s"
            net_pct = min(100, net * 10)
            self._bar_net.set_value(net_pct, net_str)
            if hasattr(self, '_spark_net'):
                self._spark_net.set_value(net_str, net_pct / 100.0, "")

        # GPU — cache chip/VRAM from system_profiler, simulate load
        if not getattr(self, '_gpu_info_cached', False):
            try:
                import subprocess as _sp, re as _re2
                _r = _sp.run(["system_profiler", "SPDisplaysDataType"],
                             capture_output=True, text=True, timeout=3)
                _cm = _re2.search(r"Chipset Model:\s*(.+)", _r.stdout)
                _vm = _re2.search(r"VRAM.*?:\s*([\d.]+ \w+)", _r.stdout)
                self._gpu_chip = _cm.group(1).strip() if _cm else "Integrated GPU"
                self._gpu_chip = self._gpu_chip.replace(" Graphics", "").replace("Intel ", "")
                self._gpu_vram_str = _vm.group(1) if _vm else "Shared"
                self._gpu_info_cached = True
            except Exception:
                self._gpu_chip = "Integrated GPU"
                self._gpu_vram_str = "Shared"
                self._gpu_info_cached = True
        if hasattr(self, '_gpu_name_lbl'):
            self._gpu_name_lbl.setText(getattr(self, '_gpu_chip', 'Integrated GPU'))
        if hasattr(self, '_gpu_vram_lbl'):
            self._gpu_vram_lbl.setText(getattr(self, '_gpu_vram_str', 'Shared'))
        gpu = float(snap.get("gpu", -1.0))
        if hasattr(self, '_gpu_pct_lbl'):
            self._gpu_pct_lbl.setText("{:.0f}%".format(gpu) if gpu >= 0 else "N/A")
        if hasattr(self, '_gpu_load_bar'):
            self._gpu_load_bar.setValue(int(gpu) if gpu >= 0 else 0)
        self._bar_gpu.set_value(max(0.0, gpu), "{:.0f}%".format(gpu) if gpu >= 0 else "N/A")

        # Temperature is shown only when the operating system exposes a real sensor.
        tmp = snap["tmp"]
        if tmp < 0:
            self._bar_tmp.set_value(0, "N/A")
            if hasattr(self, '_spark_tmp'):
                self._spark_tmp.set_value("N/A", 0.0, "")
        else:
            tmp_pct = min(100, tmp)
            self._bar_tmp.set_value(tmp_pct, "{:.0f}°C".format(tmp))
            if hasattr(self, '_spark_tmp'):
                self._spark_tmp.set_value("{:.0f}".format(tmp), tmp / 100.0, "°C")

        try:
            boot_t  = psutil.boot_time()
            elapsed = time.time() - boot_t
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
        except Exception:
            self._uptime_lbl.setText("UP  --:--")

        try:
            proc_count = len(psutil.pids())
            self._proc_lbl.setText(f"PROC  {proc_count}")
        except Exception:
            self._proc_lbl.setText("PROC  --")

        # Session timer
        try:
            if hasattr(self, "_session_start"):
                se = time.time() - self._session_start
                sh = int(se // 3600)
                sm = int((se % 3600) // 60)
                ss = int(se % 60)
                if hasattr(self, "_session_lbl"):
                    self._session_lbl.setText(f"SESSION  {sh:02d}:{sm:02d}:{ss:02d}")
        except Exception:
            pass

        # AI Cognition bar — driven by state
        try:
            if hasattr(self, "_bar_cog") and hasattr(self, "hud"):
                state = getattr(self.hud, "state", "LISTENING")
                cog_pct = {
                    "THINKING": random.uniform(70, 95),
                    "PROCESSING": random.uniform(55, 80),
                    "SPEAKING": random.uniform(30, 50),
                    "LISTENING": random.uniform(5, 20),
                }.get(state, random.uniform(2, 10))
                self._bar_cog.set_value(cog_pct, f"{cog_pct:.0f}%")
        except Exception:
            pass
