import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QObject, QPoint, QRectF, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


APP_VERSION = "0.01"
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DEFAULT_BACKGROUND = QColor("#dbeafe")


@dataclass(frozen=True)
class RatioPreset:
    name: str
    value: float
    description: str


STANDARD_RATIOS = [
    RatioPreset("1:1", 1, "正方形 / 头像 / 主图"),
    RatioPreset("4:5", 4 / 5, "社媒常见竖图"),
    RatioPreset("5:4", 5 / 4, "横版海报 / 平板"),
    RatioPreset("3:4", 3 / 4, "常见竖版 / 手机拍摄"),
    RatioPreset("4:3", 4 / 3, "传统横屏 / 平板"),
    RatioPreset("2:3", 2 / 3, "竖版摄影 / 电商图"),
    RatioPreset("3:2", 3 / 2, "相机横版 / 摄影原图"),
    RatioPreset("16:10", 16 / 10, "显示器 / 笔记本"),
    RatioPreset("16:9", 16 / 9, "宽屏 / 视频封面"),
    RatioPreset("9:16", 9 / 16, "竖屏短视频 / 手机海报"),
    RatioPreset("10:16", 10 / 16, "长竖图 / 海报"),
    RatioPreset("18:9", 18 / 9, "全面屏常见比例"),
    RatioPreset("19.5:9", 19.5 / 9, "手机全面屏"),
    RatioPreset("20:9", 20 / 9, "长屏手机"),
    RatioPreset("21:9", 21 / 9, "超宽屏 / 电影比例"),
    RatioPreset("2:1", 2, "宽幅横图"),
    RatioPreset("1:2", 0.5, "超长竖图"),
]


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event) -> None:
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


def format_value(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def find_closest_ratio(factor: float) -> str:
    closest_name = "未找到常见比例"
    min_diff = 0.015
    for preset in STANDARD_RATIOS:
        diff = abs(factor - preset.value)
        if diff < min_diff:
            min_diff = diff
            closest_name = preset.name
    return closest_name


def normalize_color_code(text: str) -> QColor:
    value = text.strip()
    if not value:
        raise ValueError("请输入颜色代码。")
    color = QColor(value)
    if not color.isValid() and not value.startswith("#"):
        color = QColor(f"#{value}")
    if not color.isValid():
        raise ValueError("颜色代码无效，请输入如 #ffffff。")
    return color


def parse_ratio_text(text: str) -> float:
    ratio_text = text.strip()
    if not ratio_text:
        raise ValueError("请输入自定义比例。")
    delimiter = ":" if ":" in ratio_text else "/" if "/" in ratio_text else ""
    if delimiter:
        left, right = ratio_text.split(delimiter, 1)
        width = float(left.strip())
        height = float(right.strip())
        if width <= 0 or height <= 0:
            raise ValueError("比例必须大于 0。")
        return width / height
    ratio = float(ratio_text)
    if ratio <= 0:
        raise ValueError("比例必须大于 0。")
    return ratio


def load_qimage(path: str) -> QImage:
    image = QImage(path)
    if image.isNull():
        raise ValueError("无法读取图片，请确认文件格式是否受支持。")
    return image.convertToFormat(QImage.Format.Format_ARGB32)


def scaled_canvas_size(size: QSize, max_side: int) -> QSize:
    if max_side <= 0 or size.width() <= max_side and size.height() <= max_side:
        return size
    if size.width() >= size.height():
        return QSize(max_side, max(1, round(size.height() * max_side / size.width())))
    return QSize(max(1, round(size.width() * max_side / size.height())), max_side)


def fitted_image_size(image_size: QSize, canvas_size: QSize) -> QSize:
    if image_size.isEmpty() or canvas_size.isEmpty():
        return QSize()
    scale = min(canvas_size.width() / image_size.width(), canvas_size.height() / image_size.height())
    return QSize(max(1, round(image_size.width() * scale)), max(1, round(image_size.height() * scale)))


def qimage_to_pil(image: QImage) -> Image.Image:
    source = image.convertToFormat(QImage.Format.Format_RGBA8888)
    data = source.bits().tobytes()
    pil_image = Image.frombuffer(
        "RGBA",
        (source.width(), source.height()),
        data,
        "raw",
        "RGBA",
        source.bytesPerLine(),
        1,
    )
    return pil_image.copy()


def resize_qimage_lanczos(image: QImage, size: QSize) -> QImage:
    if image.size() == size:
        return image
    resized = qimage_to_pil(image).resize((size.width(), size.height()), Image.Resampling.LANCZOS)
    raw = resized.tobytes("raw", "RGBA")
    result = QImage(raw, size.width(), size.height(), QImage.Format.Format_RGBA8888)
    return result.copy().convertToFormat(QImage.Format.Format_ARGB32)


def render_to_canvas(image: QImage, canvas_size: QSize, background: QColor | None = None) -> QImage:
    if image.size() == canvas_size:
        return image
    canvas = QImage(canvas_size, QImage.Format.Format_ARGB32)
    canvas.fill(background if background is not None else Qt.GlobalColor.transparent)
    if image.isNull() or canvas_size.isEmpty():
        return canvas
    scaled_size = fitted_image_size(image.size(), canvas_size)
    scaled = resize_qimage_lanczos(image, scaled_size)
    x = (canvas_size.width() - scaled.width()) // 2
    y = (canvas_size.height() - scaled.height()) // 2
    painter = QPainter(canvas)
    painter.drawImage(x, y, scaled)
    painter.end()
    return canvas


def auto_merge_orientation(image_a: QImage, image_b: QImage) -> str:
    aspect_a = image_a.width() / max(1, image_a.height())
    aspect_b = image_b.width() / max(1, image_b.height())
    return "horizontal" if (aspect_a + aspect_b) / 2 < 1 else "vertical"


def merged_image(image_a: QImage, image_b: QImage, orientation: str) -> QImage:
    if orientation == "auto":
        orientation = auto_merge_orientation(image_a, image_b)
    fill = QColor("#ffffff")
    if orientation == "horizontal":
        width = image_a.width() + image_b.width()
        height = max(image_a.height(), image_b.height())
        result = QImage(QSize(width, height), QImage.Format.Format_ARGB32)
        result.fill(fill)
        painter = QPainter(result)
        painter.drawImage(0, (height - image_a.height()) // 2, image_a)
        painter.drawImage(image_a.width(), (height - image_b.height()) // 2, image_b)
        painter.end()
        return result
    width = max(image_a.width(), image_b.width())
    height = image_a.height() + image_b.height()
    result = QImage(QSize(width, height), QImage.Format.Format_ARGB32)
    result.fill(fill)
    painter = QPainter(result)
    painter.drawImage((width - image_a.width()) // 2, 0, image_a)
    painter.drawImage((width - image_b.width()) // 2, image_a.height(), image_b)
    painter.end()
    return result


def save_image_balanced(image: QImage, file_path: str) -> bool:
    suffix = Path(file_path).suffix.lower()
    try:
        pil_image = qimage_to_pil(image)
        if suffix == ".png":
            pil_image.convert("RGB").save(file_path, format="PNG", compress_level=4, optimize=False)
            return True
        if suffix in {".jpg", ".jpeg"}:
            pil_image.convert("RGB").save(file_path, format="JPEG", quality=95, subsampling=0)
            return True
        if suffix == ".bmp":
            pil_image.convert("RGB").save(file_path, format="BMP")
            return True
    except Exception:
        return False
    return image.save(file_path)


class ExportSignals(QObject):
    finished = Signal(str)
    failed = Signal(str)


class ExportMergeTask(QRunnable):
    def __init__(self, image_a: QImage, image_b: QImage, orientation: str, file_path: str) -> None:
        super().__init__()
        self.image_a = QImage(image_a)
        self.image_b = QImage(image_b)
        self.orientation = orientation
        self.file_path = file_path
        self.signals = ExportSignals()

    def run(self) -> None:
        try:
            result = merged_image(self.image_a, self.image_b, self.orientation)
            if not save_image_balanced(result, self.file_path):
                raise RuntimeError("图片没有保存成功，请换一个位置或文件名。")
        except Exception as exc:
            self.signals.failed.emit(str(exc))
            return
        self.signals.finished.emit(self.file_path)


def difference_image(image_a: QImage, image_b: QImage) -> QImage:
    canvas_size = scaled_canvas_size(image_a.size(), 1600)
    a_canvas = render_to_canvas(image_a, canvas_size, QColor("#000000")).convertToFormat(QImage.Format.Format_RGB32)
    b_canvas = render_to_canvas(image_b, canvas_size, QColor("#000000")).convertToFormat(QImage.Format.Format_RGB32)
    result = QImage(canvas_size, QImage.Format.Format_ARGB32)
    result.fill(QColor("#101820"))
    for y in range(canvas_size.height()):
        for x in range(canvas_size.width()):
            ca = a_canvas.pixelColor(x, y)
            cb = b_canvas.pixelColor(x, y)
            diff = max(abs(ca.red() - cb.red()), abs(ca.green() - cb.green()), abs(ca.blue() - cb.blue()))
            if diff < 10:
                gray = 32 + diff
                result.setPixelColor(x, y, QColor(gray, gray, gray))
            else:
                result.setPixelColor(x, y, QColor(255, min(255, diff * 2), 40))
    return result


class RatioCalculatorWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.is_updating = False
        self.last_source = "width"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)
        calculator_box = QGroupBox("")
        calculator_layout = QGridLayout(calculator_box)
        calculator_layout.setContentsMargins(18, 18, 18, 18)
        calculator_layout.setHorizontalSpacing(12)
        calculator_layout.setVerticalSpacing(12)
        self.ratio_combo = NoWheelComboBox()
        self.ratio_combo.addItem("自定义")
        self.ratio_combo.setCurrentText("自定义")
        self.custom_ratio_input = QLineEdit()
        self.custom_ratio_input.setPlaceholderText("例如 16:9、16/9、1.777")
        self.width_input = QLineEdit()
        self.height_input = QLineEdit()
        self.width_input.setPlaceholderText("输入宽度")
        self.height_input.setPlaceholderText("输入高度")
        self.exact_label = QLabel("-")
        self.closest_label = QLabel("-")
        hint = QLabel("自定义比例为空时，可自由输入宽高并实时计算比例；选择或输入比例后，宽高会按最后编辑项联动。")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        calculator_layout.addWidget(QLabel("比例选择"), 0, 0)
        calculator_layout.addWidget(self.ratio_combo, 0, 1)
        calculator_layout.addWidget(QLabel("自定义比例"), 1, 0)
        calculator_layout.addWidget(self.custom_ratio_input, 1, 1)
        calculator_layout.addWidget(QLabel("宽度 (px)"), 2, 0)
        calculator_layout.addWidget(self.width_input, 2, 1)
        calculator_layout.addWidget(QLabel("高度 (px)"), 3, 0)
        calculator_layout.addWidget(self.height_input, 3, 1)
        calculator_layout.addWidget(QLabel("精确比例 (宽:高)"), 4, 0)
        calculator_layout.addWidget(self.exact_label, 4, 1)
        calculator_layout.addWidget(QLabel("最接近比例"), 5, 0)
        calculator_layout.addWidget(self.closest_label, 5, 1)
        calculator_layout.addWidget(hint, 6, 0, 1, 2)
        self.ratio_table = QTableWidget(len(STANDARD_RATIOS), 3)
        self.ratio_table.setHorizontalHeaderLabels(["比例", "数值", "用途"])
        self.ratio_table.verticalHeader().setVisible(False)
        self.ratio_table.setAlternatingRowColors(True)
        self.ratio_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ratio_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ratio_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.ratio_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ratio_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.ratio_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.ratio_table.horizontalHeader().setStretchLastSection(True)
        for row, preset in enumerate(STANDARD_RATIOS):
            self.ratio_table.setItem(row, 0, QTableWidgetItem(preset.name))
            self.ratio_table.setItem(row, 1, QTableWidgetItem(f"{preset.value:.2f}"))
            self.ratio_table.setItem(row, 2, QTableWidgetItem(preset.description))
        layout.addWidget(calculator_box, 0)
        layout.addWidget(self.ratio_table, 1)
        self.ratio_combo.currentIndexChanged.connect(self._on_ratio_changed)
        self.ratio_table.itemClicked.connect(self._on_ratio_table_clicked)
        self.custom_ratio_input.textEdited.connect(self._on_ratio_changed)
        self.width_input.textEdited.connect(lambda: self._on_dimension_changed("width"))
        self.height_input.textEdited.connect(lambda: self._on_dimension_changed("height"))

    def _selected_ratio_or_none(self) -> float | None:
        selected = self.ratio_combo.currentText()
        if selected == "自定义":
            text = self.custom_ratio_input.text().strip()
            if not text:
                return None
            return parse_ratio_text(text)
        for preset in STANDARD_RATIOS:
            if preset.name == selected:
                return preset.value
        return None

    def _on_ratio_changed(self) -> None:
        if self.ratio_combo.currentText() == "自定义":
            self.ratio_combo.blockSignals(True)
            try:
                while self.ratio_combo.count() > 1:
                    self.ratio_combo.removeItem(1)
            finally:
                self.ratio_combo.blockSignals(False)
            self.custom_ratio_input.setEnabled(True)
        else:
            self.custom_ratio_input.setEnabled(False)
        self._on_dimension_changed(self.last_source, show_errors=False)

    def _on_ratio_table_clicked(self, item: QTableWidgetItem) -> None:
        ratio_item = self.ratio_table.item(item.row(), 0)
        if ratio_item:
            self.ratio_table.selectRow(item.row())
            self._set_preset_combo_value(ratio_item.text())

    def _set_preset_combo_value(self, preset_name: str) -> None:
        self.ratio_combo.blockSignals(True)
        try:
            while self.ratio_combo.count() > 1:
                self.ratio_combo.removeItem(1)
            self.ratio_combo.addItem(preset_name)
            self.ratio_combo.setCurrentText(preset_name)
            self.custom_ratio_input.setEnabled(False)
        finally:
            self.ratio_combo.blockSignals(False)
        self._on_dimension_changed(self.last_source, show_errors=False)

    def _on_dimension_changed(self, source: str, show_errors: bool = True) -> None:
        if self.is_updating:
            return
        self.last_source = source
        try:
            ratio = self._selected_ratio_or_none()
            width_text = self.width_input.text().strip()
            height_text = self.height_input.text().strip()
            self.is_updating = True
            try:
                width = float(width_text) if width_text else None
                height = float(height_text) if height_text else None
                if width is not None and width <= 0:
                    raise ValueError("宽度必须大于 0。")
                if height is not None and height <= 0:
                    raise ValueError("高度必须大于 0。")

                if ratio is not None:
                    if source == "width" and width is not None:
                        height = width / ratio
                        self.height_input.setText(format_value(height))
                    elif source == "height" and height is not None:
                        width = height * ratio
                        self.width_input.setText(format_value(width))

                self._refresh_result(width, height)
            finally:
                self.is_updating = False
        except ValueError as exc:
            if show_errors:
                QMessageBox.warning(self, "输入有误", str(exc))

    def _refresh_result(self, width: float | None, height: float | None) -> None:
        if width is None or height is None or height == 0:
            self.exact_label.setText("-")
            self.closest_label.setText("-")
            return
        self._set_result(width / height)

    def _set_result(self, factor: float) -> None:
        self.exact_label.setText(f"{factor:.3f}")
        self.closest_label.setText(find_closest_ratio(factor))


class ImageDropSlot(QFrame):
    image_selected = Signal(str)

    def __init__(self, title: str) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropSlot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("dropTitle")
        self.file_label = QLabel("点击选择，或拖拽图片到这里")
        self.file_label.setObjectName("dropHint")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.file_label)

    def set_image_info(self, path: str, image: QImage) -> None:
        self.file_label.setText(f"{Path(path).name}\n{image.width()} x {image.height()}")
        self.setProperty("loaded", True)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
            if file_path:
                self.image_selected.emit(file_path)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event) -> None:
        if any(Path(url.toLocalFile()).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                self.image_selected.emit(path)
                event.acceptProposedAction()
                return


class ImageCompareCanvas(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_a: QImage | None = None
        self.image_b: QImage | None = None
        self.mode = "slide"
        self.merge_orientation = "auto"
        self.zoom = 1.0
        self.pan = QPoint(0, 0)
        self.drag_start: QPoint | None = None
        self.pan_start = QPoint(0, 0)
        self.slide_ratio = 0.5
        self.click_show_b = False
        self.diff_cache: QImage | None = None
        self.diff_cache_key: tuple[int, int] | None = None
        self.scene_cache: dict[tuple, QImage] = {}
        self.display_cache: dict[tuple, QImage] = {}
        self.last_draw_rect = QRectF()
        self.show_diff_overlay = False
        self.background_color = QColor(DEFAULT_BACKGROUND)
        self.preview_max_side = 0

    def set_images(self, image_a: QImage | None, image_b: QImage | None) -> None:
        self.image_a = image_a
        self.image_b = image_b
        self.diff_cache = None
        self.diff_cache_key = None
        self.scene_cache.clear()
        self.display_cache.clear()
        self.reset_view()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._refresh_cursor()
        self.update()

    def set_slide_percent(self, value: int) -> None:
        new_value = min(1.0, max(0.0, value / 100))
        if abs(new_value - self.slide_ratio) >= 0.001:
            self.slide_ratio = new_value
            self.update()

    def set_show_diff_overlay(self, enabled: bool) -> None:
        self.show_diff_overlay = enabled
        self.update()

    def set_background_color(self, color: QColor) -> None:
        if color.isValid():
            self.background_color = QColor(color)
            self.scene_cache.clear()
            self.display_cache.clear()
            self.update()

    def set_preview_max_side(self, max_side: int) -> None:
        self.preview_max_side = max(0, int(max_side))
        self.scene_cache.clear()
        self.display_cache.clear()
        self.update()

    def set_merge_orientation(self, orientation: str) -> None:
        self.merge_orientation = orientation
        self.display_cache.clear()
        self.update()

    def reset_view(self) -> None:
        self.zoom = 1.0
        self.pan = QPoint(0, 0)
        self.display_cache.clear()
        self.update()

    def current_scene_image(self) -> QImage | None:
        if not self.image_a or not self.image_b:
            return self.image_a or self.image_b
        if self.mode == "diff":
            key = (self.image_a.cacheKey(), self.image_b.cacheKey())
            if self.diff_cache is None or self.diff_cache_key != key:
                self.diff_cache = difference_image(self.image_a, self.image_b)
                self.diff_cache_key = key
            return self.diff_cache
        if self.mode == "merge":
            key = ("merge", self.image_a.cacheKey(), self.image_b.cacheKey(), self.merge_orientation)
            if key not in self.scene_cache:
                self.scene_cache[key] = merged_image(self.image_a, self.image_b, self.merge_orientation)
            return self.scene_cache[key]
        canvas_size = self._preview_canvas_size(self.image_a.size())
        source = self.image_b if self.mode == "click" and self.click_show_b else self.image_a
        return self._render_canvas_cached(source, canvas_size)

    def _preview_canvas_size(self, size: QSize) -> QSize:
        if self.preview_max_side <= 0:
            return size
        return scaled_canvas_size(size, self.preview_max_side)

    def _render_canvas_cached(self, image: QImage, canvas_size: QSize) -> QImage:
        if self.preview_max_side <= 0 and image.size() == canvas_size:
            return image
        key = ("canvas", image.cacheKey(), canvas_size.width(), canvas_size.height(), self.background_color.rgba())
        if key not in self.scene_cache:
            self.scene_cache[key] = render_to_canvas(image, canvas_size, self.background_color)
        return self.scene_cache[key]

    def _display_image_cached(self, image: QImage, target: QRectF) -> QImage:
        display_size = QSize(max(1, round(target.width())), max(1, round(target.height())))
        key = ("display", image.cacheKey(), display_size.width(), display_size.height())
        if key not in self.display_cache:
            if len(self.display_cache) > 8:
                self.display_cache.clear()
            self.display_cache[key] = image.scaled(display_size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return self.display_cache[key]

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.background_color)
        if not self.image_a and not self.image_b:
            painter.setPen(QColor("#6b7280"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "上传两张图片后开始对比")
            painter.end()
            return
        scene = self.current_scene_image()
        if scene is None or scene.isNull():
            painter.end()
            return
        target = self._target_rect(scene.size())
        self.last_draw_rect = target
        display_pos = target.topLeft()
        if self.preview_max_side <= 0:
            painter.drawImage(target, scene)
            display_w = target.width()
            display_h = target.height()
        else:
            display_scene = self._display_image_cached(scene, target)
            painter.drawImage(display_pos, display_scene)
            display_w = display_scene.width()
            display_h = display_scene.height()
        if self.mode == "slide" and self.image_a and self.image_b:
            overlay = self._render_canvas_cached(self.image_b, scene.size())
            clip_width = display_w * self.slide_ratio
            painter.save()
            painter.setClipRect(QRectF(display_pos.x(), display_pos.y(), clip_width, display_h))
            if self.preview_max_side <= 0:
                painter.drawImage(target, overlay)
            else:
                painter.drawImage(display_pos, self._display_image_cached(overlay, target))
            painter.restore()
            x = display_pos.x() + clip_width
            painter.setPen(QPen(QColor("#2563eb"), 1))
            painter.drawLine(round(x), round(display_pos.y()), round(x), round(display_pos.y() + display_h))
        if self.mode == "diff" and self.show_diff_overlay:
            painter.setPen(QPen(QColor("#2563eb"), 1, Qt.PenStyle.DotLine))
            painter.drawText(14, 24, "差异高亮")
        painter.end()

    def _target_rect(self, scene_size: QSize) -> QRectF:
        if scene_size.isEmpty():
            return QRectF()
        margin = 24
        available_w = max(1, self.width() - margin * 2)
        available_h = max(1, self.height() - margin * 2)
        fit_scale = min(available_w / scene_size.width(), available_h / scene_size.height())
        draw_w = scene_size.width() * fit_scale * self.zoom
        draw_h = scene_size.height() * fit_scale * self.zoom
        return QRectF((self.width() - draw_w) / 2 + self.pan.x(), (self.height() - draw_h) / 2 + self.pan.y(), draw_w, draw_h)

    def wheelEvent(self, event) -> None:
        factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        old_zoom = self.zoom
        new_zoom = min(8.0, max(0.2, self.zoom * factor))
        if abs(new_zoom - old_zoom) < 0.0001:
            return
        mouse_pos = event.position()
        before_rect = self.last_draw_rect
        if before_rect.isValid() and before_rect.width() > 0 and before_rect.height() > 0:
            relative_x = (mouse_pos.x() - before_rect.left()) / before_rect.width()
            relative_y = (mouse_pos.y() - before_rect.top()) / before_rect.height()
            zoom_factor = new_zoom / old_zoom
            after_w = before_rect.width() * zoom_factor
            after_h = before_rect.height() * zoom_factor
            after_left = (self.width() - after_w) / 2 + self.pan.x()
            after_top = (self.height() - after_h) / 2 + self.pan.y()
            target_left = mouse_pos.x() - relative_x * after_w
            target_top = mouse_pos.y() - relative_y * after_h
            self.zoom = new_zoom
            self.pan += QPoint(round(target_left - after_left), round(target_top - after_top))
        else:
            self.zoom = new_zoom
        self.update()
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        self._refresh_cursor(event.position())
        if self.drag_start is None and self.mode == "slide" and self.last_draw_rect.contains(event.position()):
            relative_x = (event.position().x() - self.last_draw_rect.left()) / max(1, self.last_draw_rect.width())
            new_ratio = min(1.0, max(0.0, relative_x))
            if abs(new_ratio - self.slide_ratio) >= 0.001:
                self.slide_ratio = new_ratio
                self.update()
        if self.drag_start is not None:
            new_pan = self.pan_start + (event.position().toPoint() - self.drag_start)
            if new_pan != self.pan:
                self.pan = new_pan
                self.update()

    def mousePressEvent(self, event) -> None:
        if self.mode == "click" and event.button() == Qt.MouseButton.RightButton:
            self.click_show_b = not self.click_show_b
            self.update()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = event.position().toPoint()
            self.pan_start = QPoint(self.pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, _event) -> None:
        self.drag_start = None
        self._refresh_cursor()

    def leaveEvent(self, _event) -> None:
        self.unsetCursor()

    def _refresh_cursor(self, position=None) -> None:
        if self.drag_start is not None:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif position is not None and self.mode == "slide" and self.last_draw_rect.contains(position):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()


class ImageCompareWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.image_a: QImage | None = None
        self.image_b: QImage | None = None
        self.path_a: str | None = None
        self.path_b: str | None = None
        self.mode_buttons: dict[str, QToolButton] = {}
        self.background_presets = {
            "白色": QColor("#ffffff"),
            "浅灰": QColor("#f3f4f6"),
            "中灰": QColor("#d1d5db"),
            "米白": QColor("#fef3c7"),
            "浅蓝": QColor("#dbeafe"),
            "浅绿": QColor("#dcfce7"),
            "浅粉": QColor("#fce7f3"),
            "深灰": QColor("#1f2937"),
            "炭黑": QColor("#111827"),
            "黑色": QColor("#000000"),
        }
        self.last_background_choice = "浅蓝"
        self.thread_pool = QThreadPool.globalInstance()
        self.active_export_task: ExportMergeTask | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        side = QVBoxLayout()
        side.setSpacing(12)
        preview = QFrame()
        preview.setObjectName("previewShell")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = ImageCompareCanvas()
        preview_layout.addWidget(self.canvas)
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(12, 0, 12, 12)
        self.canvas_hint = QLabel()
        self.canvas_hint.setObjectName("canvasHint")
        bottom_bar.addWidget(self.canvas_hint)
        bottom_bar.addStretch()
        bottom_bar.addLayout(self._mode_buttons())
        preview_layout.addLayout(bottom_bar)
        upload_box = QGroupBox("上传图片")
        upload_layout = QVBoxLayout(upload_box)
        upload_layout.setContentsMargins(14, 18, 14, 14)
        self.slot_a = ImageDropSlot("图像 A")
        self.slot_b = ImageDropSlot("图像 B")
        self.slot_a.image_selected.connect(lambda path: self.load_image("a", path))
        self.slot_b.image_selected.connect(lambda path: self.load_image("b", path))
        upload_layout.addWidget(self.slot_a)
        upload_layout.addWidget(self.slot_b)
        control_box = QGroupBox("预览设置")
        control_layout = QGridLayout(control_box)
        control_layout.setContentsMargins(14, 18, 14, 14)
        self.orientation_combo = NoWheelComboBox()
        self.orientation_combo.addItem("自动方向", "auto")
        self.orientation_combo.addItem("横向并排", "horizontal")
        self.orientation_combo.addItem("纵向并列", "vertical")
        self.orientation_combo.currentIndexChanged.connect(self._orientation_changed)
        self.background_combo = NoWheelComboBox()
        self.background_combo.addItems(list(self.background_presets.keys()) + ["自定义..."])
        self.background_combo.setCurrentText(self.last_background_choice)
        self.background_combo.currentTextChanged.connect(self._background_changed)
        self.custom_color_input = QLineEdit()
        self.custom_color_input.setPlaceholderText("例如 #ffffff")
        self.custom_color_input.setVisible(False)
        self.custom_color_input.editingFinished.connect(self._apply_custom_color)
        self.preview_combo = NoWheelComboBox()
        self.preview_combo.addItem("不压缩", 0)
        self.preview_combo.addItem("16K", 16384)
        self.preview_combo.addItem("8K", 8192)
        self.preview_combo.addItem("4K", 4096)
        self.preview_combo.currentIndexChanged.connect(self._preview_limit_changed)
        self.slide_slider = QSlider(Qt.Orientation.Horizontal)
        self.slide_slider.setRange(0, 100)
        self.slide_slider.setValue(50)
        self.slide_slider.valueChanged.connect(self.canvas.set_slide_percent)
        reset_button = QPushButton("重置视图")
        reset_button.clicked.connect(self.canvas.reset_view)
        self.export_button = QPushButton("导出合并图")
        self.export_button.setObjectName("primaryButton")
        self.export_button.clicked.connect(self.export_merge)
        control_layout.addWidget(QLabel("拼图方向"), 0, 0)
        control_layout.addWidget(self.orientation_combo, 0, 1)
        control_layout.addWidget(QLabel("背景颜色"), 1, 0)
        control_layout.addWidget(self.background_combo, 1, 1)
        control_layout.addWidget(self.custom_color_input, 2, 1)
        control_layout.addWidget(QLabel("预览压缩"), 3, 0)
        control_layout.addWidget(self.preview_combo, 3, 1)
        control_layout.addWidget(QLabel("滑动位置"), 4, 0)
        control_layout.addWidget(self.slide_slider, 4, 1)
        control_layout.addWidget(reset_button, 5, 0, 1, 2)
        control_layout.addWidget(self.export_button, 6, 0, 1, 2)
        side.addWidget(upload_box)
        side.addWidget(control_box)
        side.addStretch()
        layout.addLayout(side, 0)
        layout.addWidget(preview, 1)
        self._update_hint("slide")

    def _mode_buttons(self) -> QHBoxLayout:
        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        modes = [("slide", "滑动"), ("click", "点击"), ("diff", "差异"), ("merge", "合并")]
        for index, (mode, label) in enumerate(modes):
            button = QToolButton()
            button.setText(label)
            button.setCheckable(True)
            button.setProperty("modeButton", True)
            if mode == "slide":
                button.setChecked(True)
            self.mode_group.addButton(button, index)
            button.clicked.connect(lambda _checked=False, m=mode: self._set_mode(m))
            self.mode_buttons[mode] = button
            wrapper.addWidget(button)
        return wrapper

    def _set_mode(self, mode: str) -> None:
        for key, button in self.mode_buttons.items():
            button.setChecked(key == mode)
        self.canvas.set_mode(mode)
        self.canvas.set_show_diff_overlay(mode == "diff")
        self._update_hint(mode)

    def _update_hint(self, mode: str) -> None:
        hints = {
            "slide": "左键拖动画布，滚轮缩放；鼠标移到图像上可调整滑动线。",
            "click": "左键拖动画布，滚轮缩放；右键切换 A/B。",
            "diff": "左键拖动画布，滚轮缩放；差异高亮仅作视觉参考。",
            "merge": "左键拖动画布，滚轮缩放；可在左侧切换拼图方向。",
        }
        self.canvas_hint.setText(hints.get(mode, "左键拖动画布，滚轮缩放。"))

    def load_image(self, slot: str, path: str) -> None:
        try:
            if Path(path).suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                raise ValueError("请选择 PNG、JPG、JPEG、WEBP 或 BMP 图片。")
            image = load_qimage(path)
        except ValueError as exc:
            QMessageBox.warning(self, "图片读取失败", str(exc))
            return
        if slot == "a":
            self.path_a = path
            self.image_a = image
            self.slot_a.set_image_info(path, image)
        else:
            self.path_b = path
            self.image_b = image
            self.slot_b.set_image_info(path, image)
        self.canvas.set_images(self.image_a, self.image_b)

    def _orientation_changed(self) -> None:
        self.canvas.set_merge_orientation(self.orientation_combo.currentData())

    def _background_changed(self, text: str) -> None:
        if text == "自定义...":
            self.custom_color_input.setVisible(True)
            self.custom_color_input.setText(self.canvas.background_color.name())
            self.custom_color_input.setFocus()
            self.custom_color_input.selectAll()
            self.last_background_choice = text
            return
        self.custom_color_input.setVisible(False)
        self.canvas.set_background_color(self.background_presets[text])
        self.last_background_choice = text

    def _apply_custom_color(self) -> None:
        if self.background_combo.currentText() != "自定义...":
            return
        try:
            color = normalize_color_code(self.custom_color_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "颜色代码无效", str(exc))
            self.custom_color_input.setFocus()
            self.custom_color_input.selectAll()
            return
        self.custom_color_input.setText(color.name())
        self.canvas.set_background_color(color)

    def _preview_limit_changed(self) -> None:
        self.canvas.set_preview_max_side(self.preview_combo.currentData())

    def export_merge(self) -> None:
        if not self.image_a or not self.image_b:
            QMessageBox.information(self, "无法导出", "请先上传图像 A 和图像 B。")
            return
        orientation = self.orientation_combo.currentData()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_a = Path(self.path_a).stem if self.path_a else "A"
        name_b = Path(self.path_b).stem if self.path_b else "B"
        default_name = f"{name_a}_{name_b}_{orientation}_{timestamp}.png"
        file_path, _ = QFileDialog.getSaveFileName(self, "保存合并图片", default_name, "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;BMP Image (*.bmp)")
        if not file_path:
            return
        self.export_button.setEnabled(False)
        self.export_button.setText("正在导出...")
        task = ExportMergeTask(self.image_a, self.image_b, orientation, file_path)
        task.signals.finished.connect(self._export_finished)
        task.signals.failed.connect(self._export_failed)
        self.active_export_task = task
        self.thread_pool.start(task)

    def _export_finished(self, file_path: str) -> None:
        self.export_button.setEnabled(True)
        self.export_button.setText("导出合并图")
        self.active_export_task = None
        QMessageBox.information(self, "导出完成", f"图片已保存：\n{file_path}")

    def _export_failed(self, message: str) -> None:
        self.export_button.setEnabled(True)
        self.export_button.setText("导出合并图")
        self.active_export_task = None
        QMessageBox.warning(self, "保存失败", message)


class LctzImageToolkitWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LCTZ Image Toolkit")
        self.setMinimumSize(860, 560)
        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(RatioCalculatorWidget(), "比例计算")
        tabs.addTab(ImageCompareWidget(), "图片对比")
        self.setCentralWidget(tabs)
        about_action = self.menuBar().addAction("关于 / 致谢")
        about_action.triggered.connect(self.show_about)

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            "关于 / 致谢",
            f"LCTZ Image Toolkit\n版本：{APP_VERSION}\n\n"
            "图片滑动/点击对比体验参考了 rgthree-comfy 的 Image Comparer (rgthree)。\n"
            "rgthree-comfy 使用 MIT License，Copyright (c) 2023 Regis Gaughan, III (rgthree)。\n\n"
            "本应用没有复制 rgthree-comfy 的前端代码，而是使用 PySide6 独立实现桌面版交互。\n"
            "感谢 rgthree-comfy 项目带来的优秀体验灵感。",
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f5f7fb;
                color: #20242a;
                font-family: "Microsoft YaHei UI", "Segoe UI";
                font-size: 14px;
            }
            QTabWidget::pane { border: 0; }
            QTabBar::tab {
                background: #e8eef7;
                color: #334155;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 3px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #111827;
                font-weight: 600;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #dde3ee;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #27364a;
            }
            QLineEdit, QComboBox {
                min-height: 32px;
                padding: 3px 8px;
                border: 1px solid #c9d3e1;
                border-radius: 6px;
                background: #ffffff;
            }
            QLineEdit:disabled { color: #94a3b8; background: #eef2f7; }
            QPushButton, QToolButton {
                min-height: 30px;
                padding: 4px 10px;
                border: 1px solid #c9d3e1;
                border-radius: 6px;
                background: #ffffff;
                color: #27364a;
            }
            QPushButton:hover, QToolButton:hover { border-color: #2878d7; }
            QPushButton#primaryButton {
                min-height: 34px;
                color: #ffffff;
                background: #2878d7;
                border: 0;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton#primaryButton:hover { background: #1f6ec9; }
            QToolButton[modeButton="true"] { background: #edf3fb; border-color: #cbd8e8; }
            QToolButton[modeButton="true"]:checked { background: #2878d7; color: #ffffff; border-color: #2878d7; }
            QFrame#dropSlot {
                background: #fbfdff;
                border: 1px dashed #aebbd0;
                border-radius: 8px;
                min-height: 84px;
            }
            QFrame#dropSlot[loaded="true"] {
                background: #f1f7ff;
                border-style: solid;
                border-color: #72a7e6;
            }
            QLabel#dropTitle { color: #1f2937; font-weight: 700; }
            QLabel#dropHint, QLabel#hintLabel { color: #697386; }
            QFrame#previewShell {
                background: #ffffff;
                border-radius: 8px;
                border: 1px solid #d9e2ef;
            }
            QLabel#canvasHint { color: #5f6f84; background: transparent; }
            QTableWidget {
                background: #ffffff;
                alternate-background-color: #f8fbff;
                border: 1px solid #dfe6f1;
                border-radius: 6px;
                gridline-color: transparent;
                selection-background-color: #dbeafe;
                selection-color: #111827;
            }
            QTableWidget::item {
                padding: 4px 6px;
            }
            QTableWidget::item:hover {
                background: #eef6ff;
                color: #111827;
            }
            QTableWidget::item:selected {
                background: #dbeafe;
                color: #111827;
            }
            QHeaderView::section {
                background: #eef3f9;
                color: #344255;
                border: 0;
                border-bottom: 1px solid #dfe6f1;
                padding: 6px 8px;
                font-weight: 600;
            }
            """
        )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LCTZ Image Toolkit")
    window = LctzImageToolkitWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
