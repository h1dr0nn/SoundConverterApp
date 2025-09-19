"""Widget implementing the application preferences tab."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QVBoxLayout, QWidget


class SettingsTab(QWidget):
    """Widget that exposes preference controls backed by :class:`QSettings`."""

    defaultFormatChanged = Signal(str)
    overwriteExistingChanged = Signal(bool)
    openDestinationChanged = Signal(bool)
    rememberDestinationChanged = Signal(bool)
    rememberGeometryChanged = Signal(bool)
    autoClearSelectionChanged = Signal(bool)

    def __init__(
        self,
        settings: QSettings,
        available_formats: Sequence[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._available_formats = list(available_formats)

        self._default_format = "ogg"
        self._overwrite_existing = True
        self._open_destination = False
        self._remember_destination = True
        self._remember_geometry = True
        self._auto_clear_selection = False

        self._build_ui()
        self._load_preferences()
        self._apply_preferences()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def default_format(self) -> str:
        return self._default_format

    @property
    def overwrite_existing(self) -> bool:
        return self._overwrite_existing

    @property
    def open_destination(self) -> bool:
        return self._open_destination

    @property
    def remember_destination(self) -> bool:
        return self._remember_destination

    @property
    def remember_geometry(self) -> bool:
        return self._remember_geometry

    @property
    def auto_clear_selection(self) -> bool:
        return self._auto_clear_selection

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_available_formats(self, formats: Sequence[str]) -> None:
        self._available_formats = list(formats)
        self._apply_default_format_to_combo()

    def set_default_format(self, value: str) -> None:
        self._default_format = self._select_valid_format(value)
        self._apply_default_format_to_combo()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(18)

        default_format_label = QLabel("Default output format")
        default_format_label.setObjectName("settingsLabel")
        layout.addWidget(default_format_label)

        self.default_format_combo = QComboBox()
        self.default_format_combo.setObjectName("settingsCombo")
        self.default_format_combo.currentTextChanged.connect(
            self._handle_default_format_changed
        )
        layout.addWidget(self.default_format_combo)

        self.overwrite_checkbox = QCheckBox("Overwrite existing files")
        self.overwrite_checkbox.setObjectName("settingsCheckBox")
        self.overwrite_checkbox.toggled.connect(self._handle_overwrite_toggled)
        layout.addWidget(self.overwrite_checkbox)

        self.open_destination_checkbox = QCheckBox(
            "Open the destination folder when conversion completes"
        )
        self.open_destination_checkbox.setObjectName("settingsCheckBox")
        self.open_destination_checkbox.toggled.connect(
            self._handle_open_destination_toggled
        )
        layout.addWidget(self.open_destination_checkbox)

        self.remember_destination_checkbox = QCheckBox(
            "Remember the last destination folder"
        )
        self.remember_destination_checkbox.setObjectName("settingsCheckBox")
        self.remember_destination_checkbox.toggled.connect(
            self._handle_remember_destination_toggled
        )
        layout.addWidget(self.remember_destination_checkbox)

        self.remember_geometry_checkbox = QCheckBox(
            "Remember window size and position"
        )
        self.remember_geometry_checkbox.setObjectName("settingsCheckBox")
        self.remember_geometry_checkbox.toggled.connect(
            self._handle_remember_geometry_toggled
        )
        layout.addWidget(self.remember_geometry_checkbox)

        self.auto_clear_checkbox = QCheckBox(
            "Clear file selection after a successful conversion"
        )
        self.auto_clear_checkbox.setObjectName("settingsCheckBox")
        self.auto_clear_checkbox.toggled.connect(self._handle_auto_clear_toggled)
        layout.addWidget(self.auto_clear_checkbox)

        layout.addStretch()

    def _load_preferences(self) -> None:
        self._default_format = str(self._settings.value("default_format", "ogg"))
        self._overwrite_existing = self._get_bool_setting("overwrite_existing", True)
        self._open_destination = self._get_bool_setting("open_destination", False)
        self._remember_destination = self._get_bool_setting("remember_destination", True)
        self._remember_geometry = self._get_bool_setting("remember_window_geometry", True)
        self._auto_clear_selection = self._get_bool_setting("auto_clear_selection", False)

    def _apply_preferences(self) -> None:
        self._apply_default_format_to_combo()
        self._apply_checkbox_state(self.overwrite_checkbox, self._overwrite_existing)
        self._apply_checkbox_state(self.open_destination_checkbox, self._open_destination)
        self._apply_checkbox_state(
            self.remember_destination_checkbox, self._remember_destination
        )
        self._apply_checkbox_state(
            self.remember_geometry_checkbox, self._remember_geometry
        )
        self._apply_checkbox_state(self.auto_clear_checkbox, self._auto_clear_selection)

    def _apply_default_format_to_combo(self) -> None:
        block = self.default_format_combo.blockSignals(True)
        self.default_format_combo.clear()
        self.default_format_combo.addItems(self._available_formats)
        if self._available_formats:
            target = self._select_valid_format(self._default_format)
            self._default_format = target
            index = self.default_format_combo.findText(target)
            if index < 0:
                index = 0
            self.default_format_combo.setCurrentIndex(index)
        self.default_format_combo.blockSignals(block)

    def _apply_checkbox_state(self, checkbox: QCheckBox, value: bool) -> None:
        block = checkbox.blockSignals(True)
        checkbox.setChecked(value)
        checkbox.blockSignals(block)

    def _select_valid_format(self, value: str) -> str:
        if value in self._available_formats:
            return value
        if self._available_formats:
            return self._available_formats[0]
        return value

    def _get_bool_setting(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).lower() in {"1", "true", "yes", "on"}

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------
    def _handle_default_format_changed(self, value: str) -> None:
        if not value:
            return
        self._default_format = value
        self._settings.setValue("default_format", value)
        self.defaultFormatChanged.emit(value)

    def _handle_overwrite_toggled(self, checked: bool) -> None:
        self._overwrite_existing = checked
        self._settings.setValue("overwrite_existing", checked)
        self.overwriteExistingChanged.emit(checked)

    def _handle_open_destination_toggled(self, checked: bool) -> None:
        self._open_destination = checked
        self._settings.setValue("open_destination", checked)
        self.openDestinationChanged.emit(checked)

    def _handle_remember_destination_toggled(self, checked: bool) -> None:
        self._remember_destination = checked
        self._settings.setValue("remember_destination", checked)
        if not checked:
            self._settings.remove("last_output_directory")
        self.rememberDestinationChanged.emit(checked)

    def _handle_remember_geometry_toggled(self, checked: bool) -> None:
        self._remember_geometry = checked
        self._settings.setValue("remember_window_geometry", checked)
        if not checked:
            self._settings.remove("window_geometry")
        self.rememberGeometryChanged.emit(checked)

    def _handle_auto_clear_toggled(self, checked: bool) -> None:
        self._auto_clear_selection = checked
        self._settings.setValue("auto_clear_selection", checked)
        self.autoClearSelectionChanged.emit(checked)
