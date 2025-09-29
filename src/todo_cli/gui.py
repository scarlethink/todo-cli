from __future__ import annotations
from datetime import date
from typing import Optional
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QComboBox, QDialogButtonBox, QDateEdit, QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt, QDate

from todo_cli.db import init_db
from todo_cli.models import TaskIn, Task
from todo_cli.repository import TaskRepo


# İç değerler (DB’de bunlar saklanır)
PRIORITIES = ["low", "med", "high"]
STATUSES = ["todo", "doing", "done"]

# Görsel etiketler (TR)
STATUS_LABELS = {"all": "tümü", "todo": "yapılacak", "doing": "yapılıyor", "done": "tamamlandı"}
PRIORITY_LABELS = {"all": "tümü", "low": "düşük", "med": "orta", "high": "yüksek"}


class TaskDialog(QDialog):
    def __init__(self, parent=None, task: Optional[Task] = None):
        super().__init__(parent)
        self.setWindowTitle("Görev" + (" Düzenle" if task else " Ekle"))

        layout = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.notes_edit = QLineEdit()

        self.priority_box = QComboBox()
        for key in PRIORITIES:
            self.priority_box.addItem(PRIORITY_LABELS[key], key)  # görünen TR, data EN

        self.due_edit = QDateEdit(calendarPopup=True)
        self.due_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_edit.setDate(QDate.currentDate())

        self.tags_edit = QLineEdit()

        layout.addRow("Başlık*", self.title_edit)
        layout.addRow("Notlar", self.notes_edit)
        layout.addRow("Öncelik", self.priority_box)
        layout.addRow("Bitiş", self.due_edit)
        layout.addRow("Etiketler (virgülle)", self.tags_edit)

        if task:
            self.title_edit.setText(task.title)
            self.notes_edit.setText(task.notes or "")
            idx = self.priority_box.findData(task.priority)
            if idx >= 0:
                self.priority_box.setCurrentIndex(idx)
            if task.due:
                y, m, d = task.due.year, task.due.month, task.due.day
                self.due_edit.setDate(QDate(y, m, d))
            self.tags_edit.setText(", ".join(task.tags))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def data(self) -> TaskIn:
        due_py: Optional[date] = None
        if self.due_edit.date().isValid():
            qd = self.due_edit.date()
            due_py = date(qd.year(), qd.month(), qd.day())
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        priority_en = self.priority_box.currentData() or "med"
        return TaskIn(
            title=self.title_edit.text().strip(),
            notes=self.notes_edit.text().strip() or None,
            due=due_py,
            priority=priority_en,
            tags=tags,
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TODO – Görev Yöneticisi (GUI)")
        init_db()
        self.repo = TaskRepo()

        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        # --- Filtre / Arama / Export barı ---
        hb = QHBoxLayout()

        self.status_box = QComboBox()
        self.status_box.addItem(STATUS_LABELS["all"], "all")
        for key in STATUSES:
            self.status_box.addItem(STATUS_LABELS[key], key)

        self.priority_filter_box = QComboBox()
        self.priority_filter_box.addItem(PRIORITY_LABELS["all"], "all")
        for key in PRIORITIES:
            self.priority_filter_box.addItem(PRIORITY_LABELS[key], key)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Ara: başlık/nota göre...")

        refresh_btn = QPushButton("Filtrele")
        refresh_btn.clicked.connect(self.refresh)

        export_btn = QPushButton("Dışa Aktar")
        export_btn.clicked.connect(self.export_dialog)

        for w in (self.status_box, self.priority_filter_box, self.search_edit, refresh_btn, export_btn):
            hb.addWidget(w)
        v.addLayout(hb)

        # --- Tablo ---
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["id", "başlık", "durum", "öncelik", "bitiş", "etiketler"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # pencereye oranlı
        self.table.setStyleSheet("""
        QTableWidget { margin: 10px; padding: 6px; gridline-color: #555; }
        QHeaderView::section { background-color: #333; color: white; font-weight: bold; padding: 4px; }
        """)
        v.addWidget(self.table)

        # --- Aksiyon butonları ---
        actions = QHBoxLayout()
        add_btn = QPushButton("Ekle")
        edit_btn = QPushButton("Düzenle")
        doing_btn = QPushButton("Yapılıyor")
        done_btn = QPushButton("Tamamlandı")
        rm_btn = QPushButton("Sil")
        add_btn.clicked.connect(self.add_task)
        edit_btn.clicked.connect(self.edit_task)
        doing_btn.clicked.connect(lambda: self.set_status("doing"))
        done_btn.clicked.connect(lambda: self.set_status("done"))
        rm_btn.clicked.connect(self.remove_task)
        for b in (add_btn, edit_btn, doing_btn, done_btn, rm_btn):
            actions.addWidget(b)
        v.addLayout(actions)

        self.refresh()

    def _current_id(self) -> Optional[int]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        r = rows[0].row()
        return int(self.table.item(r, 0).text())

    def refresh(self):
        status_en = self.status_box.currentData()
        if status_en == "all":
            status_en = None
        priority_en = self.priority_filter_box.currentData()
        if priority_en == "all":
            priority_en = None
        q = self.search_edit.text().strip() or None

        tasks = self.repo.list(status=status_en, priority=priority_en, query=q)

        self.table.setRowCount(0)
        for t in tasks:
            r = self.table.rowCount()
            self.table.insertRow(r)
            cells = [
                str(t.id),
                t.title,
                STATUS_LABELS.get(t.status, t.status),
                PRIORITY_LABELS.get(t.priority, t.priority),
                t.due.isoformat() if t.due else "",
                ", ".join(t.tags),
            ]
            for c, val in enumerate(cells):
                item = QTableWidgetItem(val)
                if c == 1:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)

    def add_task(self):
        dlg = TaskDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.data()
            if not data.title:
                QMessageBox.warning(self, "Uyarı", "Başlık boş olamaz.")
                return
            self.repo.add(data)
            self.refresh()

    def edit_task(self):
        task_id = self._current_id()
        if not task_id:
            QMessageBox.information(self, "Bilgi", "Önce bir görev seç.")
            return
        current = next((t for t in self.repo.list() if t.id == task_id), None)
        if not current:
            QMessageBox.warning(self, "Hata", "Görev bulunamadı.")
            return
        dlg = TaskDialog(self, task=current)
        if dlg.exec() == QDialog.Accepted:
            self.repo.edit(task_id, dlg.data())
            self.refresh()

    def set_status(self, status: str):
        task_id = self._current_id()
        if not task_id:
            QMessageBox.information(self, "Bilgi", "Önce bir görev seç.")
            return
        self.repo.set_status(task_id, status)
        self.refresh()

    def remove_task(self):
        task_id = self._current_id()
        if not task_id:
            QMessageBox.information(self, "Bilgi", "Önce bir görev seç.")
            return
        ok = self.repo.remove(task_id)
        if not ok:
            QMessageBox.warning(self, "Hata", "Silinemedi.")
        self.refresh()

    def export_dialog(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Dışa Aktar", "gorevler.csv", "CSV (*.csv);;JSON (*.json)"
        )
        if not path:
            return
        p = Path(path)
        tasks = self.repo.list()
        records = [t.model_dump() for t in tasks]
        try:
            if p.suffix.lower() == ".json":
                import json
                p.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                import csv
                fieldnames = (
                    list(records[0].keys())
                    if records
                    else ["id", "title", "notes", "status", "priority", "due", "tags", "created_at", "updated_at"]
                )
                with p.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=fieldnames)
                    w.writeheader()
                    for r in records:
                        r = dict(r)
                        r["tags"] = ", ".join(r.get("tags", []))
                        w.writerow(r)
            QMessageBox.information(self, "Başarılı", f"{len(records)} kayıt dışa aktarıldı:\n{p}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma başarısız:\n{e}")


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(950, 560)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
