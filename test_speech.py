import win32com.client
import pythoncom
import threading
import queue
import time

q = queue.Queue()

def worker():
    pythoncom.CoInitialize()
    s = win32com.client.Dispatch('SAPI.SpVoice')
    s.Rate = -1
    print("Worker started", flush=True)
    while True:
        text = q.get()
        if text is None:
            break
        print("Saying:", text, flush=True)
        s.Speak(text)
        print("Done:", text, flush=True)
        q.task_done()
    pythoncom.CoUninitialize()
    print("Worker stopped", flush=True)

t = threading.Thread(target=worker, daemon=False)
t.start()

time.sleep(0.5)

phrases = ["person very near", "bottle far", "chair near", "laptop near"]
for phrase in phrases:
    print("Queuing:", phrase, flush=True)
    q.put(phrase)
    time.sleep(3.5)

q.put(None)
t.join()
print("All done", flush=True)
