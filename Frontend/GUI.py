import os
import sys
import threading
import time
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from dotenv import dotenv_values
import uvicorn

env_vars = dotenv_values(".env")
Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Jarvis")
current_dir = os.getcwd()

TempDirPath = os.path.join(current_dir, "Frontend", "Files")
GraphicsDirPath = os.path.join(current_dir, "Frontend", "Graphics")

os.makedirs(TempDirPath, exist_ok=True)
os.makedirs(GraphicsDirPath, exist_ok=True)

_PORT = 8000

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    return '\n'.join([line for line in lines if line.strip()])

def QueryModifier(Query):
    new_query = Query.lower().strip()
    if not new_query:
        return ""
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom",
                      "can you", "what's", "where's", "how's"]
    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."
    return new_query.capitalize()

def SetMicrophoneStatus(Command):
    with open(os.path.join(TempDirPath, 'Mic.data'), "w", encoding='utf-8') as file:
        file.write(Command)

def GetMicrophoneStatus():
    with open(os.path.join(TempDirPath, 'Mic.data'), "r", encoding='utf-8') as file:
        Status = file.read()
    return Status

def SetAssistantStatus(Status):
    with open(os.path.join(TempDirPath, 'Status.data'), "w", encoding='utf-8') as file:
        file.write(Status)

def GetAssistantStatus():
    with open(os.path.join(TempDirPath, 'Status.data'), "r", encoding='utf-8') as file:
        Status = file.read()
    return Status

def MicButtonInitialed():
    SetMicrophoneStatus("False")

def MicButtonClosed():
    SetMicrophoneStatus("True")

def GraphicsDirectoryPath(Filename):
    return os.path.join(GraphicsDirPath, Filename)

def TempDirectoryPath(Filename):
    return os.path.join(TempDirPath, Filename)

def ShowTextToScreen(Text):
    with open(os.path.join(TempDirPath, 'Responses.data'), "w", encoding='utf-8') as file:
        file.write(Text)

def AppendAssistantResponse(Response):
    with open(os.path.join(TempDirPath, 'Responses.data'), "a", encoding='utf-8') as file:
        file.write(f"\n{Assistantname}: {Response}")

def InitializeFiles():
    for filename in ['Mic.data', 'Status.data', 'Responses.data', 'Query.data', 'Transcription.data']:
        filepath = TempDirectoryPath(filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("")


class JarvisWebPage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.featurePermissionRequested.connect(self._on_permission)

    def _on_permission(self, url, feature):
        if feature in [
            QWebEnginePage.MediaAudioCapture,
            QWebEnginePage.MediaVideoCapture,
            QWebEnginePage.MediaAudioVideoCapture,
            QWebEnginePage.Geolocation,
            QWebEnginePage.Notifications,
        ]:
            self.setFeaturePermission(url, feature, QWebEnginePage.PermissionGrantedByUser)


class JarvisWebWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{Assistantname} AI Assistant")
        self.setAttribute(Qt.WA_DeleteOnClose)

        desktop = QApplication.desktop()
        screen_geo = desktop.screenGeometry()
        self.setGeometry(screen_geo)

        self.page = JarvisWebPage(self)
        self.browser = QWebEngineView()
        self.browser.setPage(self.page)
        self.setCentralWidget(self.browser)

        self._startup_timer = QTimer(self)
        self._startup_timer.timeout.connect(self._try_connect)
        self._startup_timer.start(200)
        self._attempts = 0

    def _try_connect(self):
        self._attempts += 1
        if self._attempts > 30:
            self._startup_timer.stop()
            self.browser.setHtml("<h2>Server failed to start</h2>")
            return
        import urllib.request
        try:
            urllib.request.urlopen(f"http://localhost:{_PORT}", timeout=1)
            self._startup_timer.stop()
            self.browser.setUrl(QUrl(f"http://localhost:{_PORT}"))
        except:
            pass


def _run_server():
    from Backend.WebServer import app
    uvicorn.run(app, host="0.0.0.0", port=_PORT, log_level="error")


def GraphicalUserInterface():
    InitializeFiles()
    app = QApplication(sys.argv)
    window = JarvisWebWindow()
    window.showFullScreen()
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    app.exec_()


if __name__ == "__main__":
    GraphicalUserInterface()
