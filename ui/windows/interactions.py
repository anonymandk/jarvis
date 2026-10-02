"""Mainwindowinteraction main-window behavior."""

from __future__ import annotations

import importlib

_runtime = importlib.import_module("ui._runtime")
globals().update({key: value for key, value in vars(_runtime).items() if not key.startswith("__")})

class _MainWindowInteractionMixin:
    def _show_left_panel_popup(self):
        """Show left panel content as a popup."""
        # Gather information from left panel components
        info_lines = ["RESUMO DO SISTEMA"]

        # Add system metrics if available
        if hasattr(self, '_bar_cpu'):
            cpu_val = getattr(self._bar_cpu, 'value', 0)
            info_lines.append(f"Uso de CPU: {cpu_val:.0f}%")
        if hasattr(self, '_bar_mem'):
            mem_val = getattr(self._bar_mem, 'value', 0)
            info_lines.append(f"Uso de memória: {mem_val:.0f}%")
        if hasattr(self, '_bar_net'):
            net_val = getattr(self._bar_net, 'value', 0)
            info_lines.append(f"Rede: {net_val:.0f}%")
        if hasattr(self, '_bar_gpu'):
            gpu_val = getattr(self._bar_gpu, 'value', 0)
            info_lines.append(f"GPU: {gpu_val:.0f}%")

        # Add agent info if available
        if hasattr(self, '_agent_grid'):
            # AgentGridWidget has a fixed number of agents
            agent_count = len(self._agent_grid._AGENTS)
            info_lines.append(f"Agentes ativos: {agent_count}")

        info_lines.append("")
        info_lines.append("Pressione L para atualizar este resumo")

        # Join lines and show as popup
        message = "\n".join(info_lines)
        self._popup_manager.show_popup(
            message,
            PopupType.INFORMATION
        )

    def _show_right_panel_popup(self):
        """Show right panel content as a popup."""
        # Gather information from right panel components
        info_lines = ["PAINEL DE EXECUÇÃO"]

        # Add mission info
        info_lines.append("Painel de execução")

        # Add chat status
        if hasattr(self, '_mission'):
            if hasattr(self._mission, 'log_widget'):
                info_lines.append("Conversa: ativa")
            else:
                info_lines.append("Conversa: inativa")

            # Add current tab info
            if hasattr(self._mission, '_stack'):
                current_index = self._mission._stack.currentIndex()
                tab_names = ["Logs", "Tarefas", "Arquivos", "Ferramentas"]
                if 0 <= current_index < len(tab_names):
                    current_tab = tab_names[current_index]
                    info_lines.append(f"Aba atual: {current_tab}")

        info_lines.append("")
        info_lines.append("Pressione R para atualizar este resumo")

        # Join lines and show as popup
        message = "\n".join(info_lines)
        self._popup_manager.show_popup(
            message,
            PopupType.INFORMATION
        )

    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size)
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell JARVIS what to do with it")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._style_mute_btn()
        if hasattr(self, "_compact_widget") and self._compact_widget is not None:
            self._compact_widget.set_muted(self._muted)
        if self._muted:
            self._apply_state("MUTED")
            self._log.append_log("SYS: Microphone muted.")
        else:
            self._apply_state("LISTENING")
            self._log.append_log("SYS: Microphone active.")

    def _get_selected_voice(self) -> str:
        idx = self._voice_combo.currentIndex()
        voice_name = self._voice_combo.itemData(idx)
        if isinstance(voice_name, str) and voice_name:
            return voice_name
        label = self._voice_combo.currentText().strip().lower()
        return VOICE_LABEL_TO_VALUE.get(label, "charon")

    def _on_voice_changed(self, _voice_label: str):
        """Handle voice selection change"""
        voice_name = self._get_selected_voice()
        self._log.append_log(f"SYS: Voice changed to {voice_name}.")
        os.environ["GEMINI_VOICE_NAME"] = voice_name
        try:
            cfg = json.loads(API_FILE.read_text(encoding="utf-8")) if API_FILE.exists() else {}
        except Exception:
            cfg = {}
        cfg.pop("gemini_api_key", None)
        cfg["voice_name"] = voice_name
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            API_FILE.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        except Exception as e:
            self._log.append_log(f"SYS: Could not save voice selection: {e}")
        if self.on_voice_change:
            try:
                self.on_voice_change(voice_name)
            except Exception as e:
                self._log.append_log(f"SYS: Voice callback error: {e}")

    def _style_mute_btn(self):
        if self._muted:
            self._mute_btn.setText("Microfone silenciado")
            self._mute_btn.setAccessibleName("Microfone silenciado")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.RED_BG};
                    color: {C.MUTED_C};
                    border: 1px solid {C.RED};
                    border-radius: {TOKENS.radii['legacy_5']}px;
                    padding: {TOKENS.spacing['legacy_0']}px {TOKENS.spacing['legacy_12']}px;
                }}
                QPushButton:hover {{
                    background: {C.DARK2};
                    border: 1px solid {C.MUTED_C};
                }}
            """)
        else:
            self._mute_btn.setText("Microfone ativo")
            self._mute_btn.setAccessibleName("Microfone ativo")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.GREEN_BG};
                    color: {C.GREEN};
                    border: 1px solid {C.GREEN_D};
                    border-radius: {TOKENS.radii['legacy_5']}px;
                    padding: {TOKENS.spacing['legacy_0']}px {TOKENS.spacing['legacy_12']}px;
                }}
                QPushButton:hover {{
                    background: {C.DARK2};
                    border: 1px solid {C.GREEN};
                }}
            """)

    def _send(self, txt: str = ""):
        """Handle command submission. Called via ChatBubbleWidget signal."""
        try:
            txt = str(txt or "").strip()
            if not txt:
                return
            if (not getattr(self, "_ready", True)
                    or getattr(self, "_interaction_gated", False)
                    or getattr(self, "_intro_in_progress", False)
                    or getattr(self, "_intro_voice_preparing", False)):
                return
            self._log.append_log(f"You: {txt}")
            normalized = re.sub(r"[^a-z ]+", " ", txt.lower())
            normalized = " ".join(normalized.split())
            if normalized in {
                "open command center", "open the command center", "show command center",
                "show the command center", "open command ceneter", "open the command ceneter",
            }:
                self._set_command_center(True)
                self._log.append_log("JARVIS: Command Center is open.")
                return
            if normalized in {
                "close command center", "close the command center", "hide command center",
                "hide the command center", "return to focus view",
            }:
                self._set_command_center(False)
                self._log.append_log("JARVIS: Returning to focus view.")
                return
            if self.on_text_command:
                def _dispatch():
                    try:
                        self.on_text_command(txt)
                    except Exception as exc:
                        self._log_sig.emit(f"ERR: Message processing failed: {exc}")
                threading.Thread(target=_dispatch, daemon=True).start()
        except Exception as exc:
            # Exceptions escaping a PyQt signal handler can abort the process.
            # Keep JARVIS alive and surface the problem in its own log instead.
            try:
                self._log.append_log(f"ERR: Message processing failed: {exc}")
            except Exception:
                print(f"[JARVIS] Message processing failed: {exc}")

    def _apply_state(self, state: str):
        state_key = str(state or "idle").strip().lower()
        if state_key == "thinking":
            state_key = "processing"
        if self._muted and state_key in {"idle", "listening"}:
            state_key = "muted"
        state_values = {
            "idle": ("Em espera", "◇", C.TEXT_MED),
            "listening": ("Ouvindo", "◖", C.GREEN),
            "processing": ("Processando", "◈", C.PURPLE),
            "speaking": ("Falando", "◉", C.PRI),
            "reconnecting": ("Reconectando", "↻", C.AMBER),
            "error": ("Erro", "!", C.RED),
            "muted": ("Microfone silenciado", "⌁", C.TEXT_DIM),
        }
        label, icon, state_color = state_values.get(state_key, state_values["idle"])
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")
        if hasattr(self, "_error_guidance"):
            self._error_guidance.setVisible(state_key == "error")
        if hasattr(self, "_orb"):
            self._orb.set_state(state_key)
        if hasattr(self, "_activity_visualizer"):
            self._activity_visualizer.set_state(state_key)
        if hasattr(self, "_core_state"):
            self._core_state.setText(f"{icon}  {label}")
            self._core_state.setStyleSheet(f"color: {state_color}; background: transparent;")
            self._core_state.setAccessibleDescription(f"Estado atual: {label}")
        if hasattr(self, "_rail_mode_lbl"):
            self._rail_mode_lbl.setText(label)
            rail_color = state_color
            self._rail_mode_lbl.setStyleSheet(
                f"color: {rail_color}; background: transparent;"
            )
            if hasattr(self, "_rail_status_dot"):
                self._rail_status_dot.setStyleSheet(
                    f"color: {rail_color}; background: transparent;"
                )
        if hasattr(self, "_header_mode_lbl"):
            self._header_mode_lbl.setText("Gemini Live · conexão —")
            self._header_mode_lbl.setStyleSheet(
                f"color: {C.TEXT_MED}; background: transparent;"
            )
        if hasattr(self, "_header_state_lbl"):
            self._header_state_lbl.setText(f"{icon}  {label}")
            self._header_state_lbl.setStyleSheet(f"color: {state_color}; background: transparent;")
            self._header_state_lbl.setAccessibleDescription(f"Estado atual: {label}")
        # Sync AI canvas state
        if hasattr(self, "_ai_canvas"):
            self._ai_canvas.state = state
            # Map state to canvas mode if no specific context is set
            if state == "SPEAKING":
                self._ai_canvas.set_mode("speaking")
            elif state == "THINKING":
                self._ai_canvas.set_mode(getattr(self, "_context_mode", "thinking"))
            elif state == "LISTENING":
                self._ai_canvas.set_mode("listening")

        # Sync compact mode widget state
        if self._compact_widget:
            self._compact_widget.set_state(state)
            self._compact_widget.set_muted(self._muted)

    def _parse_log_for_context(self, text: str):
        """Detect context from log messages and feed task/tool widgets."""
        tl = text.lower()

        # Context mode detection
        if any(k in tl for k in ("code_helper", "dev_agent", "coding", "python", "javascript")):
            mode = "coding"
        elif any(k in tl for k in ("file_processor", "screen_process", "analyzing", "document")):
            mode = "analyzing"
        elif any(k in tl for k in ("web_search", "flight_finder", "weather", "research")):
            mode = "researching"
        elif "thinking" in tl or "🔧" in text:
            mode = "thinking"
        else:
            mode = getattr(self, "_context_mode", "idle")

        if mode != getattr(self, "_context_mode", "idle"):
            self._context_mode = mode
            try:
                self._mode_sig.emit(mode)
            except Exception:
                pass

        # Task queue feeding
        TOOL_MAP = {
            "open_app": "Open Application",
            "web_search": "Web Search",
            "deep_research": "Deep Research",
            "weather_report": "Weather Report",
            "browser_control": "Browser Control",
            "file_controller": "File Controller",
            "send_message": "Send Message",
            "reminder": "Set Reminder",
            "youtube_video": "YouTube",
            "screen_process": "Vision Analysis",
            "computer_settings": "System Settings",
            "desktop_control": "Desktop Control",
            "email_control": "Email",
            "media_control": "Media Control",
            "code_helper": "Code Assistant",
            "dev_agent": "Dev Agent",
            "web_search": "Web Search",
            "file_processor": "File Processor",
            "computer_control": "Computer Control",
            "game_updater": "Game Updater",
            "flight_finder": "Flight Finder",
        }
        for key, label in TOOL_MAP.items():
            if key in tl:
                if "📞" in text or "🔧" in text:
                    status = "calling"
                    # Show tool progress indicator
                    if hasattr(self, "_tool_progress"):
                        self._tool_progress.show_tool(label)
                elif "→" in text or "done" in tl or "✓" in text:
                    status = "done"
                    # Hide tool progress indicator
                    if hasattr(self, "_tool_progress"):
                        self._tool_progress.hide_tool()
                elif "❌" in text or "error" in tl or "fail" in tl:
                    status = "error"
                    if hasattr(self, "_tool_progress"):
                        self._tool_progress.hide_tool()
                    self._show_toast(f"Tool error: {label}", "error")
                else:
                    status = "active"
                try:
                    self._task_sig.emit(label, status)
                except Exception:
                    pass
                break

        # Tool log feeding — forward SYS/tool lines to tool widget
        if "🔧" in text or "📞" in text or "→" in text:
            try:
                self._tool_sig.emit(text)
            except Exception:
                pass
