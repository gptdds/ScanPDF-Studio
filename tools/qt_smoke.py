from PySide6.QtCore import QCoreApplication, qVersion


print(f"Qt {qVersion()}")
app = QCoreApplication([])
print("QtCore import and QCoreApplication OK")
