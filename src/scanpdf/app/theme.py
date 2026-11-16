LIGHT = """
* { font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; }
QMainWindow, QWidget#Root { background: #f5f6f7; color: #20272d; }
QWidget { color: #20272d; }
QFrame#Sidebar { background: #eef0f1; border: none; }
QFrame#Card, QWidget#Card { background: #ffffff; border: 1px solid #e2e6e8; border-radius: 10px; }
QLabel#Brand { font-size: 17px; font-weight: 600; letter-spacing: .2px; }
QLabel#BrandMark { background: #1e5b50; color: white; border-radius: 8px;
  font-size: 15px; font-weight: 700; }
QLabel#PageTitle { font-size: 24px; font-weight: 600; color: #182126; }
QLabel#Subtitle { color: #6d7880; font-size: 13px; }
QLabel#SectionTitle { font-size: 14px; font-weight: 600; margin-top: 4px; }
QLabel#Meta { color: #77838b; font-size: 12px; }
QLabel#Metric { font-size: 26px; font-weight: 600; color: #1e5b50; }
QLabel#Pill { background: #e8f1ef; color: #225f54; border-radius: 10px;
  padding: 3px 9px; font-size: 12px; }
QLabel#WarningPill { background: #fff2dc; color: #8a5a0a; border-radius: 10px;
  padding: 3px 9px; font-size: 12px; }
QPushButton { background: #ffffff; border: 1px solid #d5dbde; border-radius: 7px;
  padding: 7px 14px; min-height: 20px; }
QPushButton:hover { background: #f8faf9; border-color: #b8c2c6; }
QPushButton:pressed { background: #edf1f0; }
QPushButton:disabled { color: #a6aeb3; background: #f3f5f5; }
QPushButton#Primary { background: #1e5b50; color: #ffffff; border: 1px solid #1e5b50;
  font-weight: 600; padding: 8px 18px; }
QPushButton#Primary:hover { background: #267064; }
QPushButton#Primary:pressed { background: #17483f; }
QPushButton#Danger { color: #9b3c32; }
QPushButton#Nav { text-align: left; border: none; background: transparent;
  padding: 9px 13px; border-radius: 7px; color: #526068; }
QPushButton#Nav:hover { background: #e3e7e8; color: #20272d; }
QPushButton#Nav:checked { background: #ffffff; color: #1e5b50; font-weight: 600; }
QPushButton#Link { border: none; background: transparent; color: #1e5b50; padding: 3px; }
QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
  background: #ffffff; border: 1px solid #d7dde0; border-radius: 7px; padding: 6px 8px;
  selection-background-color: #cfe2dd; }
QTextEdit:focus, QLineEdit:focus, QComboBox:focus { border: 1px solid #4b8a7c; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: white; border: 1px solid #d7dde0;
  selection-background-color: #e6f0ed; selection-color: #20272d; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #aeb8bd;
  border-radius: 4px; background: white; }
QCheckBox::indicator:checked { background: #1e5b50; border-color: #1e5b50; }
QProgressBar { border: none; background: #e4e8e9; border-radius: 4px; height: 7px;
  text-align: center; color: transparent; }
QProgressBar::chunk { background: #2f786b; border-radius: 4px; }
QListWidget { background: #ffffff; border: 1px solid #e1e5e7; border-radius: 8px;
  outline: none; padding: 4px; }
QListWidget::item { padding: 10px 11px; border-radius: 6px; margin: 1px 0; }
QListWidget::item:selected { background: #e6f0ed; color: #183d35; }
QListWidget::item:hover { background: #f5f8f7; }
QTableWidget { background: white; border: 1px solid #e1e5e7; border-radius: 8px;
  gridline-color: #eef1f2; selection-background-color: #e6f0ed;
  selection-color: #183d35; }
QHeaderView::section { background: #f6f8f8; border: none; border-bottom: 1px solid #e6eaeb;
  padding: 8px; font-weight: 600; color: #5e6a72; }
QTabWidget::pane { border: 1px solid #e2e6e8; background: white; border-radius: 8px; }
QTabBar::tab { background: transparent; color: #69757d; padding: 8px 14px; border: none; }
QTabBar::tab:selected { color: #1e5b50; border-bottom: 2px solid #1e5b50; font-weight: 600; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #c8d0d3; min-height: 30px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #c8d0d3; min-width: 30px; border-radius: 5px; }
QToolTip { background: #20272d; color: white; border: none; padding: 5px; }
QStatusBar { background: #f5f6f7; color: #6d7880; }
QSplitter::handle { background: #e6eaeb; width: 1px; height: 1px; }
QMenu { background: white; border: 1px solid #e0e5e7; padding: 5px; }
QMenu::item { padding: 7px 22px; border-radius: 4px; }
QMenu::item:selected { background: #e6f0ed; }
"""

DARK = """
* { font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; }
QMainWindow, QWidget#Root { background: #171a1c; color: #e8eceb; }
QWidget { color: #e8eceb; }
QFrame#Sidebar { background: #1d2123; border: none; }
QFrame#Card, QWidget#Card { background: #22272a; border: 1px solid #30373a; border-radius: 10px; }
QLabel#Brand { font-size: 17px; font-weight: 600; }
QLabel#BrandMark { background: #4fa08e; color: #102420; border-radius: 8px;
  font-size: 15px; font-weight: 700; }
QLabel#PageTitle { font-size: 24px; font-weight: 600; color: #f3f6f5; }
QLabel#Subtitle { color: #919da3; font-size: 13px; }
QLabel#SectionTitle { font-size: 14px; font-weight: 600; margin-top: 4px; }
QLabel#Meta { color: #8a969b; font-size: 12px; }
QLabel#Metric { font-size: 26px; font-weight: 600; color: #72b9a8; }
QLabel#Pill { background: #243b35; color: #9bd5c6; border-radius: 10px;
  padding: 3px 9px; font-size: 12px; }
QLabel#WarningPill { background: #3a3020; color: #e3bc7b; border-radius: 10px;
  padding: 3px 9px; font-size: 12px; }
QPushButton { background: #2b3134; border: 1px solid #3a4246; border-radius: 7px;
  padding: 7px 14px; min-height: 20px; color: #e7ebea; }
QPushButton:hover { background: #343b3f; border-color: #4c565a; }
QPushButton:pressed { background: #252b2e; }
QPushButton:disabled { color: #626c71; background: #22272a; }
QPushButton#Primary { background: #4d9d8d; color: #0f2420; border: 1px solid #4d9d8d;
  font-weight: 600; padding: 8px 18px; }
QPushButton#Primary:hover { background: #62b2a0; }
QPushButton#Primary:pressed { background: #3b8173; }
QPushButton#Danger { color: #e68d80; }
QPushButton#Nav { text-align: left; border: none; background: transparent;
  padding: 9px 13px; border-radius: 7px; color: #98a4a9; }
QPushButton#Nav:hover { background: #262c2f; color: #e8eceb; }
QPushButton#Nav:checked { background: #2a3134; color: #8fd2c2; font-weight: 600; }
QPushButton#Link { border: none; background: transparent; color: #83c9b9; padding: 3px; }
QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
  background: #1b2022; border: 1px solid #394145; border-radius: 7px; padding: 6px 8px;
  color: #e8eceb; selection-background-color: #30584f; }
QTextEdit:focus, QLineEdit:focus, QComboBox:focus { border: 1px solid #5aa795; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #22282b; border: 1px solid #394145;
  selection-background-color: #30584f; color: #e8eceb; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #5b666b;
  border-radius: 4px; background: #1b2022; }
QCheckBox::indicator:checked { background: #4d9d8d; border-color: #4d9d8d; }
QProgressBar { border: none; background: #2d3437; border-radius: 4px; height: 7px;
  text-align: center; color: transparent; }
QProgressBar::chunk { background: #5aab9a; border-radius: 4px; }
QListWidget { background: #22272a; border: 1px solid #333b3e; border-radius: 8px;
  outline: none; padding: 4px; }
QListWidget::item { padding: 10px 11px; border-radius: 6px; margin: 1px 0; }
QListWidget::item:selected { background: #2c4540; color: #d9f1ea; }
QListWidget::item:hover { background: #272e31; }
QTableWidget { background: #22272a; border: 1px solid #333b3e; border-radius: 8px;
  gridline-color: #2c3336; selection-background-color: #2c4540;
  selection-color: #d9f1ea; }
QHeaderView::section { background: #262d30; border: none; border-bottom: 1px solid #353d40;
  padding: 8px; font-weight: 600; color: #9ba7ac; }
QTabWidget::pane { border: 1px solid #30383b; background: #22272a; border-radius: 8px; }
QTabBar::tab { background: transparent; color: #8e9a9f; padding: 8px 14px; border: none; }
QTabBar::tab:selected { color: #8fd2c2; border-bottom: 2px solid #5aab9a; font-weight: 600; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #465055; min-height: 30px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #465055; min-width: 30px; border-radius: 5px; }
QToolTip { background: #e8eceb; color: #1a2023; border: none; padding: 5px; }
QStatusBar { background: #171a1c; color: #8e9a9f; }
QSplitter::handle { background: #30383b; width: 1px; height: 1px; }
QMenu { background: #23292c; border: 1px solid #363f42; padding: 5px; }
QMenu::item { padding: 7px 22px; border-radius: 4px; }
QMenu::item:selected { background: #2c4540; }
"""

