#!/usr/bin/env python
#coding=utf8

import rospy
import cv2 as cv
import numpy as np
import copy


from std_msgs.msg import Float32
from geometry_msgs.msg import PoseStamped, Pose
from drone_msgs.msg import Goal


# класс хранящий основные параметры найденных контуров
class contour_obj:
    # конструктор
    def __init__(self):
        self.name = None
        self.frame = []
        self.cords = []
        self.mask = []


# задаем пороги цвета
OrangeMinBGR = (0, 135, 100)
OrangeMaxBGR = (94, 255, 255)


GreenMinBGR = (45, 63, 0)
GreenMaxBGR = (80, 255, 162)


pointLandMinOrange = (0, 121, 126)      #(0, 0, 230)
pointLandMaxOrange = (255, 255, 255)    #(255, 255, 255)


pointLandMinGreen = (0, 181, 0)
pointLandMaxGreen = (255, 255, 255)


view_window_flag = False


# переменные
drone_alt = Float32
drone_current_pose = Pose()
goal_point = Goal()
max_resize = (64, 64)


# topics
alt_topic = "/drone/alt"
drone_pose_topic = "/mavros/local_position/pose"


# делаем захват видео с камеры в переменную cap
cap = cv.VideoCapture("/dev/video0")  # stereo elp >> /dev/video2, /dev/video4


# функция считывания текущего положения дрона
def callbackDronePose(data):
    global drone_pose
    drone_pose = data


# функция приёма высоты
def callbackDroneAlt(data):
    global drone_alt
    drone_alt = data


# функция определения какой маркер обнаружен
def detect_marker(cut_frame, origin_frame_bin):
    difference_val = 0
    similarity_val = 0

    try:

        for i in range(64):
            for j in range(64):
                if cut_frame[i][j] == origin_frame_bin[i][j]:
                    similarity_val += 1
                elif cut_frame[i][j] != origin_frame_bin[i][j]:
                    difference_val += 1
    except:
        similarity_val = 0
        difference_val = 0

    return(similarity_val, difference_val)


# функция вырезает детектируемый контур из кадра и возвращает его в бинаризованном виде с фиксированным размером кадра
def cut_contour(frame, cords, minVal, maxVal):
    try:
        print(cords)
        cut_contour_frame = frame[cords[1]: (cords[1] + cords[3]) + 1, cords[0]: (cords[0] + cords[2]) + 1]

        # делаем фиксированный размер картинки 64 x 64
        cut_contour_frame = cv.resize(cut_contour_frame, max_resize)
        hsv_local = cv.cvtColor(cut_contour_frame, cv.COLOR_BGR2HSV)
        cut_contour_frame = cv.inRange(hsv_local, minVal, maxVal)

    except:
        cut_contour_frame = None

    return cut_contour_frame


def contour_finder(frame, ValMinBGR, ValMaxBGR):
    # создаём объект хранящий в себе основные параметры детектируемого объекта
    detect_obj = contour_obj()

    detect_obj.frame = frame
    # переводим картинку с камеры из формата BGR в HSV
    hsv = cv.cvtColor(detect_obj.frame, cv.COLOR_BGR2HSV)

    # делаем размытие картинки HSV
    hsv = cv.blur(hsv, (4, 4))

    if view_window_flag:
        cv.imshow('Blur', hsv)

    # делаем бинаризацию картинки и пихаем её в переменную mask
    detect_obj.mask = cv.inRange(hsv, ValMinBGR, ValMaxBGR)              #OrangeMinBGR, OrangeMaxBGR
    # cv.imshow('mask', mask)

    # Уменьшаем контуры белых объектов - делаем две итерации
    detect_obj.mask = cv.erode(detect_obj.mask, None, iterations = 2)
    # cv.imshow("Erode", mask)

    # Увеличиваем контуры белых объектов (Делаем противоположность функции erode) - делаем две итерации
    mask = cv.dilate(detect_obj.mask, None, iterations = 2)

    if view_window_flag:
        cv.imshow('Dilate', detect_obj.mask)

    # накладываем полученную маску на картинку с камеры переведённую в формат HSV
    result = cv.bitwise_and(detect_obj.frame, detect_obj.frame, mask = detect_obj.mask)

    if view_window_flag:
        cv.imshow('result', result)

    # ищем контуры в результирующем кадре
    contours = cv.findContours(detect_obj.mask, cv.RETR_TREE, cv.CHAIN_APPROX_NONE)

    # вычленяем массив контуров из переменной contours и переинициализируем переменную contours
    contours = contours[1]

    # проверяем найдены ли контуры в кадре
    if contours:
        # сортируем элементы массива контуров по площади по убыванию
        contours = sorted(contours, key = cv.contourArea, reverse = True)
        # выводим все контуры на изображении
        cv.drawContours(detect_obj.frame, contours, -1, (0, 180, 255), 1)  # cv.drawContours(кадр, массив с контурами, индекс контура, цветовой диапазон контура, толщина контура)

        # получаем координаты прямоугольника описанного относительно контура
        detect_obj.cords = cv.boundingRect(contours[0])  # возвращает кортеж в формате  (x, y, w, h)

        # рисуем прямоугольник описанный относительно контура
        cv.rectangle(frame, (detect_obj.cords[0], detect_obj.cords[1]), (detect_obj.cords[0] + detect_obj.cords[2], detect_obj.cords[1] + detect_obj.cords[3]), (0, 0, 255), 2)

        # print("x: %s, y: %s" % (detect_obj.cords[0] + (detect_obj.cords[2] // 2), detect_obj.cords[1] + (detect_obj.cords[3] // 2)))
        # print("frame_center_cords:","x = ", len(frame[0])/2, "y = ", len(frame)/2)

        # рисуем окружность в центре детектируемого прямоугольника
        cv.circle(detect_obj.frame, (detect_obj.cords[0] + (detect_obj.cords[2] // 2), detect_obj.cords[1] + (detect_obj.cords[3] // 2)), 5, (0, 255, 0), thickness = 2)
        cv.circle(detect_obj.frame, (len(detect_obj.frame[0]) // 2, len(detect_obj.frame) // 2), 5, (0, 255, 0), thickness = 2)

        return detect_obj

    else:
        return detect_obj


# основная функция
def main():
    
    rospy.init_node('cv_camera_capture') # инициальизируем данную ноду с именем cv_camera_capture

    # инициализируем все переменные хранящие маски детектируемых картинок из памяти
    global point_land_mask_orange, point_land_mask_green

    # считываем и бинаризуем все метки детектирования
    point_land = cv.imread('point_land.jpg')
    point_land_mask_orange = cv.inRange(point_land, pointLandMinOrange, pointLandMaxOrange)
    point_land_mask_orange = cv.resize(point_land_mask_orange, max_resize)
    cv.imshow('cut_bin_orange', point_land_mask_orange)

    point_land_mask_green = cv.inRange(point_land, pointLandMinGreen, pointLandMaxGreen)
    point_land_mask_green = cv.resize(point_land_mask_green, max_resize)
    cv.imshow('cut_bin_green', point_land_mask_green)


    while(True):

        # читаем флаг подключения камеры и картинку с камеры
        ret, frame = cap.read()
        # делаем копию кадра
        copy_frame = frame.copy()

        # print(frame)
        if ret:
                ##########################

            point_land_orange = contour_finder(frame, OrangeMinBGR, OrangeMaxBGR)
            print(point_land_orange.cords)

                ##########################

            print("Orange Найдено сходств %s, найдено различий %s" %detect_marker(cut_contour(copy_frame, point_land_orange.cords, OrangeMinBGR, OrangeMaxBGR), point_land_mask_orange))
            # print("Green Найдено сходств %s, найдено различий %s" % detect_marker(cut_contour(copy_frame, point_land_orange.cords, GreenMinBGR, GreenMaxBGR), point_land_mask_green))


            if cv.waitKey(1) == 27:  # проверяем была ли нажата кнопка esc
                break

        else:
            print("Camera not found!")
            break


if __name__ == "__main__":
    main()
    cap.release()
    cv.destroyAllWindows()

