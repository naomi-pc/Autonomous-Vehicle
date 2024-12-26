import cv2
import numpy as np
import requests
import threading
import queue

# Clase personalizada para capturar el video en segundo plano
class VideoCapture:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        self.q = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    def _reader(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        return self.q.get()

# Dirección del ESP32
URL = "http://192.168.1.13"
cap = VideoCapture(URL + ":81/stream")

if __name__ == '__main__':
    # Configurar el tamaño del frame (ajusta según tu necesidad)
    requests.get(URL + "/control?var=framesize&val={}".format(3))  # 3 = CIF

    while True:
        # Leer un frame del flujo
        frame = cap.read()

        if frame is not None:
            # Convertir a escala de grises
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Binarización (asumiendo fondo claro y formas oscuras)
            _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)

            # Encontrar contornos
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                # Aproximar contorno
                approx = cv2.approxPolyDP(cnt, 0.03 * cv2.arcLength(cnt, True), True)

                # Filtrar contornos pequeños
                area = cv2.contourArea(cnt)
                if area > 500:  # Ignorar ruido o formas pequeñas
                    cv2.drawContours(frame, [approx], 0, (0, 255, 0), 3)

                    # Calcular bounding box
                    x, y, w, h = cv2.boundingRect(approx)

                    # Clasificar formas según el número de lados
                    num_sides = len(approx)

                    # Detectar manos (formas con bordes irregulares y área grande)
                    if area > 1000 and num_sides > 8:
                        print("Mano detectada")
                        cv2.putText(frame, "MANO", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                    # Detectar flechas (triángulos o formas similares)
                    elif num_sides == 7 or num_sides == 3:
                        moments = cv2.moments(cnt)
                        if moments["m00"] != 0:
                            cx = int(moments["m10"] / moments["m00"])  # Centroide X
                            cy = int(moments["m01"] / moments["m00"])  # Centroide Y

                            # Clasificar según la posición del "triángulo" de la flecha
                            if cx < x + w // 2:
                                print("Flecha hacia la derecha")
                                cv2.putText(frame, "Derecha", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            else:
                                print("Flecha hacia la izquierda")
                                cv2.putText(frame, "Izquierda", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Mostrar el frame procesado
            cv2.imshow("Output", frame)

        # Salir con la tecla 'ESC'
        key = cv2.waitKey(3)
        if key == 27:
            break

    cv2.destroyAllWindows()
    cap.cap.release()
