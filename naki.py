#!/usr/bin/env python3
"""
Naki (ناکی) - Professional Desktop Pet (Tray Icon Edition)
Updates: English context menus, Windows System Tray integration, and unified exiting.
"""

import sys
import os
import random
import ctypes
from PyQt6.QtWidgets import QApplication, QWidget, QMenu, QSystemTrayIcon
from PyQt6.QtGui import QPainter, QAction, QCursor, QPixmap, QImage, QColor, QIcon
from PyQt6.QtCore import Qt, QTimer, QPoint

def generate_mouse_sprite():
    """تولید خودکار یک موش پیکسلی رترو با کد در صورت عدم وجود"""
    file_name = "mouse_food.png"
    if os.path.exists(file_name):
        return
    
    img = QImage(16, 16, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    
    # رسم بدنه موش (خاکستری)
    painter.fillRect(4, 7, 8, 5, QColor("#8A8A8A"))
    painter.fillRect(10, 6, 3, 4, QColor("#A1A1A1"))
    
    # گوش‌ها و بینی صورتی
    painter.fillRect(6, 5, 2, 2, QColor("#FFB6C1"))
    painter.fillRect(13, 8, 1, 1, QColor("#FF69B4"))
    
    # چشم سیاه
    painter.fillRect(10, 7, 1, 1, QColor("#000000"))
    
    # دم موش
    painter.fillRect(1, 9, 3, 1, QColor("#D3D3D3"))
    painter.fillRect(3, 8, 1, 1, QColor("#D3D3D3"))
    
    painter.end()
    img.save(file_name)

class FoodItem(QWidget):
    """غذای موش با فیزیک سقوط مستقل"""
    def __init__(self, start_pos):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        generate_mouse_sprite()
        base_pixmap = QPixmap("mouse_food.png")
        self.pixmap = base_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        self.setFixedSize(self.pixmap.width(), self.pixmap.height())
        
        self.move(start_pos)
        
        self.velocity_y = 0.0
        self.gravity = 2.5
        self.is_on_floor = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fall)
        self.timer.start(40)
        self.show()

    def fall(self):
        if not self.is_on_floor:
            self.velocity_y += self.gravity
            next_y = self.pos().y() + int(self.velocity_y)
            
            screen_geo = QApplication.primaryScreen().availableGeometry()
            floor_y = screen_geo.height() - self.height() - 15
            
            if next_y >= floor_y:
                next_y = floor_y
                self.is_on_floor = True
                self.timer.stop()
            self.move(self.pos().x(), next_y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        painter.end()

class NakiPet(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.scale_factor = 3  
        self.is_docked = False
        self.raw_base_frames = []
        self.load_sprite_sheet()
        
        self.state_indices = {
            "IDLE": [0],
            "SCRATCHING": [1, 2, 3, 2, 1, 0], 
            "CHASING": [4, 5],
            "SLEEPING": [6, 7, 8, 9],
            "STARTLED": [10]
        }
        
        self.current_state = "IDLE"
        self.frame_index = 0
        self.speed = 7 
        self.idle_counter = 0
        self.animation_tick = 0
        
        self.is_falling = False
        self.velocity_y = 0.0
        self.gravity_acceleration = 1.8  
        
        self.active_food = None
        self.eating_timer = 0
        
        self._drag_active = False
        self._drag_pos = QPoint()
        
        self.update_window_size()
        
        # راه‌اندازی سیستم منوی Tray ویندوز
        self.setup_system_tray()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_behavior)
        self.timer.start(60)
        
        self.show()

    def load_sprite_sheet(self):
        image_path = "neko.png"
        if not os.path.exists(image_path):
            print(f"Error: {image_path} missing!")
            sys.exit(1)
            
        full_sprite = QPixmap(image_path)
        frame_w = full_sprite.width() // 4
        frame_h = full_sprite.height() // 3
        
        self.raw_base_frames = []
        for row in range(3):
            for col in range(4):
                if row == 2 and col == 3:
                    break
                self.raw_base_frames.append(full_sprite.copy(col * frame_w, row * frame_h, frame_w, frame_h))

    def update_window_size(self):
        if self.raw_base_frames:
            w = int(self.raw_base_frames[0].width() * self.scale_factor)
            h = int(self.raw_base_frames[0].height() * self.scale_factor)
            self.setFixedSize(w, h)
            self.update()

    def setup_system_tray(self):
        """ایجاد آیکون و منوی انگلیسی در بخش System Tray ویندوز"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # لود کردن لوگوی اختصاصی شما برای Tray ویندوز
        if os.path.exists("logo.png"):
            self.tray_icon.setIcon(QIcon("logo.png"))
        elif os.path.exists("logo.ico"):
            self.tray_icon.setIcon(QIcon("logo.ico"))
        else:
            # در صورت نبود لوگو، اولین فریم ناکی به عنوان آیکون موقت قرار می‌گیرد
            if self.raw_base_frames:
                self.tray_icon.setIcon(QIcon(self.raw_base_frames[0]))

        # ساخت منوی انگلیسی برای راست‌کلیک روی آیکون Tray
        tray_menu = QMenu()
        tray_menu.setStyleSheet("QMenu { background-color: #222; color: white; font-family: Arial; } QMenu::item:selected { background-color: #555; }")
        
        feed_act = QAction("🍕 Feed (Spawn Mouse)", self)
        feed_act.triggered.connect(self.spawn_food)
        tray_menu.addAction(feed_act)
        
        wake_act = QAction("⏰ Wake Up / Reset Naki", self)
        wake_act.triggered.connect(self.undock_from_corner)
        tray_menu.addAction(wake_act)
        
        tray_menu.addSeparator()
        
        exit_act = QAction("❌ Exit Naki", self)
        exit_act.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(exit_act)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("Naki - Desktop Pet")
        self.tray_icon.show()

    def check_if_desktop_is_active(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd: return True
            buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
            return hwnd == int(self.winId()) or buf.value in ["Progman", "WorkerW"]
        except:
            return True

    def get_current_frame_pixmap(self):
        indices = self.state_indices[self.current_state]
        actual_frame = indices[self.frame_index % len(indices)]
        return self.raw_base_frames[actual_frame].scaled(
            self.width(), self.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
        )

    def spawn_food(self):
        if self.active_food is not None:
            self.active_food.close()
            
        screen_geo = QApplication.primaryScreen().availableGeometry()
        naki_x = self.pos().x()
        
        spawn_x = random.randint(60, screen_geo.width() - 80)
        if abs(spawn_x - naki_x) < 400:
            if naki_x > screen_geo.width() / 2:
                spawn_x = random.randint(60, max(60, naki_x - 350))
            else:
                spawn_x = random.randint(min(screen_geo.width() - 80, naki_x + 350), screen_geo.width() - 80)
                
        self.active_food = FoodItem(QPoint(spawn_x, 40))
        
        if self.is_docked:
            self.undock_from_corner()

    def dock_to_corner(self):
        if self.active_food: 
            return
        self.is_falling = False
        self.is_docked = True
        self.scale_factor = 1.5  
        self.update_window_size()
        self.set_state("SLEEPING")
        
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geo.width() - self.width() - 15, screen_geo.height() - self.height() - 15)

    def undock_from_corner(self):
        self.is_docked = False
        self.scale_factor = 3  
        self.update_window_size()
        self.set_state("STARTLED")
        self.idle_counter = 0

    def set_state(self, new_state):
        if self.current_state != new_state:
            self.current_state = new_state
            self.frame_index = 0

    def update_behavior(self):
        self.animation_tick += 1
        self.raise_()
        
        if self._drag_active:
            self.update()
            return

        if self.is_falling:
            self.velocity_y += self.gravity_acceleration
            next_y = self.pos().y() + int(self.velocity_y)
            screen_geo = QApplication.primaryScreen().availableGeometry()
            floor_y = screen_geo.height() - self.height() - 15
            
            if next_y >= floor_y:
                next_y = floor_y
                self.is_falling = False
                self.set_state("SCRATCHING")
                self.idle_counter = 0
            self.move(self.pos().x(), next_y)
            
            if self.animation_tick % 4 == 0:
                self.frame_index = (self.frame_index + 1) % len(self.state_indices[self.current_state])
            self.update()
            return

        desktop_active = self.check_if_desktop_is_active()
        
        if self.active_food and not self.active_food.isVisible():
            self.active_food = None

        if self.active_food:
            target_pos = self.active_food.pos() + QPoint(self.active_food.width()//2, self.active_food.height()//2)
        else:
            target_pos = QCursor.pos()

        pet_center = self.pos() + QPoint(self.width() // 2, self.height() // 2)
        vector = target_pos - pet_center
        distance = (vector.x()**2 + vector.y()**2)**0.5

        if self.active_food and distance <= 35:
            if self.current_state != "SCRATCHING":
                self.set_state("SCRATCHING") 
                self.eating_timer = 0
            
            self.eating_timer += 1
            if self.eating_timer > 45: 
                self.active_food.close()
                self.active_food = None
                self.set_state("IDLE")
                self.idle_counter = 0
            
            if self.animation_tick % 3 == 0:
                self.frame_index = (self.frame_index + 1) % len(self.state_indices["SCRATCHING"])
            self.update()
            return

        if not desktop_active and not self.active_food:
            if not self.is_docked: self.dock_to_corner()
            if self.animation_tick % 8 == 0:
                self.frame_index = (self.frame_index + 1) % len(self.state_indices[self.current_state])
            self.update()
            return
        elif self.is_docked and desktop_active and distance < 180:
            self.undock_from_corner()

        if self.current_state == "STARTLED":
            self.idle_counter += 1
            if self.idle_counter > 12: self.set_state("IDLE")
        elif distance > 22:  
            self.set_state("CHASING")
            self.idle_counter = 0
            dx = int((vector.x() / distance) * self.speed)
            dy = int((vector.y() / distance) * self.speed)
            self.move(self.pos().x() + dx, self.pos().y() + dy)
        else:
            if self.current_state == "CHASING": self.set_state("IDLE")
            self.idle_counter += 1
            
            if self.idle_counter > 116: 
                self.set_state("SLEEPING")
            elif self.current_state != "SLEEPING":
                if self.idle_counter % 25 == 0 and random.random() < 0.7:
                    self.set_state("SCRATCHING")
                elif self.current_state == "SCRATCHING" and self.frame_index == len(self.state_indices["SCRATCHING"]) - 1:
                    self.set_state("IDLE")

        rate = 8 if self.current_state == "SLEEPING" else 4
        if self.animation_tick % rate == 0:
            indices = self.state_indices[self.current_state]
            self.frame_index = (self.frame_index + 1) % len(indices)
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.get_current_frame_pixmap())
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_falling = False
            if self.is_docked: self.undock_from_corner()
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.set_state("STARTLED")
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_active and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
            screen_geo = QApplication.primaryScreen().availableGeometry()
            if self.pos().y() < (screen_geo.height() - self.height() - 35):
                self.is_falling = True
                self.velocity_y = 0.0
                self.set_state("STARTLED")
            else:
                self.set_state("IDLE")
            event.accept()

    def contextMenuEvent(self, event):
        """ساخت منوی انگلیسی هنگام راست‌کلیک مستقیم روی خود ناکی"""
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #222; color: white; font-family: Arial; } QMenu::item:selected { background-color: #555; }")
        
        feed_action = QAction("🍕 Feed (Spawn Mouse)", self)
        feed_action.triggered.connect(self.spawn_food)
        menu.addAction(feed_action)
        
        wake_action = QAction("⏰ Wake Up / Reset Naki", self)
        wake_action.triggered.connect(self.undock_from_corner)
        menu.addAction(wake_action)
        
        menu.addSeparator()
        exit_action = QAction("❌ Exit Naki", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(exit_action)
        
        menu.exec(event.globalPos())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # برای اینکه برنامه با بستن پنجره اصلی کلاً بسته نشود و سیستم Tray فعال بماند
    app.setQuitOnLastWindowClosed(False)
    pet = NakiPet()
    sys.exit(app.exec())
