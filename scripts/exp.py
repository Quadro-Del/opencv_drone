#!/usr/bin/env python
#coding=utf8

import cv2 as cv

cap = cv.VideoCapture("/dev/video2") # "/dev/video0"
cap.set(cv.CAP_PROP_FPS, 24) # Частота кадров
cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920) # Ширина кадров в видеопотоке.       # 1280, 960
cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080) # Высота кадров в видеопотоке.

while True:

    ret, frame = cap.read()


    if ret:
        # frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        cv.imshow("hnya", frame)
        print(len(frame[0]), len(frame))
        #print(result)
        if cv.waitKey(1) == 27: # проверяем была ли нажата кнопка esc
            break
    else:
        print("Camera not found!")
        break

cap.release()
cv.destroyAllWindows()
