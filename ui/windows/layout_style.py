"""Mainwindowstyle main-window behavior."""

from __future__ import annotations

import importlib

_legacy = importlib.import_module("ui._legacy")
globals().update({key: value for key, value in vars(_legacy).items() if not key.startswith("__")})

class _MainWindowStyleMixin:
    def _style_splitter(self):
        if not hasattr(self, "_splitter"):
            return
        self._splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {C.BORDER};
                width: 4px;
            }}
            QSplitter::handle:hover {{ background: {C.BORDER_B}; }}
        """)

    def _style_header(self):
        if not hasattr(self, "_header") and not hasattr(self, "_utility_btn"):
            return
        header = getattr(self, "_header", None)
        if header is not None:
            header.setStyleSheet(f"""
                QWidget#appHeader {{
                    background: {C.DARK};
                    border-bottom: 1px solid {C.BORDER};
                }}
            """)
        if hasattr(self, "_utility_btn"):
            self._utility_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C.PANEL2}; color: {C.TEXT_MED};
                    border: 1px solid {C.BORDER}; border-radius: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ color: {C.WHITE}; border-color: {C.BORDER_B}; }}
                QPushButton::menu-indicator {{ image: none; }}
            """)
        if hasattr(self, "_utility_menu"):
            self._utility_menu.setStyleSheet(f"""
                QMenu {{
                    background: {C.PANEL}; color: {C.WHITE};
                    border: 1px solid {C.BORDER}; padding: 6px;
                }}
                QMenu::item {{ padding: 7px 24px 7px 10px; border-radius: 4px; }}
                QMenu::item:selected {{ background: {C.PRI_GHO}; color: {C.PRI}; }}
                QMenu::separator {{ height: 1px; background: {C.BORDER}; margin: 5px; }}
            """)
        label_styles = (
            ("_header_brand_lbl", C.WHITE),
            ("_header_mark_lbl", C.TEXT_MED),
            ("_header_state_lbl", C.GREEN),
            ("_header_mode_lbl", C.TEXT_MED),
            ("_clock_lbl", C.WHITE),
            ("_date_lbl", C.TEXT_DIM),
            ("_utc_lbl", C.TEXT_DIM),
        )
        for attr, color in label_styles:
            label = getattr(self, attr, None)
            if label is not None:
                label.setStyleSheet(f"color: {color}; background: transparent;")

    def _style_left_nav(self):
        for attr, color in (
            ("_rail_title_lbl", C.WHITE),
            ("_system_title_lbl", C.TEXT_MED),
            ("_hardware_title_lbl", C.TEXT_DIM),
            ("_gpu_name_lbl", C.TEXT_MED),
            ("_gpu_vram_lbl", C.TEXT_MED),
            ("_uptime_lbl", C.TEXT_DIM),
            ("_session_lbl", C.TEXT_DIM),
            ("_proc_lbl", C.TEXT_MED),
        ):
            label = getattr(self, attr, None)
            if label is not None:
                label.setStyleSheet(f"color: {color}; background: transparent;")
        for button in (getattr(self, "_left_system_btn", None), getattr(self, "_left_agents_btn", None)):
            if button is None:
                continue
            if button.isChecked():
                button.setStyleSheet(f"""
                    QPushButton {{
                        background: {C.PRI_GHO}; color: {C.PRI};
                        border: 1px solid {C.PRI_DIM}; border-radius: 5px;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; color: {C.TEXT_MED};
                        border: 1px solid {C.BORDER}; border-radius: 5px;
                    }}
                    QPushButton:hover {{ color: {C.WHITE}; border-color: {C.BORDER_B}; }}
                """)

    def _style_command_button(self, button: QPushButton, color: str, hover: str):
        button.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {color};
                border: 1px solid transparent; border-radius: 5px;
                padding: 0 11px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; color: {hover}; border-color: {C.BORDER_B};
            }}
            QPushButton:focus {{
                background: {C.PRI_GHO}; color: {hover};
                border: 1px solid {hover};
            }}
            QPushButton:pressed {{ background: {C.DARK2}; color: {C.WHITE}; }}
            QPushButton:disabled {{ color: {C.TEXT_DIM}; background: transparent; }}
        """)

    def _style_command_rail(self):
        rail = getattr(self, "_dock_frame", None)
        if rail is not None:
            rail.setStyleSheet(f"""
                QWidget#JarvisCommandRail {{
                    background: {C.BAR_BG};
                    border-top: 1px solid {C.BORDER_B};
                    border-bottom: 1px solid {C.BORDER};
                }}
                QFrame#CommandControlTrack {{
                    background: {C.PANEL2};
                    border: 1px solid {C.BORDER};
                    border-radius: 6px;
                }}
                QFrame#CommandRailDivider {{
                    color: {C.BORDER};
                    background: {C.BORDER};
                    border: none;
                }}
            """)
        if hasattr(self, "_rail_divider"):
            self._rail_divider.setStyleSheet(f"color: {C.BORDER_B};")
        if hasattr(self, "_command_title_lbl"):
            self._command_title_lbl.setStyleSheet(
                f"color: {C.WHITE}; background: transparent; letter-spacing: 1px;"
            )
        if hasattr(self, "_rail_mode_lbl"):
            self._rail_mode_lbl.setStyleSheet(
                f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;"
            )
        if hasattr(self, "_rail_status_dot"):
            self._rail_status_dot.setStyleSheet(f"color: {C.PRI}; background: transparent;")

    def _style_maker_signature(self):
        strip = getattr(self, "_maker_signature", None)
        if strip is not None:
            strip.setStyleSheet(f"""
                QWidget#JarvisMakerSignature {{
                    background: {C.BG};
                    border: none;
                }}
            """)
        label = getattr(self, "_maker_signature_lbl", None)
        if label is not None:
            label.setStyleSheet(
                f"color: {C.TEXT_DIM}; background: transparent; letter-spacing: 1px;"
            )

    def _style_command_controls(self):
        self._style_command_rail()
        if hasattr(self, "_tts_btn"):
            self._style_command_button(self._tts_btn, C.TEXT_MED, C.PRI)
        if hasattr(self, "_name_btn"):
            self._style_command_button(self._name_btn, C.TEXT_MED, C.PRI)
        if hasattr(self, "_theme_btn"):
            self._style_command_button(self._theme_btn, C.TEXT_MED, C.PRI)
        if hasattr(self, "_quit_btn"):
            self._quit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C.RED};
                    border: 1px solid {C.RED_D}; border-radius: 5px;
                    padding: 0 13px;
                }}
                QPushButton:hover, QPushButton:focus {{
                    background: {C.RED_BG}; color: {C.MUTED_C}; border-color: {C.RED};
                }}
                QPushButton:pressed {{ background: {C.DARK2}; }}
            """)
        if hasattr(self, "_mute_btn"):
            self._style_mute_btn()

    def _update_theme_btn(self):
        if hasattr(self, "_theme_btn"):
            display = ThemeManager.theme_display_name(ThemeManager.current_name())
            self._theme_btn.setText(f"THEME  ·  {display}")
